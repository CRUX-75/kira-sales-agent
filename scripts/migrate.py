"""Apply pending SQL migrations to DATABASE_URL. Run from the repository root:

python scripts/migrate.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.infrastructure.migrations import apply_migrations  # noqa: E402


def main() -> None:
    dsn = get_settings().database_url
    if not dsn:
        sys.exit("DATABASE_URL is not set")
    applied = apply_migrations(dsn)
    print(f"Applied: {', '.join(applied)}" if applied else "Nothing to apply, schema is current.")


if __name__ == "__main__":
    main()
