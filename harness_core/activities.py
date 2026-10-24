"""Publish immutable multi-surface activities; retain old links and learner work."""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from .engine import activity_key, require
from .store import Invalid, atomic_json, identity, safe_path, text

SURFACES = {".html": "html", ".htm": "html", ".md": "markdown", ".ipynb": "notebook",
            ".txt": "text", ".pdf": "pdf", ".mp3": "audio", ".wav": "audio", ".ogg": "audio",
            ".mp4": "video", ".webm": "video", ".png": "image", ".jpg": "image", ".jpeg": "image", ".svg": "image"}


def publish(harness, course, specification, artifact=None, *, activity_id=None):
    require(isinstance(specification, dict), "Activity specification must be an object")
    specification = json.loads(json.dumps(specification, allow_nan=False))
    source = Path(artifact).expanduser().absolute() if artifact is not None else None
    require(source is None or (source.exists() and not source.is_symlink()), "Activity artifact does not exist or is a symbolic link")
    entry = specification.get("entrypoint", source.name if source and source.is_file() else "index.html" if source else "question.md")
    identity(activity_id or "activity")
    with harness.store.locked(course):
        state = harness.state(course)
        harness.validate_activity(specification, state)
        aid = activity_id or "a_" + uuid.uuid4().hex[:12]
        identity(aid)
        versions = [a for a in state["activities"].values() if a["id"] == aid]
        version = f"v{len(versions) + 1:03d}"
        root = harness.store.root(course)
        from .sources import verify
        integrity = verify(root)
        require(integrity["ok"], "Original source integrity failed: " + "; ".join(integrity["errors"]))
        target = safe_path(root, f"activities/{aid}/{version}")
        require(not target.exists(), "Activity version already exists; never overwrite a published activity")
        parent = safe_path(root, "activities")
        with tempfile.TemporaryDirectory(prefix=".publish-", dir=parent) as temporary:
            stage = Path(temporary) / "content"
            stage.mkdir()
            if source is None:
                require(entry == "question.md", "Chat-only tasks use question.md as their saved question")
                question = "# " + specification["title"] + "\n\n" + specification["instruction"] + "\n\n"
                question += "## Announced criteria\n\n" + "\n".join("- " + c["description"] for c in specification["criteria"])
                (stage / entry).write_text(question, encoding="utf-8")
                source = stage
                conversation = True
            else:
                conversation = False
            candidates = list(source.rglob("*")) if source.is_dir() else [source]
            files, total = {}, 0
            for path in candidates:
                require(not path.is_symlink(), "Activity bundles cannot contain symbolic links")
                if not path.is_file():
                    continue
                relative = path.relative_to(source).as_posix() if source.is_dir() else source.name
                require(not any(part.startswith(".") for part in Path(relative).parts), "Do not publish hidden/runtime files")
                data = path.read_bytes()
                total += len(data)
                require(total <= 50 * 1024 * 1024, "Activity exceeds 50 MiB; keep large source libraries separate")
                destination = safe_path(stage, relative)
                destination.parent.mkdir(parents=True, exist_ok=True)
                if destination != path:
                    destination.write_bytes(data)
                files[relative] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            require(entry in files, "Entrypoint must be a file inside the activity bundle")
            surface = "conversation" if conversation else SURFACES.get(Path(entry).suffix.lower())
            require(surface is not None, "Unsupported entrypoint; use HTML, Markdown, notebook, text, PDF, image, audio or video")
            if surface == "notebook":
                notebook = json.loads((stage / entry).read_text())
                require(notebook.get("nbformat") == 4 and isinstance(notebook.get("cells"), list), "Use a valid notebook v4 document")
            specification.update(id=aid, version=version, surface=surface, entrypoint=entry, files=files,
                path=f"activities/{aid}/{version}", graph_scope_version=state["graph"].get("scope_version", 0))
            target.parent.mkdir(parents=True, exist_ok=True)
            stage.rename(target)
            try:
                event = harness.store.append_locked(course, "activity", specification, at=harness.clock())
            except BaseException:
                shutil.rmtree(target)
                raise
        harness._snapshot(course)
        return {"activity": activity_key(specification), "event_id": event["id"],
                "path": str(target), "url_path": f"/activity/{course}/{aid}/{version}"}


