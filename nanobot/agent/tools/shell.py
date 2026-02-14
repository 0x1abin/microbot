"""Shell execution tool for MicroPython embedded environment.

Since MicroPython has no shell or subprocess, this implements a mini
command interpreter (ls, cat, mkdir, rm, mv, cp, pwd, cd, free, df,
uname, tree, stat, head, wc, grep, freq, gc, modules, echo, touch,
curl) and direct Python code execution (prefix with ``py:``).
"""

import os
import sys
import gc

from nanobot.agent.tools.base import Tool


# Stat mode flag for directory
_IFDIR = 0x4000


class ExecTool(Tool):
    """Tool to execute commands in a MicroPython embedded environment."""

    _DENY_CMDS = {"reset", "reboot", "format"}

    def __init__(
        self,
        timeout=60,
        working_dir=None,
        deny_patterns=None,
        allow_patterns=None,
        restrict_to_workspace=False,
    ):
        self.timeout = timeout
        self.working_dir = working_dir or os.getcwd()
        self.restrict_to_workspace = restrict_to_workspace
        # deny_patterns / allow_patterns kept for interface compatibility

    @property
    def name(self):
        return "exec"

    @property
    def description(self):
        return (
            "Execute a command in the MicroPython environment. "
            "Built-in commands: ls, cat, mkdir, rm, rmdir, mv, cp, pwd, cd, "
            "free, df, uname, tree, stat, head, wc, grep, echo, touch, freq, "
            "gc, modules, curl.  Prefix with 'py:' to run arbitrary MicroPython code."
        )

    @property
    def parameters(self):
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Command to execute. Use shell-like syntax or "
                        "'py: <code>' for MicroPython code execution."
                    ),
                },
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        }

    async def execute(self, command, working_dir=None, **kwargs):
        cwd = working_dir or self.working_dir or os.getcwd()
        cmd = command.strip()

        if not cmd:
            return "Error: empty command"

        # Python code execution: py: <code> or python: <code>
        if cmd.startswith("py:") or cmd.startswith("python:"):
            code = cmd.split(":", 1)[1].strip()
            return self._exec_python(code)

        # Parse command and arguments
        parts = _split_cmd(cmd)
        name = parts[0].lower()
        args = parts[1:]

        # Safety guard
        if name in self._DENY_CMDS:
            return "Error: command blocked by safety guard"

        # Workspace restriction: reject .. traversal
        if self.restrict_to_workspace:
            for a in args:
                if ".." in a:
                    return "Error: path traversal blocked by safety guard"

        handler = _HANDLERS.get(name)
        if handler is None:
            # Fallback: try as Python expression
            return self._exec_python(cmd)

        try:
            return handler(self, args, cwd)
        except Exception as e:
            return "Error: %s" % str(e)

    # ------------------------------------------------------------------ #
    #  Python code execution                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _exec_python(code):
        """Execute Python code and capture printed output."""
        import io

        buf = io.StringIO()

        # Redirect sys.stdout if available (not all MicroPython ports have it)
        old_stdout = None
        can_redirect = False
        try:
            old_stdout = sys.stdout
            sys.stdout = buf
            can_redirect = True
        except AttributeError:
            pass

        # Custom print fallback when sys.stdout is unavailable
        def _print(*args, **kwargs):
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            buf.write(sep.join(str(a) for a in args) + end)

        try:
            # Try eval first so expressions return a value
            try:
                result = eval(code)
                if result is not None:
                    if can_redirect:
                        print(repr(result))
                    else:
                        buf.write(repr(result) + '\n')
            except SyntaxError:
                if can_redirect:
                    exec(code)
                else:
                    # Inject custom print into exec namespace
                    exec(code, {'print': _print})
            output = buf.getvalue()
            if len(output) > 4096:
                output = output[:4096] + "\n... (truncated)"
            return output if output else "(no output)"
        except Exception as e:
            return "Error: %s: %s" % (type(e).__name__, str(e))
        finally:
            if can_redirect:
                sys.stdout = old_stdout


# ====================================================================== #
#  Helper utilities                                                       #
# ====================================================================== #

def _resolve(path, cwd):
    """Resolve *path* relative to *cwd*."""
    if path.startswith("/"):
        return path
    return cwd.rstrip("/") + "/" + path


def _split_cmd(cmd):
    """Lightweight command-line splitter with quote support."""
    parts = []
    cur = []
    quote = None
    for ch in cmd:
        if quote:
            if ch == quote:
                quote = None
            else:
                cur.append(ch)
        elif ch in ('"', "'"):
            quote = ch
        elif ch == " ":
            if cur:
                parts.append("".join(cur))
                cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts or [""]


def _is_dir(path):
    """Return True if *path* is a directory."""
    try:
        return (os.stat(path)[0] & _IFDIR) != 0
    except OSError:
        return False


# ====================================================================== #
#  Built-in command implementations                                       #
# ====================================================================== #

