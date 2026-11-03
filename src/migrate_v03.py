"""Add queue cancellation attribution without rewriting historical reservations."""
from sqlalchemy import text
from src.database import create_db_engine
from src.migrate_v02 import upgrade as upgrade_v02


def upgrade(connection):
    upgrade_v02(connection)
    connection.execute(text('''ALTER TABLE reservations
        ADD COLUMN IF NOT EXISTS cancellation_reason varchar(100)'''))


def main():
    engine = create_db_engine()
    try:
        with engine.begin() as connection:
            upgrade(connection)
        print('v0.3 ready. Existing drafts retain ID order; existing bookings are preserved.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
