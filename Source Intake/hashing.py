#!/usr/bin/env python3
"""
hashing.py

Japanese Corpus Pipeline - Source Intake (utility layer)

SHA-256 file hashing only.

Deterministic: identical file content always produces the identical hash.
This module does not own artifacts, does not create metadata, and does
not know the meaning of any source.
"""

import sys
from pathlib import Path

# Allow imports from the project root (project convention).
sys.path.append(str(Path(__file__).resolve().parent.parent))

from common import sha256_file as _sha256_file


def sha256_file(file_path):
    """
    Return the lowercase hex SHA-256 digest of a file.

    Input:
        file_path: path to the file to hash.

    Output:
        64-character lowercase hexadecimal string.

    Reuses the project's shared hashing utility (common.sha256_file).
    """
    return _sha256_file(file_path)


__all__ = ["sha256_file"]
