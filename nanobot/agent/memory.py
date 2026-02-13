"""Memory system for persistent agent memory."""

from pathlib import Path

from nanobot.utils.helpers import ensure_dir


class MemoryStore:
    """Two-layer memory: MEMORY.md (long-term facts) + HISTORY.md (grep-searchable log)."""

    def __init__(self, workspace: Path | str):
        base = Path(workspace)
        self.memory_dir = ensure_dir(base / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            with open(str(self.memory_file), encoding="utf-8") as f:
                return f.read()
        return ""

    def write_long_term(self, content: str) -> None:
        with open(str(self.memory_file), "w", encoding="utf-8") as f:
            f.write(content)

    def append_history(self, entry: str) -> None:
        with open(str(self.history_file), "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""
