#!/usr/bin/env python3
"""
common.py

Shared utility functions for the Japanese Corpus Pipeline.

This module contains only generic functions that can be safely
used by multiple project scripts.
"""

from pathlib import Path
from datetime import datetime
import hashlib
import json

from project_config import LOG_DATE_FORMAT


# ============================================================
# Display
# ============================================================

def divider(character="-", length=60):
    """Print a horizontal divider."""
    print(character * length)


def print_header(program_name, version):
    """Print the standard program header."""
    print("\n" + "=" * 60)
    print("Japanese Corpus Pipeline")
    print(program_name)
    print(f"Version {version}")
    print("=" * 60)


def print_footer():
    """Print the standard completion footer."""
    print("\n" + "=" * 60)
    print("Completed")
    print("=" * 60)


# ============================================================
# User Interaction
# ============================================================

def confirm(message):
    """
    Ask the user for confirmation.

    Returns:
        True if the user enters Y.
        False for any other response.
    """
    answer = input(f"\n{message} (Y/N): ").strip().lower()
    return answer == "y"


# ============================================================
# Dates and Times
# ============================================================

def timestamp():
    """Return the current date and time using the project format."""
    return datetime.now().strftime(LOG_DATE_FORMAT)


# ============================================================
# File and Folder Utilities
# ============================================================

def ensure_folder(folder):
    """
    Create a folder and any required parent folders.

    Does nothing if the folder already exists.
    """
    Path(folder).mkdir(parents=True, exist_ok=True)


def read_text_file(file_path):
    """
    Read a UTF-8 text file.

    UTF-8 BOM characters are handled automatically.
    """
    return Path(file_path).read_text(encoding="utf-8-sig")


def write_text_file(file_path, text):
    """Write UTF-8 text to a file."""
    Path(file_path).write_text(text, encoding="utf-8")


# ============================================================
# JSON Utilities
# ============================================================

def read_json(file_path):
    """Read and return JSON data from a file."""
    with Path(file_path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(file_path, data):
    """
    Write JSON using UTF-8 encoding and readable formatting.
    """
    file_path = Path(file_path)

    ensure_folder(file_path.parent)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4,
        )


# ============================================================
# Integrity
# ============================================================

def sha256_text(text):
    """
    Return the SHA-256 checksum of text encoded as UTF-8.
    """
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def sha256_file(file_path):
    """
    Return the SHA-256 checksum of a file.
    """
    sha256 = hashlib.sha256()

    with Path(file_path).open("rb") as file:
        for block in iter(lambda: file.read(65536), b""):
            sha256.update(block)

    return sha256.hexdigest()


# ============================================================
# Logging
# ============================================================

def write_log(log_file, content):
    """
    Write a UTF-8 log file.

    The parent folder is created automatically if necessary.
    """
    log_file = Path(log_file)

    ensure_folder(log_file.parent)

    log_file.write_text(
        content,
        encoding="utf-8",
    )


def build_log_header(program_name, version):
    """
    Create the standard beginning of a log file.
    """
    return (
        f"Program: {program_name}\n"
        f"Version: {version}\n"
        f"Date: {timestamp()}\n"
        "\n"
    )


# ============================================================
# Validation
# ============================================================

def require_file(file_path):
    """
    Verify that a required file exists.

    Raises:
        FileNotFoundError if the file does not exist.
    """
    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

    return file_path


def require_folder(folder):
    """
    Verify that a required folder exists.

    Raises:
        FileNotFoundError if the folder does not exist.
    """
    folder = Path(folder)

    if not folder.is_dir():
        raise FileNotFoundError(
            f"Required folder not found: {folder}"
        )

    return folder