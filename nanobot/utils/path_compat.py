"""Path compatibility for MicroPython: stdlib Path may lack iterdir()."""

from pathlib import Path as _Path
import os

class Path(_Path):
    """
    Path subclass that implements iterdir() using os.listdir().
    Use this instead of pathlib.Path when running on MicroPython.
    Overrides parent and __truediv__ so derived paths stay as this class.
    """

    def iterdir(self):
        """Iterate over directory entries; compatible with MicroPython."""
        for name in os.listdir(str(self)):
            yield self / name

    @property
    def parent(self) -> "Path":
        """Return parent path as Path subclass."""
        return type(self)(super().parent)

    def __truediv__(self, other) -> "Path":
        """Return joined path as Path subclass."""
        return type(self)(super().__truediv__(other))
