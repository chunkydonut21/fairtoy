import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import make_engine
from backend.models import BillOfMaterial, Factory, Finisher, FinisherToy, Part, PartSource
from backend.seed import DATA_DIR, seed_database
from backend.server import create_app


class FairToyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "fairtoy.db"
        self.app = create_app(self.db_path)
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.temp.cleanup()

    def flag(self, finisher_id, supplier_id):
        response = self.client.post(
            f"/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags",
            json={"reason": "Verified concern"},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_fresh_catalog_and_toy_trace(self):
        self.assertEqual(self.client.get("/api/health").json(), {"ok": True})
        self.assertEqual(len(self.client.get("/api/finishers").json()), 8)
        overview = self.client.get("/api/finishers/FIN-001/overview").json()
        self.assertEqual(overview["summary"]["toy_count"], len(overview["toys"]))
        self.assertEqual(overview["summary"]["supplier_count"], len(overview["suppliers"]))

        toy = overview["toys"][0]
        detail = self.client.get(f"/api/finishers/FIN-001/toys/{toy['id']}").json()
        self.assertEqual(toy["part_count"], len(detail["parts"]))
        self.assertFalse(detail["affected"])
        with Session(self.app.state.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(PartSource)), 422)
            source = session.scalar(select(PartSource).limit(1))
            self.assertEqual(source.factory.supplier_id, source.factory.supplier.id)

    def test_flag_reaches_alternate_source_but_not_another_finisher(self):
        # The supplied CSV lists PRT-0079 under two suppliers; SUP-001 also serves FIN-004.
        part_id, supplier_id = "PRT-0079", "SUP-001"
        with Session(self.app.state.engine) as session:
            toy_id = session.scalar(
                select(BillOfMaterial.toy_id)
                .join(FinisherToy, FinisherToy.toy_id == BillOfMaterial.toy_id)
                .where(FinisherToy.finisher_id == "FIN-001", BillOfMaterial.part_id == part_id)
                .limit(1)
            )
            self.assertIsNotNone(toy_id)
        other_before = self.client.get("/api/finishers/FIN-004/overview").json()
        self.assertIn(supplier_id, {supplier["id"] for supplier in other_before["suppliers"]})
        self.flag("FIN-001", supplier_id)
        overview = self.client.get("/api/finishers/FIN-001/overview").json()
        toy = next(toy for toy in overview["toys"] if toy["id"] == toy_id)
        self.assertEqual(toy["flagged_supplier_count"], 1)
        detail = self.client.get(f"/api/finishers/FIN-001/toys/{toy_id}").json()
        part = next(part for part in detail["parts"] if part["id"] == part_id)
        self.assertTrue(part["affected"])
        self.assertGreater(len({source["supplier_id"] for source in part["sources"]}), 1)
        self.assertTrue(any(
            source["supplier_id"] == supplier_id and source["flagged_at"]
            for source in part["sources"]
        ))
        self.assertEqual(self.client.get("/api/finishers/FIN-004/overview").json(), other_before)
        self.assertEqual(
            self.client.post(
                f"/api/finishers/FIN-001/suppliers/{supplier_id}/flags",
                json={"reason": "Duplicate finding"},
            ).status_code,
            409,
        )

    def test_second_factory_does_not_double_count(self):
        self.flag("FIN-001", "SUP-001")
        before = self.client.get("/api/finishers/FIN-001/overview").json()
        with Session(self.app.state.engine) as session:
            source = session.scalar(
                select(PartSource)
                .join(PartSource.factory)
                .join(BillOfMaterial, BillOfMaterial.part_id == PartSource.part_id)
                .join(FinisherToy, FinisherToy.toy_id == BillOfMaterial.toy_id)
                .where(Factory.supplier_id == "SUP-001", FinisherToy.finisher_id == "FIN-001")
            )
            self.assertIsNotNone(source)
            session.add(Factory(
                id="FACT-EXTRA", supplier_id="SUP-001", name="Extra factory",
                city="Test city", country="Test country",
            ))
            session.add(PartSource(
                part_id=source.part_id, factory_id="FACT-EXTRA", unit_cost_usd=source.unit_cost_usd,
            ))
            session.commit()
        self.assertEqual(self.client.get("/api/finishers/FIN-001/overview").json(), before)

    def test_toy_trace_keeps_a_part_without_a_source(self):
        with Session(self.app.state.engine) as session:
            toy_id = session.scalar(
                select(FinisherToy.toy_id).where(FinisherToy.finisher_id == "FIN-001").limit(1)
            )
            session.add(Part(id="PART-NO-SOURCE", name="No recorded source"))
            session.add(BillOfMaterial(toy_id=toy_id, part_id="PART-NO-SOURCE", quantity=2))
            session.commit()
        detail = self.client.get(f"/api/finishers/FIN-001/toys/{toy_id}").json()
        part = next(part for part in detail["parts"] if part["id"] == "PART-NO-SOURCE")
        self.assertEqual(part["quantity"], 2)
        self.assertEqual(part["sources"], [])
        self.assertFalse(part["affected"])

    def test_resolution_keeps_history_and_other_open_flags(self):
        first = self.flag("FIN-001", "SUP-001")
        self.flag("FIN-001", "SUP-043")
        self.assertEqual(
            self.client.post(
                f"/api/finishers/FIN-004/flags/{first['id']}/resolve",
                json={"outcome": "recalled", "note": "Wrong finisher"},
            ).status_code,
            404,
        )
        resolved = self.client.post(
            f"/api/finishers/FIN-001/flags/{first['id']}/resolve",
            json={"outcome": "flagged_in_error", "note": "  Investigation complete  "},
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertEqual(resolved.json()["resolution_note"], "Investigation complete")
        overview = self.client.get("/api/finishers/FIN-001/overview").json()
        self.assertEqual(overview["summary"]["flagged_supplier_count"], 1)
        self.assertIsNotNone(next(s for s in overview["suppliers"] if s["id"] == "SUP-043")["flag"])
        with TestClient(create_app(self.db_path)) as restarted:
            history = restarted.get("/api/finishers/FIN-001/suppliers/SUP-001/flags").json()
            self.assertEqual(history, [resolved.json()])
            self.assertEqual(
                restarted.post(
                    f"/api/finishers/FIN-001/flags/{first['id']}/resolve",
                    json={"outcome": "recalled", "note": "Trying again"},
                ).status_code,
                409,
            )
            self.assertEqual(
                restarted.post(
                    "/api/finishers/FIN-001/suppliers/SUP-001/flags",
                    json={"reason": "New finding"},
                ).status_code,
                201,
            )

    def test_invalid_requests_are_rejected(self):
        flag_url = "/api/finishers/FIN-001/suppliers/SUP-001/flags"
        self.assertEqual(self.client.post(flag_url, json={"reason": "x"}).status_code, 422)
        self.assertEqual(
            self.client.post(flag_url, json={"reason": "Valid concern", "unexpected": True}).status_code,
            422,
        )
        self.assertEqual(
            self.client.post(
                "/api/finishers/UNKNOWN/suppliers/SUP-001/flags",
                json={"reason": "Valid concern"},
            ).status_code,
            404,
        )
        self.assertEqual(self.client.get("/api/finishers/FIN-001/toys/UNKNOWN").status_code, 404)
        flag = self.flag("FIN-001", "SUP-001")
        self.assertEqual(
            self.client.post(
                f"/api/finishers/FIN-001/flags/{flag['id']}/resolve",
                json={"outcome": "reviewed", "note": "Valid note"},
            ).status_code,
            422,
        )

    def test_seed_rejects_supplier_factory_mismatch_without_partial_data(self):
        data_dir = Path(self.temp.name) / "data"
        shutil.copytree(DATA_DIR, data_dir)
        parts_file = data_dir / "parts.csv"
        with parts_file.open(encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            rows = list(reader)
            fields = reader.fieldnames
        rows[0]["supplier_id"] = "SUP-001" if rows[0]["supplier_id"] != "SUP-001" else "SUP-002"
        with parts_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        engine = make_engine(Path(self.temp.name) / "invalid.db")
        try:
            with self.assertRaisesRegex(ValueError, "Factory/supplier mismatch"):
                seed_database(engine, data_dir)
            with Session(engine) as session:
                self.assertEqual(session.scalar(select(func.count()).select_from(Finisher)), 0)
            self.assertTrue(seed_database(engine))
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
