"""Agent directory resolution.

The kit never assumes a name. Resolution order:
  1. $MIND_AGENT_DIR
  2. --agent-dir on the command line
  3. ./agent  (relative to the kit root)
"""
from __future__ import annotations
import os, sys
from pathlib import Path


def agent_dir() -> Path:
    for i, arg in enumerate(sys.argv):
        if arg == "--agent-dir" and i + 1 < len(sys.argv):
            return Path(sys.argv[i + 1]).expanduser().resolve()
        if arg.startswith("--agent-dir="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    env = os.environ.get("MIND_AGENT_DIR")
    if env:
        return Path(env).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / "agent")
