#!/usr/bin/env python3
"""
project_audit.py

Japanese Corpus Pipeline

Project Audit Utility

This utility NEVER modifies the project.

Its purpose is to inspect the project structure,
configuration and pipeline health, then produce
a diagnostic report.

Version 1 audits:

    • System information
    • Project folders
    • Python modules
    • Configuration
    • Imports
    • Data folders
    • Overall health

Future versions will also audit:

    • Jobs
    • Responses
    • Corpus integrity
    • API statistics
    • Performance
"""

import sys
import platform
from pathlib import Path
from datetime import datetime

# ------------------------------------------------------------
# Allow imports from project root
# ------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent

sys.path.append(str(PROJECT_ROOT))

from paths import (
    PROJECT_NAME,
    PROJECT_ROOT,
    DIAGNOSTICS,
    verify_paths,
)

from project_config import (
    PROJECT_VERSION,
    LOG_DATE_FORMAT,
)

from common import (
    ensure_folder,
)

# ------------------------------------------------------------
# Program Information
# ------------------------------------------------------------

PROGRAM_NAME = "Project Audit"

AUDIT_VERSION = "1.0"

REPORT_FOLDER = DIAGNOSTICS

STATUS_HEALTHY = "HEALTHY"
STATUS_WARNING = "WARNING"
STATUS_FAILED = "FAILED"
# ============================================================
# Audit Result
# ============================================================

class AuditResult:
    """
    Represents the results of one audit section.
    """

    def __init__(self, title):

        self.title = title

        self.lines = []

        self.warnings = []

        self.errors = []

    def add(self, text):

        self.lines.append(text)

    def warning(self, text):

        self.warnings.append(text)

    def error(self, text):

        self.errors.append(text)

    @property
    def warning_count(self):

        return len(self.warnings)

    @property
    def error_count(self):

        return len(self.errors)


# ============================================================
# Report Builder
# ============================================================

class AuditReport:
    """
    Collects all audit sections into one report.
    """

    def __init__(self):

        self.sections = []

    def add_section(self, section):

        self.sections.append(section)

    @property
    def warning_count(self):

        return sum(
            section.warning_count
            for section in self.sections
        )

    @property
    def error_count(self):

        return sum(
            section.error_count
            for section in self.sections
        )

    @property
    def status(self):

        if self.error_count:
            return STATUS_FAILED

        if self.warning_count:
            return STATUS_WARNING

        return STATUS_HEALTHY
    # ============================================================
# System Information Audit
# ============================================================

def audit_system_information():
    """
    Gather basic information about the current system.
    """

    result = AuditResult(
        "System Information"
    )

    result.add(
        f"Project           : {PROJECT_NAME}"
    )

    result.add(
        f"Project Version   : {PROJECT_VERSION}"
    )

    result.add(
        f"Audit Version     : {AUDIT_VERSION}"
    )

    result.add(
        f"Python Version    : {platform.python_version()}"
    )

    result.add(
        f"Operating System  : "
        f"{platform.system()} "
        f"{platform.release()}"
    )

    result.add(
        f"Machine           : "
        f"{platform.machine()}"
    )

    result.add(
        f"Report Date       : "
        f"{datetime.now().strftime(LOG_DATE_FORMAT)}"
    )

    result.add(
        f"Project Root      : "
        f"{PROJECT_ROOT}"
    )

    return result
# ============================================================
# Report Writer
# ============================================================

def write_audit_report(report):
    """
    Write the completed audit report to disk.
    """

    ensure_folder(
        REPORT_FOLDER
    )

    report_file = (
        REPORT_FOLDER
        / (
            "Project_Audit_"
            + datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            + ".txt"
        )
    )

    with report_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        f.write(
            "=" * 60 + "\n"
        )

        f.write(
            f"{PROJECT_NAME}\n"
        )

        f.write(
            "PROJECT AUDIT\n"
        )

        f.write(
            "=" * 60 + "\n\n"
        )

        f.write(
            f"Overall Status : {report.status}\n"
        )

        f.write(
            f"Warnings       : {report.warning_count}\n"
        )

        f.write(
            f"Errors         : {report.error_count}\n\n"
        )

        for section in report.sections:

            f.write(
                "-" * 60 + "\n"
            )

            f.write(
                section.title.upper()
                + "\n"
            )

            f.write(
                "-" * 60 + "\n\n"
            )

            for line in section.lines:

                f.write(
                    line + "\n"
                )

            if section.warnings:

                f.write("\nWarnings\n")

                for warning in section.warnings:

                    f.write(
                        f"  • {warning}\n"
                    )

            if section.errors:

                f.write("\nErrors\n")

                for error in section.errors:

                    f.write(
                        f"  • {error}\n"
                    )

            f.write("\n")

    return report_file
# ============================================================
# Project Structure Audit
# ============================================================

def audit_project_structure():
    """
    Verify that the expected project folders exist.
    """

    result = AuditResult(
        "Project Structure"
    )

    expected_folders = [

        "Common",

        "Transcript Cleaner",

        "Subtitle Cleaner",

        "Data Processor",

        "Prompts",

        "Logs",

        "Diagnostics",

    ]

    for folder_name in expected_folders:

        folder = PROJECT_ROOT / folder_name

        if folder.exists():

            result.add(
                f"✓ {folder_name}"
            )

        else:

            result.error(
                f"Missing folder: {folder_name}"
            )

    return result
# ============================================================
# Python Module Audit
# ============================================================

def audit_python_modules():
    """
    Discover every Python module in the project.
    """

    result = AuditResult(
        "Python Modules"
    )

    modules = sorted(
        PROJECT_ROOT.rglob("*.py")
    )

    seen = {}

    for module in modules:

        relative = module.relative_to(
            PROJECT_ROOT
        )

        result.add(
            f"✓ {relative}"
        )

        name = module.name

        if name not in seen:
            seen[name] = []

        seen[name].append(relative)

    for name, locations in seen.items():

        if len(locations) > 1:

            result.warning(
                f"Duplicate module: {name}"
            )

            for location in locations:

                result.warning(
                    f"    {location}"
                )

    return result
# ============================================================
# Run All Audits
# ============================================================

def run_all_audits():
    """
    Execute every audit and collect the results.
    """

    report = AuditReport()

    audits = [

        audit_system_information,

        audit_project_structure,

        audit_python_modules,

    ]

    for audit in audits:

        try:

            section = audit()

            report.add_section(
                section
            )

        except Exception as ex:

            failed = AuditResult(
                audit.__name__
            )

            failed.error(
                f"Audit failed: {ex}"
            )

            report.add_section(
                failed
            )

    return report
# ============================================================
# Main Program
# ============================================================

def main():
    """
    Run the complete project audit.
    """

    verify_paths()

    report = run_all_audits()

    report_file = write_audit_report(
        report
    )

    print()

    print("=" * 60)

    print(PROGRAM_NAME)

    print("=" * 60)

    print()

    print(
        f"Status   : {report.status}"
    )

    print(
        f"Warnings : {report.warning_count}"
    )

    print(
        f"Errors   : {report.error_count}"
    )

    print()

    print(
        "Report written:"
    )

    print(
        f"  {report_file}"
    )

    print()

    input(
        "Press Enter to exit..."
    )


# ============================================================
# Program Entry Point
# ============================================================

if __name__ == "__main__":
    main()
    