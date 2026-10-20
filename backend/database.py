import os
from pathlib import Path

from sqlalchemy import URL, create_engine, event
from sqlalchemy.engine import Engine

DB_PATH = Path(os.environ.get("FAIRTOY_DB", Path(__file__).resolve().parents[1] / "fairtoy.db"))


def make_engine(db_path: str | Path) -> Engine:
    path = Path(db_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        URL.create("sqlite", database=path.as_posix()),
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def configure_connection(connection, _):
        # Let SQLAlchemy start real transactions for reads as well as writes.
        connection.isolation_level = None
        connection.execute("PRAGMA foreign_keys = ON")

    @event.listens_for(engine, "begin")
    def begin_transaction(connection):
        connection.exec_driver_sql("BEGIN")

    return engine
