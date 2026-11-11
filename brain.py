"""Plup's brains. A brain takes a user message and streams events back:

    emit("text", str)        a chunk of reply text
    emit("break", None)      a new assistant message starts (after tool use)
    emit("tool", str)        a short description of a tool Plup is using
    emit("done", dict)       the turn finished (cost, duration, ...)
    emit("error", str)       something went wrong

To add another LLM, subclass Brain, implement send(), and register it in BRAINS.
"""
import json
import os
import shutil
import signal
import subprocess
import threading

PERSONA = (
    "You are Plup, a tiny, cheerful 16-bit pixel-art penguin who lives on the user's "
    "Linux desktop as their helper buddy (think Windows XP desktop buddies, but actually "
    "useful). You can really do things on the user's computer with your tools: run "
    "commands, read and edit files, search the web, and so on. Your replies show up in a "
    "small MS-DOS style text console next to you, so keep them short and friendly: "
    "a few sentences, plain language, light markdown at most, and no emoji (the "
    "console font can't show them). A little penguin charm is welcome, but "
    "never at the cost of being genuinely helpful. When you finish a task, say plainly "
    "what you did."
)


class Brain:
    name = "brain"

    def send(self, prompt, emit):
        """Blocking; called from a worker thread."""
        raise NotImplementedError

    def cancel(self):
        pass

    def reset(self):
        pass

    def configure(self, cfg):
        """Pick up changed settings (model, permissions, folder...)."""


def _summarize_tool(name, inp):
    inp = inp or {}
    detail = (inp.get("command") or inp.get("file_path") or inp.get("pattern")
              or inp.get("url") or inp.get("query") or inp.get("description") or "")
    detail = " ".join(str(detail).split())
    if len(detail) > 70:
        detail = detail[:67] + "..."
    return f"{name}: {detail}" if detail else name


class ClaudeCodeBrain(Brain):
    """Runs the Claude Code CLI headless, so Plup gets Claude's full agent toolset."""
    name = "Claude"

    def __init__(self, cfg):
        self.session_id = None
        self.proc = None
        self.configure(cfg)

    def configure(self, cfg):
        self.exe = (cfg.get("claude_path") or shutil.which("claude")
                    or os.path.expanduser("~/.local/bin/claude"))
        self.model = cfg.get("model") or None
        self.permission_mode = cfg.get("permission_mode") or "auto"
        self.cwd = os.path.expanduser(cfg.get("cwd") or "~")

    def reset(self):
        self.session_id = None

    def cancel(self):
        if self.proc and self.proc.poll() is None:
            try:
                os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def send(self, prompt, emit):
        cmd = [self.exe, "-p", "--output-format", "stream-json", "--verbose",
               "--include-partial-messages", "--permission-mode", self.permission_mode,
               "--append-system-prompt", PERSONA]
        if self.model:
            cmd += ["--model", self.model]
        if self.session_id:
            cmd += ["--resume", self.session_id]

        self.proc = proc = subprocess.Popen(
            cmd, cwd=self.cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, start_new_session=True)
        stderr_tail = []
        threading.Thread(target=lambda: stderr_tail.extend(proc.stderr), daemon=True).start()
        proc.stdin.write(prompt)
        proc.stdin.close()

        got_text = False
        finished = False
        for line in proc.stdout:
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("session_id"):
                self.session_id = msg["session_id"]
            if msg.get("parent_tool_use_id"):
                continue  # chatter from subagents
            kind = msg.get("type")
            if kind == "stream_event":
                ev = msg.get("event", {})
                if ev.get("type") == "message_start" and got_text:
                    emit("break", None)
                elif ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta":
                        got_text = True
                        emit("text", delta.get("text", ""))
            elif kind == "assistant":
                for block in msg.get("message", {}).get("content", []):
                    if block.get("type") == "tool_use":
                        emit("tool", _summarize_tool(block.get("name", "tool"), block.get("input")))
            elif kind == "result":
                finished = True
                if msg.get("is_error"):
                    emit("error", str(msg.get("result") or msg.get("subtype") or "unknown error"))
                else:
                    emit("done", {"cost": msg.get("total_cost_usd"),
                                  "seconds": (msg.get("duration_ms") or 0) / 1000})
        rc = proc.wait()
        self.proc = None
        if not finished and rc not in (0, -signal.SIGTERM):
            tail = "".join(stderr_tail[-5:]).strip()
            emit("error", tail or f"claude exited with code {rc}")


BRAINS = {"claude-code": ClaudeCodeBrain}


def make_brain(cfg):
    return BRAINS[cfg.get("brain", "claude-code")](cfg)
