# Install Fieldnotes from a link

This guide is for the agent helping the learner. Do the setup for them, then
begin learning. The public repository is
https://github.com/ujjwalk906/learning_harness.

## Choose the available environment

Check what tools you actually have: downloading files, writing files and running
Python 3.11+ in a macOS/Linux environment are sufficient. No API key, paid API,
pip package, Node, Git or separate model runner is required for core learning.
Git is convenient for acquisition; downloading and extracting GitHub's source ZIP
also works. Native Windows needs a Linux environment such as WSL.

If you can only browse/read links, you cannot install this executable skill from
the chat. Explain this briefly and offer the user the ZIP upload route below or
a local file-capable agent. You can explain material in chat, but do not claim
durable Fieldnotes records without executing its tools.

## Local Claude Code or Codex

1. Download the repository into an unused workspace folder. Read `install.py` and
   this guide before executing setup. With Git, the acquisition command is:

   ```sh
   git clone https://github.com/ujjwalk906/learning_harness.git
   cd learning_harness
   ```

2. Run the installer for the current agent:

   ```sh
   python3 install.py --target claude
   # Or, for Codex:
   python3 install.py --target codex
   ```

   Without `--target`, it installs for both. It copies a complete skill to
   `~/.claude/skills/learning-guide` or `~/.agents/skills/learning-guide`.
   The original clone is no longer needed after installation. Do not use a
   generic skill-folder installer on `skills/learning-guide` alone: that folder
   lacks the runtime. The project installer bundles everything it needs.

3. Use the absolute `learn.py` path printed by setup to run `doctor` and `list`.
   Read the installed `SKILL.md`. Verify the reported courses directory is the
   one the learner intends to use. Setup must not create a practice course,
   fake answers, observations or an assessment of the person installing it.
4. Report that setup is ready and begin with the learner's stated goal. Claude
   Code can invoke `/learning-guide`; Codex can invoke `$learning-guide`.
   Ordinary requests such as “Help me learn Spanish” can also select the skill.
   If discovery has not refreshed, restart the agent app or read the installed
   skill directly for the current session.

Installer options:

```sh
python3 install.py --target claude --data-dir '/path/to/My learning'
python3 install.py --target codex --skills-dir /path/to/agent/skills
python3 install.py --target both --update
python3 install.py --package /tmp/learning-guide.zip
```

`--data-dir` is the parent of `courses/` and disposable `.runtime/`. By default,
both agents share `~/Fieldnotes/courses`, so switching agents keeps the history.
`FIELDNOTES_HOME` overrides the installed data parent for a session. Explicit
`--courses` and `--runtime` CLI options override these defaults.
An update preserves each installation's selected data folder unless changed
explicitly. It replaces recognized installed code only and refuses unrelated
skills or a skill folder containing `courses/`. Back up course folders as usual.
To uninstall, remove only the installed skill folder; learning records remain in
the separate data folder. Existing checkout courses are not moved automatically;
use `--data-dir /absolute/path/to/learning_harness` to keep using that checkout's
`courses/`, or select its parent with `--courses`.

## Claude in the browser or Cowork

Use the self-contained **learning-guide.zip**, not GitHub's “Download ZIP” source
archive. Published builds, when available, are on the repository's
[Releases page](https://github.com/ujjwalk906/learning_harness/releases).
If no release exists, a file-capable agent can download the source and run
`python3 install.py --package /tmp/learning-guide.zip`, then give that ZIP to the
user as a download.

In Claude, enable code execution/file creation, open **Customize → Skills →
+ → Create skill → Upload a skill**, upload the ZIP, and enable it. Then say:
“Use learning-guide. Help me learn [my goal].” Cowork users can select the skill
through the skill controls available in their account. The bundled tools need
the session's Python/filesystem access; reading the instructions alone is insufficient.

## ChatGPT and hosted agents

For **ChatGPT desktop with Work and local plugin support**, a local file-capable
agent can prepare the complete plugin and add it to the personal marketplace:

```sh
python3 install.py --target chatgpt
```

The installer preserves other marketplace entries, writes the plugin under
`~/.codex/plugins/fieldnotes`, and keeps learning records in `~/Fieldnotes/courses`.
Restart ChatGPT desktop, open **Plugins**, select the personal plugin source and
install **Fieldnotes**. Run its setup or ask it to help you learn. This is a local
plugin source, not publication to the public directory. Availability of personal
plugin sources depends on the client/account. Updates use `--target chatgpt --update`;
refresh/reinstall the plugin through the client so its cached copy is refreshed.
`--marketplace-root /path/to/workspace` prepares an isolated local marketplace
there instead of changing your personal source; use the host's supported local
marketplace controls to add that root. This is also useful for packaging QA.

In a file-capable ChatGPT/Codex environment, download the source, read the learning
skill, and use `learn.py` in that environment, or extract the portable ZIP and read
its `SKILL.md`. This works for that session without requiring global installation.
Use a supported persistent workspace for continuation. A generic file attachment
does not register a skill in every ChatGPT product; do not promise that it does.

ChatGPT Work distributes reusable skills through plugins. The desktop setup above
prepares that package and its local source; the user installs it through the app.
It does not publish to a directory. If the current surface cannot
write/run files, use a local agent or a supported skill/plugin installation flow.

Hosted files may be temporary. Help the user download their actual course folders
for safekeeping and restore them with `--courses /restored/course-parent`. The
dashboard is optional; keep teaching in chat if a usable port preview is absent.

## Finish setup in ordinary language

Tell the learner where their work is saved, how to return (“Continue my learning”),
and any actual storage limitation. Ask for a learning goal only if none is already
given. Begin a useful first step, without requiring a terminal, a full syllabus or
an entrance exam. Optional Jupyter/compiler setup can wait until an activity needs it.

Platform references (checked October 2026):
[OpenAI skill discovery](https://learn.chatgpt.com/docs/build-skills),
[ChatGPT plugin distribution](https://learn.chatgpt.com/docs/customization/overview),
[local plugin installation](https://developers.openai.com/plugins/build/plugins),
[Claude Code skills](https://code.claude.com/docs/en/skills), and
[Claude skill uploads](https://support.claude.com/en/articles/12512180-use-skills-in-claude).
