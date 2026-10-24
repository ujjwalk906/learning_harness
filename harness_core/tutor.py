"""Optional Jupyter AI/Codex setup; importing this module installs nothing."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import sysconfig

PERSONA_ID = "jupyter-ai-personas::jupyter_ai_acp_client::CodexAcpPersona"
ADAPTER_PACKAGE = "@agentclientprotocol/codex-acp@2.2.2"
REQUIRED_MODULES = ["jupyter_ai", "jupyter_ai_acp_client", "pycrdt", "watchfiles", "cryptography"]


def android_environment(environ=None):
    """Expose Python symbols to Android abi3 libraries in child processes only."""
    env = dict(os.environ if environ is None else environ)
    if sys.platform == "android":
        library = sysconfig.get_config_var("LDLIBRARY")
        libpython = Path(sys.base_prefix) / "lib" / library if library else None
        if libpython and libpython.is_file():
            preloads = env.get("LD_PRELOAD", "").replace(":", " ").split()
            if str(libpython) not in preloads:
                env["LD_PRELOAD"] = " ".join([str(libpython), *preloads])
    return env


def adapter_path(directory):
    return Path(directory) / "node/node_modules/.bin" / (
        "codex-acp.cmd" if os.name == "nt" else "codex-acp")


def prerequisites(directory):
    required = ["node", "codex"]
    if not adapter_path(directory).exists():
        required.append("npm")
    commands = {name: shutil.which(name) for name in required}
    missing = [name for name, value in commands.items() if not value]
    if missing:
        raise SystemExit("AI chat needs " + ", ".join(missing) +
                         ". See docs/ai-tutor.md. Ordinary sh start.sh remains available.")
    return commands


def ensure_adapter(directory):
    """Called under the course lifecycle lock; never install npm packages globally."""
    commands = prerequisites(directory)
    if not adapter_path(directory).exists():
        subprocess.run([
            commands["npm"], "install", "--prefix", str(Path(directory) / "node"),
            "--omit=optional", "--ignore-scripts", "--no-audit", "--no-fund", ADAPTER_PACKAGE,
        ], check=True, timeout=600)
    if not adapter_path(directory).exists():
        raise SystemExit("Codex adapter installation did not produce an executable")


def instructions(config):
    """Give the tutor a small course brief; retrieve relevant chapters on demand."""
    options = config.get("runtime", {}).get("ai_tutor", {})
    if not isinstance(options, dict) or not isinstance(options.get("instructions", ""), str):
        raise ValueError("runtime.ai_tutor must be an object with optional instructions text")
    return (
        "You are the learner's tutor for " + str(config.get("title", "this course")) + ". "
        "The learner's goal is: " + str(config.get("goal", "See course.json")) + ". "
        "Answer questions about attached notebook cells, outputs and readings. "
        "Explain mechanisms, prerequisites, concrete examples and limits. "
        "For source-specific questions inspect the relevant source catalog, chapter "
        "and state/current.json, then cite local paths and sections. Do not assume "
        "you have seen a cell, output or source that was not provided or inspected. "
        "Offer hints before exercise solutions unless the learner asks for the solution. "
        "Follow the learner's requested depth and tutoring style. Do not modify source "
        "originals or course teaching. Do not run commands or change workspace files "
        "unless the learner requests it. Do not delegate. Chat, successful execution "
        "and answered questions are not proof of mastery. The active teaching agent uses learn.py for evidence. Do not automatically write "
        "submissions, assessments or review schedules; record assistance explicitly "
        "if the learner separately requests an evidence submission. " + options.get("instructions", "")
    )


def environment(config, directory, environ=None):
    env = android_environment(environ)
    try:
        overrides = json.loads(env.get("CODEX_CONFIG", "{}"))
    except ValueError as exc:
        raise ValueError("CODEX_CONFIG must be a JSON object") from exc
    if not isinstance(overrides, dict):
        raise ValueError("CODEX_CONFIG must be a JSON object")
    existing = overrides.get("developer_instructions", "")
    if not isinstance(existing, str):
        raise ValueError("CODEX_CONFIG developer_instructions must be text")
    overrides.setdefault("sandbox_mode", "read-only")
    # The earlier `untrusted` approval policy is no longer accepted by Codex.
    overrides.setdefault("approval_policy", "on-request")
    overrides["developer_instructions"] = (existing + "\n\n" if existing else "") + instructions(config)
    env.update({
        "PATH": str(adapter_path(directory).parent) + os.pathsep + env.get("PATH", ""),
        "CODEX_PATH": shutil.which("codex") or "codex",
        "INITIAL_AGENT_MODE": env.get("INITIAL_AGENT_MODE", "read-only"),
        "CODEX_CONFIG": json.dumps(overrides),
    })
    return env


def jupyter_configuration():
    # Put these in the explicitly loaded server config. A separate
    # jupyter_server_config.d file was ignored by that launch path in the trial.
    return ("c.PersonaManager.default_persona_id = " + repr(PERSONA_ID) + "\n"
            "c.MCPExtensionApp.mcp_port = 0\n")


def connection_result(reply):
    """Classify a fixed smoke request without retaining a transcript."""
    text = reply.strip() if isinstance(reply, str) else ""
    if text == "TUTOR_CONNECTION_OK":
        return {"ok": True, "status": "ok"}
    lowered = text.casefold()
    if any(term in lowered for term in ["usage limit", "usage_limit_exceeded", "insufficient_quota", "rate limit"]):
        return {"ok": False, "status": "usage-limit",
                "detail": "The configured account is usage-limited; model access was not verified. Retry after account availability returns."}
    if any(term in lowered for term in ["not configured", "authentication required", "not authenticated", "log in", "sign in"]):
        return {"ok": False, "status": "authentication-required",
                "detail": "Codex needs authentication. Complete the chosen login in your terminal."}
    return {"ok": False, "status": "unexpected-reply",
            "detail": "The fixed connection request did not complete as expected; inspect the private Jupyter log."}
