#!/usr/bin/env python3
"""Run the repository's project verification suite with a configured DATABASE_URL.

This repository keeps the C08 approval-timeout proposal in DEFER / NO_CHANGE
state until a product owner accepts a new policy. The automation below is the
repeatable check path for the current production baseline.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print(
            "DATABASE_URL is required before running the project verification suite.",
            file=sys.stderr,
        )
        print(
            "Example: export DATABASE_URL='postgresql+psycopg://postgres@localhost:5432/study_room_app'",
            file=sys.stderr,
        )
        print("Add PGPASSWORD if the local PostgreSQL role requires it.", file=sys.stderr)
        return 2

    # Keep the automation narrow: the project's test suite is the release gate.
    command = [sys.executable, "-m", "pytest", "tests", "-v", "--tb=short"]
    result = subprocess.run(command, cwd=str(ROOT))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
