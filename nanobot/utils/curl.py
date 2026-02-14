"""Lightweight curl implementation for MicroPython shell.

Supports common curl flags: -X, -H, -d, -o, -I, -v, -s, -k, -L.
Uses requests/urequests for HTTP transport.
"""

# Prefer requests; fallback to urequests (MicroPython)
try:
    import requests
except ImportError:
    import urequests as requests


_MAX_RESPONSE = 4096  # max bytes returned to shell output


def _parse_args(args):
    """Parse curl-style arguments into an options dict.

    Returns (opts, error_str | None).
    opts keys: method, headers, data, output, url, verbose, silent, head_only,
               insecure, follow.
    """
    opts = {
        "method": None,
        "headers": {},
        "data": None,
        "output": None,
        "url": None,
        "verbose": False,
        "silent": False,
        "head_only": False,
        "insecure": False,
        "follow": False,
    }

    i = 0
    while i < len(args):
        a = args[i]
        if a == "-X" or a == "--request":
            i += 1
            if i >= len(args):
                return opts, "-X requires a method argument"
            opts["method"] = args[i].upper()
        elif a == "-H" or a == "--header":
            i += 1
            if i >= len(args):
                return opts, "-H requires a header argument"
            hdr = args[i]
            if ":" not in hdr:
                return opts, "Invalid header (missing ':'): %s" % hdr
            k, v = hdr.split(":", 1)
            opts["headers"][k.strip()] = v.strip()
        elif a == "-d" or a == "--data":
            i += 1
            if i >= len(args):
                return opts, "-d requires a data argument"
            opts["data"] = args[i]
        elif a == "-o" or a == "--output":
            i += 1
            if i >= len(args):
                return opts, "-o requires a filename argument"
            opts["output"] = args[i]
        elif a == "-I" or a == "--head":
            opts["head_only"] = True
        elif a == "-v" or a == "--verbose":
            opts["verbose"] = True
        elif a == "-s" or a == "--silent":
            opts["silent"] = True
        elif a == "-k" or a == "--insecure":
            opts["insecure"] = True
        elif a == "-L" or a == "--location":
            opts["follow"] = True
        elif not a.startswith("-"):
            opts["url"] = a
        else:
            return opts, "Unknown option: %s" % a
        i += 1

    if not opts["url"]:
        return opts, None  # no URL yet, caller shows usage

    # Infer method from flags
    if opts["method"] is None:
        if opts["head_only"]:
            opts["method"] = "HEAD"
        elif opts["data"] is not None:
            opts["method"] = "POST"
        else:
            opts["method"] = "GET"

    return opts, None


def _format_headers(headers):
    """Format response headers dict to display string."""
    if not headers:
        return ""
    lines = []
    if isinstance(headers, dict):
        for k, v in headers.items():
            lines.append("< %s: %s" % (k, v))
    return "\n".join(lines)


def curl(args, cwd=None):
    """Execute a curl-like HTTP request.

    Args:
        args: list of string arguments (same as curl CLI flags).
        cwd: current working directory (for -o relative paths).

    Returns:
        String result suitable for shell output.
    """
    if not args:
        return (
            "Usage: curl [options] <url>\n"
            "Options:\n"
            "  -X METHOD   HTTP method (GET/POST/PUT/DELETE/PATCH/HEAD)\n"
            "  -H 'K: V'   Add request header\n"
            "  -d DATA     Request body (sets POST if -X not given)\n"
            "  -o FILE     Write response to file\n"
            "  -I          Show response headers only (HEAD)\n"
            "  -v          Verbose (show request/response headers)\n"
            "  -s          Silent (suppress status line)\n"
            "  -k          Allow insecure SSL\n"
            "  -L          Follow redirects"
        )

    opts, err = _parse_args(args)
    if err:
        return "Error: %s" % err
    if not opts["url"]:
        return "Error: no URL specified"

    url = opts["url"]
    method = opts["method"]
    headers = opts["headers"]
    data = opts["data"]
    verbose = opts["verbose"]
    silent = opts["silent"]

    # Build request kwargs
    kw = {"headers": headers} if headers else {}

    # Timeout
    kw["timeout"] = 30

    # Body
    if data is not None:
        # Auto-set Content-Type for JSON-like data
        if data.startswith("{") or data.startswith("["):
            headers.setdefault("Content-Type", "application/json")
        kw["headers"] = headers
        kw["data"] = data

    # Dispatch
    try:
        m = method.upper()
        if m == "GET":
            r = requests.get(url, **kw)
        elif m == "POST":
            r = requests.post(url, **kw)
        elif m == "PUT":
            r = requests.put(url, **kw)
        elif m == "DELETE":
            r = requests.delete(url, **kw)
        elif m == "HEAD":
            r = requests.head(url, **kw)
        elif m == "PATCH":
            r = requests.patch(url, **kw)
        else:
            return "Error: unsupported method '%s'" % m
    except Exception as e:
        return "Error: %s" % str(e)

    # Collect output parts
    parts = []
    status = getattr(r, "status_code", 0)
    reason = getattr(r, "reason", "")

    # Verbose: show request info
    if verbose:
        parts.append("> %s %s" % (method, url))
        for k, v in headers.items():
            parts.append("> %s: %s" % (k, v))
        parts.append(">")

    # Status line (unless silent)
    if not silent:
        parts.append("HTTP %s %s" % (status, reason))

    # Response headers (verbose or head-only)
    resp_hdrs = getattr(r, "headers", None)
    if (verbose or opts["head_only"]) and resp_hdrs:
        parts.append(_format_headers(resp_hdrs))

    # HEAD: no body needed
    if opts["head_only"]:
        _close_response(r)
        return "\n".join(parts)

    # Write to file
    if opts["output"]:
        return _save_to_file(r, opts["output"], cwd, parts)

    # Return body text
    try:
        body = r.text
    except Exception:
        body = str(getattr(r, "content", b""))

    _close_response(r)

    if len(body) > _MAX_RESPONSE:
        body = body[:_MAX_RESPONSE] + "\n... (truncated at %d bytes)" % _MAX_RESPONSE

    if parts:
        parts.append("")  # blank line before body
    parts.append(body)

    return "\n".join(parts)


def _save_to_file(r, filename, cwd, parts):
    """Save response body to a file."""
    import os

    if cwd and not filename.startswith("/"):
        filepath = cwd.rstrip("/") + "/" + filename
    else:
        filepath = filename

    try:
        body = getattr(r, "content", None)
        if body is None:
            body = (getattr(r, "text", "") or "").encode()
        with open(filepath, "wb") as f:
            f.write(body)
        _close_response(r)
        parts.append("Saved to: %s (%d bytes)" % (filepath, len(body)))
        return "\n".join(parts)
    except Exception as e:
        _close_response(r)
        return "Error writing file: %s" % str(e)


def _close_response(r):
    """Safely close the response object."""
    close = getattr(r, "close", None)
    if close:
        try:
            close()
        except Exception:
            pass
