"""Academy Student Progress Tracker backend.

Company requirement: the project runs on Python 3.11 only. Python
imports this file before any other module of the package, so the
check below protects the server, the tests and every script.
"""

import sys

REQUIRED_PYTHON = (3, 11)

if sys.version_info[:2] != REQUIRED_PYTHON:
    raise RuntimeError(
        "This project requires Python 3.11 (company requirement), "
        f"but it is running on Python {sys.version.split()[0]}. "
        "See 'Python version (restricted)' in README.md."
    )