def _cmd_ls(self, args, cwd):
    """List directory contents with type/size indicators."""
    show_all = False
    path = cwd
    for a in args:
        if a == "-a":
            show_all = True
        else:
            path = _resolve(a, cwd)

    try:
        entries = sorted(os.listdir(path))
    except OSError as e:
        return "Error: %s" % str(e)

    if not show_all:
        entries = [n for n in entries if not n.startswith(".")]

    lines = []
    for name in entries:
        full = path.rstrip("/") + "/" + name
        try:
            st = os.stat(full)
            is_d = (st[0] & _IFDIR) != 0
            lines.append("%s %7d  %s" % ("d" if is_d else "-", st[6], name))
        except OSError:
            lines.append("?        ?  %s" % name)
    return "\n".join(lines) if lines else "(empty directory)"


def _cmd_cat(self, args, cwd):
    """Read and return file contents (max 4 KiB)."""
    if not args:
        return "Usage: cat <file>"
    path = _resolve(args[0], cwd)
    try:
        with open(path, "r") as f:
            content = f.read(4097)
            if len(content) > 4096:
                content = content[:4096] + "\n... (truncated)"
        return content
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_mkdir(self, args, cwd):
    """Create a directory. Supports -p flag for recursive creation."""
    if not args:
        return "Usage: mkdir [-p] <path>"
    # Parse -p flag
    parents = False
    paths = []
    for a in args:
        if a == "-p":
            parents = True
        else:
            paths.append(a)
    if not paths:
        return "Usage: mkdir [-p] <path>"
    path = _resolve(paths[0], cwd)
    try:
        if parents:
            os.makedirs(path, exist_ok=True)
        else:
            os.mkdir(path)
        return "Created: %s" % path
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_rm(self, args, cwd):
    """Remove a file."""
    if not args:
        return "Usage: rm <file>"
    path = _resolve(args[0], cwd)
    # Refuse to rm directories (use rmdir)
    if _is_dir(path):
        return "Error: %s is a directory (use rmdir)" % path
    try:
        os.remove(path)
        return "Removed: %s" % path
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_rmdir(self, args, cwd):
    """Remove an empty directory."""
    if not args:
        return "Usage: rmdir <path>"
    path = _resolve(args[0], cwd)
    try:
        os.rmdir(path)
        return "Removed directory: %s" % path
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_mv(self, args, cwd):
    """Rename / move a file or directory."""
    if len(args) < 2:
        return "Usage: mv <src> <dst>"
    src = _resolve(args[0], cwd)
    dst = _resolve(args[1], cwd)
    try:
        os.rename(src, dst)
        return "Moved: %s -> %s" % (src, dst)
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_cp(self, args, cwd):
    """Copy a file using a small buffer (512 bytes)."""
    if len(args) < 2:
        return "Usage: cp <src> <dst>"
    src = _resolve(args[0], cwd)
    dst = _resolve(args[1], cwd)
    try:
        buf = bytearray(512)
        with open(src, "rb") as sf, open(dst, "wb") as df:
            while True:
                n = sf.readinto(buf)
                if not n:
                    break
                df.write(buf[:n])
        return "Copied: %s -> %s" % (src, dst)
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_pwd(self, args, cwd):
    """Print current working directory."""
    return os.getcwd()


def _cmd_cd(self, args, cwd):
    """Change working directory."""
    target = _resolve(args[0], cwd) if args else "/"
    try:
        os.chdir(target)
        self.working_dir = os.getcwd()
        return self.working_dir
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_free(self, args, cwd):
    """Show RAM usage after a GC sweep."""
    gc.collect()
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    total = free + alloc
    return (
        "Memory:\n"
        "  Total : %d bytes\n"
        "  Used  : %d bytes (%.1f%%)\n"
        "  Free  : %d bytes (%.1f%%)"
        % (total, alloc, alloc * 100 / total, free, free * 100 / total)
    )


def _cmd_df(self, args, cwd):
    """Show filesystem usage (via os.statvfs)."""
    path = args[0] if args else "/"
    try:
        st = os.statvfs(path)
        bsize = st[0]
        total = bsize * st[2]
        free = bsize * st[3]
        used = total - free
        pct = used * 100 / total if total else 0
        return (
            "Filesystem: %s\n"
            "  Block size: %d\n"
            "  Total : %d bytes\n"
            "  Used  : %d bytes (%.1f%%)\n"
            "  Free  : %d bytes (%.1f%%)"
            % (path, bsize, total, used, pct, free, 100 - pct)
        )
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_uname(self, args, cwd):
    """Show platform / firmware information."""
    info = os.uname()
    lines = [
        "System  : %s" % info.sysname,
        "Node    : %s" % info.nodename,
        "Release : %s" % info.release,
        "Version : %s" % info.version,
        "Machine : %s" % info.machine,
        "Python  : %s" % sys.version,
        "Platform: %s" % sys.platform,
    ]
    return "\n".join(lines)


def _cmd_tree(self, args, cwd):
    """Show directory tree (max depth 3)."""
    path = _resolve(args[0], cwd) if args else cwd

    lines = []

    def _walk(p, prefix, depth):
        if depth > 3:
            return
        try:
            entries = sorted(os.listdir(p))
        except OSError:
            lines.append(prefix + "(cannot read)")
            return
        for i, name in enumerate(entries):
            last = i == len(entries) - 1
            connector = "└── " if last else "├── "
            lines.append(prefix + connector + name)
            full = p.rstrip("/") + "/" + name
            if _is_dir(full):
                ext = "    " if last else "│   "
                _walk(full, prefix + ext, depth + 1)

    _walk(path, "", 0)
    return "\n".join(lines) if lines else "(empty)"


