"""
Shared path utilities for resource and data file resolution.
"""

import sys
import os


def app_dir() -> str:
    """Directory for user data files (config.json, *.db)."""
    if getattr(sys, "frozen", False):
        if "ANDROID_PRIVATE" in os.environ:
            return os.environ["ANDROID_PRIVATE"]
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def resource_dir() -> str:
    """Directory for bundled resources (cat.jpg). Inside exe when frozen."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def icon_path() -> str:
    """Return the path to cat.jpg if it exists (resource dir first, then app dir)."""
    for base in (resource_dir(), app_dir()):
        p = os.path.join(base, "cat.jpg")
        if os.path.isfile(p):
            return p
    return ""
