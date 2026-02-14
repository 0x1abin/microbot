"""Path compatibility for MicroPython: extend stdlib Path with missing methods."""

from pathlib import Path as _Path
import os

class Path(_Path):
    """
    Path subclass that adds missing methods for MicroPython compatibility.
    Overrides parent and __truediv__ so derived paths stay as this class.
    """

    def iterdir(self):
        """Iterate over directory entries; compatible with MicroPython."""
        for name in os.listdir(str(self)):
            yield self / name

    def expanduser(self):
        """Expand ~ to home directory. Return self unchanged if HOME is
        not available (common on embedded MicroPython)."""
        p = str(self)
        if p.startswith("~"):
            home = os.getenv("HOME") if hasattr(os, "getenv") else None
            if home:
                return type(self)(home + p[1:])
        return self

    def resolve(self):
        """Return an absolute Path object."""
        return type(self)(super().resolve())

    @property
    def parent(self) -> "Path":
        """Return parent path as Path subclass."""
        return type(self)(super().parent)

    def __truediv__(self, other) -> "Path":
        """Return joined path as Path subclass."""
        return type(self)(super().__truediv__(other))
