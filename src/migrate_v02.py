"""Explicit additive v0.1 → v0.2 migration; never runs on application import."""
from sqlalchemy import inspect, text
from sqlalchemy.dialects.postgresql import ENUM

from src.database import create_db_engine
from src.models import ApprovalStatus


def upgrade(connection):
    if connection.dialect.name != "postgresql":
        raise RuntimeError("The v0.2 migration requires PostgreSQL")
    if not {'users', 'rooms', 'reservations'}.issubset(inspect(connection).get_table_names()):
        raise RuntimeError("Initialize a new database with src.init_db, or supply a v0.1 database")
    ENUM(*(status.value for status in ApprovalStatus), name='approval_status').create(
        connection, checkfirst=True)
    connection.execute(text('''ALTER TABLE rooms
        ADD COLUMN IF NOT EXISTS requires_approval boolean NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS approver_user_id integer REFERENCES users(id)'''))
    connection.execute(text('''ALTER TABLE reservations
        ADD COLUMN IF NOT EXISTS approval_decision approval_status NOT NULL DEFAULT 'NOT_REQUIRED',
        ADD COLUMN IF NOT EXISTS approval_deadline timestamptz,
        ADD COLUMN IF NOT EXISTS decided_by integer REFERENCES users(id),
        ADD COLUMN IF NOT EXISTS decided_at timestamptz'''))


def main():
    engine = create_db_engine()
    try:
        with engine.begin() as connection:
            upgrade(connection)
        print('v0.2 columns ready; existing reservations retain NOT_REQUIRED approval.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