def read_asset(harness, course, activity, relative):
    record = harness.state(course)["activities"].get(activity)
    require(record is not None, "Unknown activity version")
    require(relative in record["files"], "Asset is not part of this published activity")
    path = safe_path(harness.store.root(course), record["path"] + "/" + relative)
    data = path.read_bytes()
    require(hashlib.sha256(data).hexdigest() == record["files"][relative]["sha256"],
            "Published activity was altered; publish a new version and preserve the old evidence")
    return data


def public_activity(record):
    return {k: v for k, v in record.items() if k not in {"private_evaluation", "files"}}


def markdown(source):
    """Small escaped reading renderer; original Markdown is available for download."""
    blocks, code = [], None
    def inline(value):
        value = html.escape(value)
        value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
        value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
        # Preserve readable links, permitting only explicit HTTP(S) destinations.
        value = re.sub(r"\[([^\]]+)\]\((https?://[^\s)]+)\)", r'<a href="\2" target="_blank" rel="noreferrer">\1</a>', value)
        return value
    for line in source.splitlines():
        if line.startswith("```"):
            if code is None:
                code = []
            else:
                blocks.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
                code = None
        elif code is not None:
            code.append(line)
        elif re.match(r"^#{1,6} ", line):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(f"<h{level}>{inline(line[level + 1:])}</h{level}>")
        elif line.startswith(("- ", "* ")):
            blocks.append("<p class='list-item'>• " + inline(line[2:]) + "</p>")
        elif line.strip():
            blocks.append("<p>" + inline(line) + "</p>")
    if code is not None:
        blocks.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
    return "\n".join(blocks)


def reading_document(content):
    return ("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
            "<style>body{font:17px/1.8 Georgia,serif;color:#243d34;background:#fffdf8;max-width:760px;margin:40px auto;padding:0 28px}"
            "h1,h2,h3{font-family:system-ui;line-height:1.3}pre{overflow:auto;background:#edf1ec;padding:20px;border-radius:10px;font:14px/1.7 monospace}"
            "code{background:#edf1ec}a{color:#27614c}.list-item{margin:.4em 0}.cell{border-top:1px solid #dae2d8;margin-top:28px;padding-top:20px}"
            "</style></head><body>" + content + "</body></html>").encode()


def render(harness, course, activity, relative):
    record = harness.state(course)["activities"][activity]
    data = read_asset(harness, course, activity, relative)
    if relative != record["entrypoint"]:
        return data, None
    surface = record["surface"]
    if surface == "html":
        source = data.decode("utf-8")
        bridge = '<script src="/bridge.js"></script>'
        source = source.replace("</head>", bridge + "</head>", 1) if "</head>" in source else bridge + source
        return source.encode(), "text/html; charset=utf-8"
    if surface in {"markdown", "conversation"}:
        return reading_document(markdown(data.decode("utf-8"))), "text/html; charset=utf-8"
    if surface == "text":
        return reading_document("<pre>" + html.escape(data.decode("utf-8")) + "</pre>"), "text/html; charset=utf-8"
    if surface == "notebook":
        cells = []
        for cell in json.loads(data)["cells"]:
            source = cell.get("source", "")
            source = "".join(source) if isinstance(source, list) else source
            cells.append("<section class='cell'>" + (markdown(source) if cell["cell_type"] == "markdown"
                         else "<pre><code>" + html.escape(source) + "</code></pre>") + "</section>")
        return reading_document("<p>Notebook preview. Use <strong>Open in Jupyter</strong> in the activity toolbar to execute cells.</p>" + "".join(cells)), "text/html; charset=utf-8"
    return data, None
