from sys import platform, version

def system() -> str:
    return 'Embedded system'

def machine() -> str:
    return platform

def python_version() -> str:
    return version