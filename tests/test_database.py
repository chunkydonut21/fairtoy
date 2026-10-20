import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import make_engine
from backend.models import Base, Finisher, Supplier, SupplierFlag


class DatabaseTests(unittest.TestCase):
    def test_read_transaction_sees_one_snapshot_during_a_concurrent_write(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]) as folder:
            engine = make_engine(Path(folder) / "snapshot.db")
            try:
                Base.metadata.create_all(engine)
                with Session(engine) as session, session.begin():
                    session.add_all([
                        Finisher(id="F", name="Finisher", country="Country"),
                        Supplier(id="S", name="Supplier", country="Country"),
                    ])

                updated = Event()

                def write_flag():
                    with Session(engine) as session, session.begin():
                        session.add(SupplierFlag(
                            finisher_id="F", supplier_id="S", reason="Finding", flagged_at="2026-10-20T00:00:00+00:00",
                        ))
                        session.flush()
                        updated.set()

                with ThreadPoolExecutor(max_workers=1) as executor:
                    with Session(engine) as reader:
                        statement = select(func.count()).select_from(SupplierFlag)
                        self.assertEqual(reader.scalar(statement), 0)
                        pending_write = executor.submit(write_flag)
                        self.assertTrue(updated.wait(timeout=3), "Concurrent flag did not start")
                        self.assertEqual(reader.scalar(statement), 0)
                    pending_write.result(timeout=5)

                with Session(engine) as session:
                    self.assertEqual(session.scalar(statement), 1)
            finally:
                engine.dispose()


if __name__ == "__main__":
    unittest.main()