def _cmd_stat(self, args, cwd):
    """Show file / directory metadata."""
    if not args:
        return "Usage: stat <path>"
    path = _resolve(args[0], cwd)
    try:
        st = os.stat(path)
        is_d = (st[0] & _IFDIR) != 0
        return (
            "Path : %s\n"
            "Type : %s\n"
            "Size : %d bytes\n"
            "Mode : 0x%04x"
            % (path, "directory" if is_d else "file", st[6], st[0])
        )
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_echo(self, args, cwd):
    """Echo text; supports ``> file`` redirect."""
    if ">" in args:
        idx = args.index(">")
        text = " ".join(args[:idx])
        if idx + 1 < len(args):
            path = _resolve(args[idx + 1], cwd)
            try:
                with open(path, "w") as f:
                    f.write(text + "\n")
                return "Wrote to %s" % path
            except OSError as e:
                return "Error: %s" % str(e)
    return " ".join(args)


def _cmd_touch(self, args, cwd):
    """Create an empty file (or update access)."""
    if not args:
        return "Usage: touch <file>"
    path = _resolve(args[0], cwd)
    try:
        with open(path, "a"):
            pass
        return "Touched: %s" % path
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_head(self, args, cwd):
    """Show first N lines of a file (default 10)."""
    n = 10
    path = None
    for a in args:
        if a.startswith("-"):
            try:
                n = int(a[1:])
            except ValueError:
                pass
        else:
            path = a
    if not path:
        return "Usage: head [-N] <file>"
    path = _resolve(path, cwd)
    try:
        result = []
        with open(path, "r") as f:
            for _ in range(n):
                line = f.readline()
                if not line:
                    break
                result.append(line.rstrip("\n"))
        return "\n".join(result)
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_wc(self, args, cwd):
    """Count lines, words, and characters in a file."""
    if not args:
        return "Usage: wc <file>"
    path = _resolve(args[0], cwd)
    try:
        lines = words = chars = 0
        with open(path, "r") as f:
            for line in f:
                lines += 1
                words += len(line.split())
                chars += len(line)
        return "%d lines  %d words  %d chars  %s" % (lines, words, chars, args[0])
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_grep(self, args, cwd):
    """Simple substring search in a file (max 100 matches)."""
    if len(args) < 2:
        return "Usage: grep <pattern> <file>"
    pattern = args[0]
    path = _resolve(args[1], cwd)
    try:
        results = []
        with open(path, "r") as f:
            for i, line in enumerate(f, 1):
                if pattern in line:
                    results.append("%d: %s" % (i, line.rstrip("\n")))
                    if len(results) >= 100:
                        results.append("... (truncated at 100 matches)")
                        break
        return "\n".join(results) if results else "(no matches)"
    except OSError as e:
        return "Error: %s" % str(e)


def _cmd_freq(self, args, cwd):
    """Get or set CPU frequency (Hz)."""
    try:
        import machine
    except ImportError:
        return "Error: machine module not available"
    if args:
        try:
            hz = int(args[0])
            machine.freq(hz)
            return "CPU frequency set to %d Hz" % hz
        except (ValueError, OSError) as e:
            return "Error: %s" % str(e)
    return "CPU frequency: %d Hz" % machine.freq()


def _cmd_gc(self, args, cwd):
    """Force garbage collection and report results."""
    gc.collect()
    return "GC done. Free: %d bytes, Alloc: %d bytes" % (
        gc.mem_free(),
        gc.mem_alloc(),
    )


def _cmd_modules(self, args, cwd):
    """List currently loaded modules."""
    names = sorted(sys.modules.keys())
    return "Loaded modules (%d):\n%s" % (len(names), "\n".join(names))


def _cmd_curl(self, args, cwd):
    """Lightweight HTTP client (curl subset)."""
    from nanobot.utils.curl import curl
    return curl(args, cwd)


# ====================================================================== #
#  Handler dispatch table (built once at import time)                      #
# ====================================================================== #

_HANDLERS = {
    "ls": _cmd_ls,
    "dir": _cmd_ls,
    "cat": _cmd_cat,
    "mkdir": _cmd_mkdir,
    "rm": _cmd_rm,
    "rmdir": _cmd_rmdir,
    "mv": _cmd_mv,
    "cp": _cmd_cp,
    "pwd": _cmd_pwd,
    "cd": _cmd_cd,
    "free": _cmd_free,
    "df": _cmd_df,
    "uname": _cmd_uname,
    "tree": _cmd_tree,
    "stat": _cmd_stat,
    "echo": _cmd_echo,
    "touch": _cmd_touch,
    "head": _cmd_head,
    "wc": _cmd_wc,
    "grep": _cmd_grep,
    "freq": _cmd_freq,
    "gc": _cmd_gc,
    "modules": _cmd_modules,
    "curl": _cmd_curl,
}
