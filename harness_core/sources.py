"""Acquire licensed source originals and check their immutable receipts.

Only acquisition writes receipts.  Verification deliberately has no repair mode:
changed originals require a new source ID and a new acquisition.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from urllib.parse import unquote, urlsplit
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener, url2pathname
import zipfile


class SourceError(ValueError):
    """Invalid source request, acquisition failure, or publication collision."""


_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}\Z")
_HASH = re.compile(r"[0-9a-fA-F]{64}\Z")
_ROLES = {"primary-teaching", "supporting-teaching", "technical-reference"}
_METHODS = {"file", "archive", "git", "local"}


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise SourceError(f"{label} must be a nonempty string")
    return value


def _source_id(value: object) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise SourceError("source_id must use 1–100 letters, digits, hyphens or underscores")
    return value


def _relative(value: object, *, archive: bool = False) -> str:
    """Return a safe portable relative path without silently removing '..'."""
    if not isinstance(value, str) or not value or "\x00" in value or "\\" in value:
        raise SourceError(f"unsafe relative path: {value!r}")
    if archive:
        while value.startswith("./"):
            value = value[2:]
        value = value.rstrip("/")
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise SourceError(f"unsafe relative path: {value!r}")
    if any(part in {"", ".", ".."} for part in value.split("/")):
        raise SourceError(f"unsafe relative path: {value!r}")
    return value


def _paths(values: object, label: str) -> list[str]:
    if isinstance(values, (str, bytes)):
        raise SourceError(f"{label} must be a sequence of relative paths")
    try:
        result = [_relative(value) for value in values]
    except TypeError as exc:
        raise SourceError(f"{label} must be a sequence of relative paths") from exc
    if len(set(result)) != len(result):
        raise SourceError(f"{label} contains duplicate paths")
    return result


def _http_url(value: object) -> str:
    value = _text(value, "url")
    if any(character.isspace() or ord(character) < 32 for character in value) or "\\" in value:
        raise SourceError("URL contains whitespace, control characters or backslashes")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.fragment or (port is not None and not 0 < port < 65536)):
            raise ValueError
    except ValueError as exc:
        raise SourceError("use an absolute HTTP(S) URL without credentials or a fragment") from exc
    return value


def _local_path(value: object) -> Path:
    value = _text(value, "local URL/path")
    if value.startswith("file:"):
        parsed = urlsplit(value)
        if (parsed.scheme != "file" or parsed.netloc not in {"", "localhost"}
                or parsed.query or parsed.fragment):
            raise SourceError("local file URLs must name an absolute local path")
        value = url2pathname(parsed.path)
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.exists():
        raise SourceError("local sources must be existing absolute paths, not symlinks")
    return path.resolve()


class _SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        try:
            _http_url(new_url)
        except SourceError:
            response.close()
            raise
        return super().redirect_request(request, response, code, message, headers, new_url)


def _download(url: str) -> tuple[bytes, str]:
    try:
        opener = build_opener(_SafeRedirect())
        with opener.open(Request(url, headers={"User-Agent": "course-harness/1"}), timeout=60) as response:
            final_url = _http_url(response.geturl())
            return response.read(), final_url
    except SourceError:
        raise
    except HTTPError as exc:
        exc.close()
        raise SourceError(f"download failed for {url}: HTTP {exc.code}") from exc
    except (OSError, ValueError, HTTPException) as exc:
        raise SourceError(f"download failed for {url}: {exc}") from exc


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_digest(data: bytes, expected: str | None) -> str:
    actual = _digest(data)
    if expected is not None and actual != expected.lower():
        raise SourceError(f"SHA-256 mismatch: expected {expected.lower()}, received {actual}")
    return actual


def _selected(path: str, include: list[str]) -> bool:
    return not include or any(path == item or path.startswith(item + "/") for item in include)


def _write(destination: Path, name: str, data: bytes) -> None:
    path = destination.joinpath(*name.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as output:
            output.write(data)
    except (FileExistsError, IsADirectoryError, NotADirectoryError) as exc:
        raise SourceError(f"duplicate or conflicting source path: {name}") from exc


def _archive(data: bytes, destination: Path, include: list[str], strip: int) -> None:
    """Read, never execute/extractall, an archive; inspect unselected entries too."""
    seen: set[str] = set()
    matched: set[str] = set()

    def target(name: str, directory: bool) -> str | None:
        # A tar created with `tar ... .` may contain the root directory itself.
        if directory and name.rstrip("/") in {"", "."}:
            return None
        safe = _relative(name, archive=True)
        parts = safe.split("/")[strip:]
        if not parts:
            if not directory:
                raise SourceError(f"strip_components removes an entire file path: {name}")
            return None
        name = "/".join(parts)
        if not directory:
            if name in seen:
                raise SourceError(f"duplicate archive file: {name}")
            seen.add(name)
        if not _selected(name, include):
            return None
        for item in include:
            if name == item or name.startswith(item + "/"):
                matched.add(item)
        return name

    stream = io.BytesIO(data)
    try:
        if zipfile.is_zipfile(stream):
            with zipfile.ZipFile(stream) as archive:
                for member in archive.infolist():
                    mode = member.external_attr >> 16
                    kind = stat.S_IFMT(mode)
                    directory = member.is_dir()
                    if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
                        raise SourceError(f"archive contains a link or special file: {member.filename}")
                    name = target(member.filename, directory)
                    if name is not None and not directory:
                        _write(destination, name, archive.read(member))
        else:
            stream.seek(0)
            with tarfile.open(fileobj=stream, mode="r:*") as archive:
                for member in archive:
                    if not (member.isfile() or member.isdir()):
                        raise SourceError(f"archive contains a link or special file: {member.name}")
                    name = target(member.name, member.isdir())
                    if name is not None and member.isfile():
                        original = archive.extractfile(member)
                        if original is None:
                            raise SourceError(f"unreadable archive member: {member.name}")
                        with original:
                            _write(destination, name, original.read())
    except (tarfile.TarError, zipfile.BadZipFile, RuntimeError, EOFError, OSError) as exc:
        raise SourceError(f"invalid or unreadable archive: {exc}") from exc
    missing = set(include) - matched
    if missing:
        raise SourceError(f"selected paths not found in archive: {', '.join(sorted(missing))}")


def _inventory(directory: Path) -> list[dict]:
    result = []
    if directory.is_symlink() or not directory.is_dir():
        raise SourceError(f"source root is missing or is a symlink: {directory}")
    def unreadable(error):
        raise error

    for parent, directories, files in os.walk(directory, followlinks=False, onerror=unreadable):
        for name in directories + files:
            path = Path(parent) / name
            if path.is_symlink():
                raise SourceError(f"source contains a symlink: {path.relative_to(directory)}")
            if name in files:
                if not path.is_file():
                    raise SourceError(f"source contains a special file: {path.relative_to(directory)}")
                data = path.read_bytes()
                result.append({"path": path.relative_to(directory).as_posix(),
                               "bytes": len(data), "sha256": _digest(data)})
    return sorted(result, key=lambda entry: entry["path"])


def _copy_local(source: Path, destination: Path, include: list[str], filename: str | None) -> None:
    if source.is_file():
        name = filename or _relative(source.name)
        if include:
            raise SourceError("include applies to directories, not a single local file")
        _write(destination, name, source.read_bytes())
        return
    if filename is not None:
        raise SourceError("filename applies only to single files")
    entries = _inventory(source)  # Also rejects links outside the selected scope.
    for item in include:
        if not any(entry["path"] == item or entry["path"].startswith(item + "/") for entry in entries):
            raise SourceError(f"selected local path not found: {item}")
    for entry in entries:
        name = entry["path"]
        if _selected(name, include):
            _write(destination, name, (source / name).read_bytes())


def _git(url: str, revision: str, destination: Path, include: list[str], work: Path) -> str:
    """Fetch a revision into a bare repo and read exact, unfiltered Git blobs."""
    env = os.environ.copy()
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0"})
    # Do not inherit repository/command injection settings from a caller's shell.
    for name in list(env):
        if name in {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_CONFIG_PARAMETERS",
                    "GIT_CONFIG_COUNT", "GIT_EXEC_PATH", "GIT_TEMPLATE_DIR"} or name.startswith("GIT_CONFIG_KEY_") or name.startswith("GIT_CONFIG_VALUE_"):
            env.pop(name, None)
    repo = work / "repository.git"

    def run(*arguments: str, input_data: bytes | None = None) -> bytes:
        command = ["git", "-c", "core.hooksPath=" + os.devnull,
                   "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
                   "-c", "protocol.http.allow=always", "-c", "protocol.file.allow=always",
                   *arguments]
        try:
            result = subprocess.run(command, env=env, input=input_data,
                                    stdin=subprocess.DEVNULL if input_data is None else None,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    check=True, timeout=180)
            return result.stdout
        except FileNotFoundError as exc:
            raise SourceError("git is required for method='git'") from exc
        except subprocess.TimeoutExpired as exc:
            raise SourceError("git source acquisition timed out") from exc
        except subprocess.CalledProcessError as exc:
            detail = exc.stderr.decode("utf-8", errors="replace").strip()
            raise SourceError(f"git acquisition failed: {detail}") from exc

    run("init", "--bare", "--template=", str(repo))
    run("-C", str(repo), "fetch", "--no-tags", "--depth=1", "--", url, revision)
    commit = run("-C", str(repo), "rev-parse", "--verify", "FETCH_HEAD^{commit}").decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", commit):
        raise SourceError("git did not resolve a full commit ID")
    # A checkout can run filters; git archive can rewrite export-subst blobs or
    # omit export-ignore files. Read blobs directly to preserve committed bytes.
    selected = []
    matched = set()
    tree = run("-C", str(repo), "ls-tree", "-r", "-z", "--full-tree", commit)
    for record in tree.split(b"\x00"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, object_id = metadata.split()
        try:
            name = _relative(raw_name.decode("utf-8"))
        except UnicodeDecodeError as exc:
            raise SourceError("Git source paths must use UTF-8") from exc
        if mode not in {b"100644", b"100755"} or kind != b"blob":
            raise SourceError(f"git source contains a symlink, submodule or special entry: {name}")
        if _selected(name, include):
            selected.append((name, object_id))
            matched.update(item for item in include if name == item or name.startswith(item + "/"))
    missing = set(include) - matched
    if missing:
        raise SourceError(f"selected paths not found in git revision: {', '.join(sorted(missing))}")
    if selected:
        blobs = io.BytesIO(run("-C", str(repo), "cat-file", "--batch",
                               input_data=b"".join(object_id + b"\n" for _, object_id in selected)))
        for name, object_id in selected:
            header = blobs.readline().split()
            if len(header) != 3 or header[0] != object_id or header[1] != b"blob":
                raise SourceError(f"invalid git blob response: {name}")
            size = int(header[2])
            data = blobs.read(size)
            if len(data) != size or blobs.read(1) != b"\n":
                raise SourceError(f"incomplete git blob: {name}")
            _write(destination, name, data)
    return commit


def _directories(root: Path, *, create: bool) -> Path:
    sources = root / "sources"
    for path in (sources, sources / "library", sources / "receipts", sources / "catalog"):
        if path.is_symlink():
            raise SourceError(f"source storage may not be a symlink: {path}")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        if path.exists() and not path.is_dir():
            raise SourceError(f"source storage must be a directory: {path}")
    return sources


@contextmanager
def _lock(sources: Path):
    path = sources / ".acquire.lock"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise SourceError("another acquisition is active; inspect sources/.acquire.lock if interrupted") from exc
    try:
        with os.fdopen(descriptor, "w") as output:
            output.write(str(os.getpid()) + "\n")
        yield
    finally:
        path.unlink()


def _json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def acquire(root: Path, *, source_id, title, url, license, license_files: list[str],
            role="primary-teaching", method="file", revision=None, include=(),
            strip_components=0, sha256=None, filename=None, selection_reason="") -> dict:
    """Acquire original bytes after the author has checked reuse permission.

    Archive includes are exact paths/directory prefixes *after* stripping. Git
    requires an explicit revision; the recorded revision is its resolved commit.
    A direct file may name itself as a license_file when its license is embedded.
    This function cannot determine whether a supplied license actually grants use.
    """
    source_id = _source_id(source_id)
    _text(title, "title")
    _text(license, "license (explicit, human-checked reuse metadata)")
    if method not in _METHODS or role not in _ROLES:
        raise SourceError("unsupported acquisition method or source role")
    if not isinstance(selection_reason, str):
        raise SourceError("selection_reason must be a string")
    licenses = _paths(license_files, "license_files")
    if not licenses:
        raise SourceError("at least one actual license file must be preserved")
    includes = _paths(include, "include")
    if isinstance(strip_components, bool) or not isinstance(strip_components, int) or strip_components < 0:
        raise SourceError("strip_components must be a nonnegative integer")
    if method != "archive" and strip_components:
        raise SourceError("strip_components applies only to archives")
    if method == "archive" and not includes:
        raise SourceError("archive acquisition requires explicit include paths")
    if method in {"git", "archive"} and filename is not None:
        raise SourceError("filename applies only to single files")
    if method == "file" and includes:
        raise SourceError("include applies to directory, archive or git sources")
    if filename is not None:
        filename = _relative(filename)
    if sha256 is not None and (not isinstance(sha256, str) or not _HASH.fullmatch(sha256)):
        raise SourceError("sha256 must be a 64-character hexadecimal digest")
    if method == "git" and sha256 is not None:
        raise SourceError("git is pinned by revision; sha256 applies to downloaded/local snapshots")
    if revision is not None:
        _text(revision, "revision")
    if method == "git":
        if revision is None or revision.startswith("-") or any(c.isspace() for c in revision):
            raise SourceError("git requires an explicit revision without whitespace or option prefixes")
        if isinstance(url, str) and (url.startswith("file:") or Path(url).is_absolute()):
            canonical_url = _local_path(url).as_uri()
        else:
            canonical_url = _http_url(url)
    elif method == "local":
        local_source = _local_path(url)
        canonical_url = local_source.as_uri()
    else:
        canonical_url = _http_url(url)

    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    sources = _directories(root, create=True)
    destinations = (sources / "library" / source_id,
                    sources / "receipts" / (source_id + ".json"),
                    sources / "catalog" / (source_id + ".json"))
    with _lock(sources):
        if any(path.exists() or path.is_symlink() for path in destinations):
            raise SourceError(f"source ID already exists or collides with stored data: {source_id}")
        with tempfile.TemporaryDirectory(prefix=".acquire-", dir=sources) as temporary:
            work = Path(temporary)
            payload = work / "originals"
            payload.mkdir()
            retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            selection = {"include": includes, "strip_components": strip_components,
                         "scope": "selected" if includes else "all"}
            if filename is not None:
                selection["filename"] = filename
            if revision is not None:
                selection["requested_revision"] = revision
            extra = {}
            if method == "git":
                resolved_revision = _git(canonical_url, revision, payload, includes, work)
            elif method == "local":
                _copy_local(local_source, payload, includes, filename)
            else:
                data, final_url = _download(canonical_url)
                if final_url != canonical_url:
                    selection["resolved_url"] = final_url
                snapshot_digest = _check_digest(data, sha256)
                if method == "archive":
                    extra["archive_sha256"] = snapshot_digest
                    _archive(data, payload, includes, strip_components)
                else:
                    name = filename or _relative(unquote(PurePosixPath(urlsplit(canonical_url).path).name))
                    _write(payload, name, data)
                    selection["filename"] = name
            files = _inventory(payload)
            if not files:
                raise SourceError("source selection contains no files")
            actual_names = {entry["path"] for entry in files}
            missing = set(licenses) - actual_names
            if missing:
                raise SourceError(f"license files are missing from selected originals: {', '.join(sorted(missing))}")
            if method == "local":
                if local_source.is_file():
                    snapshot_digest = _check_digest((payload / files[0]["path"]).read_bytes(), sha256)
                else:
                    snapshot_digest = _check_digest(json.dumps(files, sort_keys=True, separators=(",", ":")).encode(), sha256)
            if method != "git":
                resolved_revision = revision or "sha256:" + snapshot_digest
            receipt = {"schema_version": 1, "source_id": source_id, "method": method,
                       "url": canonical_url, "revision": resolved_revision,
                       "retrieved_at": retrieved_at, "selection": selection,
                       "files": files, **extra}
            catalog = {"id": source_id, "title": title, "upstream_url": canonical_url,
                       "revision": resolved_revision, "retrieved_at": retrieved_at,
                       "license": license, "license_files": licenses,
                       "local_root": f"sources/library/{source_id}", "role": role,
                       "selection_reason": selection_reason, "files_read": [], "limitations": []}
            receipt_path, catalog_path = work / "receipt.json", work / "catalog.json"
            _json(receipt_path, receipt)
            _json(catalog_path, catalog)
            _directories(root, create=False)
            committed = []
            try:
                for staged, destination in zip((payload, receipt_path, catalog_path), destinations):
                    if destination.exists() or destination.is_symlink():
                        raise SourceError(f"source ID collided during acquisition: {source_id}")
                    staged.rename(destination)
                    committed.append(destination)
            except BaseException:
                for path in reversed(committed):
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                raise
    return catalog


def verify(root: Path) -> dict:
    """Compare current originals to saved receipts without changing any files."""
    errors: list[str] = []
    count_files = 0
    count_sources = 0
    root = Path(root).resolve()
    try:
        sources = _directories(root, create=False)
        if (sources / ".acquire.lock").exists() or (sources / ".acquire.lock").is_symlink():
            raise SourceError("acquisition in progress or interrupted: sources/.acquire.lock exists")
        if not sources.exists():
            return {"ok": True, "sources": 0, "files": 0, "errors": []}
        groups: dict[str, set[str]] = {}
        for group in ("library", "receipts", "catalog"):
            directory = sources / group
            names = set()
            if directory.exists():
                for path in sorted(directory.iterdir()):
                    if path.is_symlink():
                        errors.append(f"{group}: symlink is forbidden: {path.name}")
                        continue
                    if group == "library":
                        if not path.is_dir():
                            errors.append(f"library: unexpected non-directory: {path.name}")
                            continue
                        name = path.name
                    else:
                        if path.suffix != ".json" or not path.is_file():
                            errors.append(f"{group}: unexpected entry: {path.name}")
                            continue
                        name = path.stem
                    try:
                        names.add(_source_id(name))
                    except SourceError as exc:
                        errors.append(f"{group}: {exc}: {name}")
            groups[group] = names
        all_ids = set.union(*groups.values())
        for source_id in sorted(all_ids):
            count_sources += 1
            missing_groups = [group for group, names in groups.items() if source_id not in names]
            if missing_groups:
                errors.append(f"{source_id}: incomplete acquisition; missing {', '.join(missing_groups)}")
                continue
            try:
                receipt = json.loads((sources / "receipts" / (source_id + ".json")).read_text(encoding="utf-8"))
                catalog = json.loads((sources / "catalog" / (source_id + ".json")).read_text(encoding="utf-8"))
                if not isinstance(receipt, dict) or not isinstance(catalog, dict):
                    raise SourceError("receipt and catalog must be JSON objects")
                if receipt.get("schema_version") != 1 or receipt.get("source_id") != source_id:
                    raise SourceError("receipt schema/source_id mismatch")
                if receipt.get("method") not in _METHODS or not isinstance(receipt.get("selection"), dict):
                    raise SourceError("receipt method/selection is invalid")
                for field in ("url", "revision", "retrieved_at"):
                    _text(receipt.get(field), "receipt " + field)
                if catalog.get("id") != source_id or catalog.get("local_root") != f"sources/library/{source_id}":
                    raise SourceError("catalog ID/local_root mismatch")
                for catalog_field, receipt_field in (("upstream_url", "url"), ("revision", "revision"), ("retrieved_at", "retrieved_at")):
                    if catalog.get(catalog_field) != receipt[receipt_field]:
                        raise SourceError(f"catalog {catalog_field} differs from acquisition receipt")
                licenses = _paths(catalog.get("license_files"), "catalog license_files")
                if not licenses:
                    raise SourceError("catalog has no license files")
                _text(catalog.get("license"), "catalog license")
                entries = receipt.get("files")
                if not isinstance(entries, list) or not entries:
                    raise SourceError("receipt files must be a nonempty list")
                expected = {}
                for entry in entries:
                    if not isinstance(entry, dict):
                        raise SourceError("invalid receipt file entry")
                    name = _relative(entry.get("path"))
                    if name in expected:
                        raise SourceError(f"duplicate receipt file: {name}")
                    size, digest = entry.get("bytes"), entry.get("sha256")
                    if isinstance(size, bool) or not isinstance(size, int) or size < 0 or not isinstance(digest, str) or not _HASH.fullmatch(digest):
                        raise SourceError(f"invalid receipt byte length/hash: {name}")
                    expected[name] = {"path": name, "bytes": size, "sha256": digest.lower()}
                if set(licenses) - set(expected):
                    raise SourceError("license file is absent from immutable receipt")
                actual = {entry["path"]: entry for entry in _inventory(sources / "library" / source_id)}
                count_files += len(actual)
                for name in sorted(set(expected) - set(actual)):
                    errors.append(f"{source_id}: missing original: {name}")
                for name in sorted(set(actual) - set(expected)):
                    errors.append(f"{source_id}: added original: {name}")
                for name in sorted(set(actual) & set(expected)):
                    if actual[name] != expected[name]:
                        errors.append(f"{source_id}: changed original: {name}")
            except (SourceError, OSError, ValueError, TypeError) as exc:
                errors.append(f"{source_id}: {exc}")
    except (SourceError, OSError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "sources": count_sources, "files": count_files, "errors": errors}
