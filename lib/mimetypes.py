"""
MicroPython mimetypes module - Minimal implementation
Provides basic mapping between file extensions and MIME types
"""

# Common MIME type mappings (minimal version)
_types_map = {
    # Text types
    '.txt': 'text/plain',
    '.html': 'text/html',
    '.htm': 'text/html',
    '.css': 'text/css',
    '.csv': 'text/csv',
    '.xml': 'text/xml',
    
    # Application types
    '.json': 'application/json',
    '.js': 'application/javascript',
    '.pdf': 'application/pdf',
    '.zip': 'application/zip',
    '.gz': 'application/gzip',
    '.bin': 'application/octet-stream',
    
    # Image types
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.bmp': 'image/bmp',
    '.ico': 'image/x-icon',
    '.svg': 'image/svg+xml',
    '.webp': 'image/webp',
    
    # Audio types
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    
    # Video types
    '.mp4': 'video/mp4',
    '.avi': 'video/x-msvideo',
    '.mpeg': 'video/mpeg',
    '.webm': 'video/webm',
    
    # Font types
    '.ttf': 'font/ttf',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
}

# Reverse mapping (MIME type to extension)
_extensions_map = None


def _init_extensions_map():
    """Initialize reverse extension mapping"""
    global _extensions_map
    if _extensions_map is None:
        _extensions_map = {}
        for ext, mime in _types_map.items():
            if mime not in _extensions_map:
                _extensions_map[mime] = ext


def guess_type(url, strict=True):
    """
    Guess MIME type based on filename or URL
    
    Args:
        url: Filename or URL string
        strict: Compatibility parameter (unused in minimal version)
    
    Returns:
        (type, encoding) tuple, encoding is always None in minimal version
    """
    # Extract file extension
    if '?' in url:
        url = url.split('?')[0]
    
    # Find last dot
    dot_index = url.rfind('.')
    if dot_index == -1:
        return (None, None)
    
    # Get extension (convert to lowercase)
    ext = url[dot_index:].lower()
    
    # Look up MIME type
    mime_type = _types_map.get(ext)
    return (mime_type, None)


def guess_extension(mime_type, strict=True):
    """
    Guess file extension based on MIME type
    
    Args:
        mime_type: MIME type string
        strict: Compatibility parameter (unused in minimal version)
    
    Returns:
        Extension string (including dot), or None if not found
    """
    _init_extensions_map()
    return _extensions_map.get(mime_type.lower())


def add_type(mime_type, ext, strict=True):
    """
    Add custom MIME type mapping
    
    Args:
        mime_type: MIME type string
        ext: Extension (should include leading dot)
        strict: Compatibility parameter (unused in minimal version)
    """
    global _extensions_map
    
    # Ensure extension has leading dot
    if not ext.startswith('.'):
        ext = '.' + ext
    
    # Convert to lowercase
    ext = ext.lower()
    mime_type = mime_type.lower()
    
    # Add mapping
    _types_map[ext] = mime_type
    
    # Update reverse mapping
    if _extensions_map is not None:
        if mime_type not in _extensions_map:
            _extensions_map[mime_type] = ext


def init(files=None):
    """
    Initialize module (standard library compatibility)
    In minimal version, mappings are built-in, so this is a no-op
    """
    pass


# Common aliases (standard library compatibility)
guess = guess_type
