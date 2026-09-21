"""Create application tables explicitly: python -m src.init_db."""

from src.database import Base, create_db_engine
from src import models  # Register the shared tables on Base.metadata.


def main():
    engine = create_db_engine()
    try:
        Base.metadata.create_all(engine)
        print("Application tables are ready (existing tables are not migrated).")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
