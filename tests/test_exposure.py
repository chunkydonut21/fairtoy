import tempfile
import unittest
import shutil
import csv
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.seed import DATA_DIR, seed_database
from backend.database import make_engine
from backend.models import BillOfMaterial, Factory, Finisher, FinisherToy, Part, PartSource, SupplierFlag, Toy
from backend.server import create_app
from backend.suppliers import flag_supplier


class ExposureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.db_path = Path(self.temp.name) / "test.db"
        self.app = create_app(self.db_path)
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        self.temp.cleanup()

    def flag(self, finisher_id, supplier_id, reason="Verified finding"):
        response = self.client.post(
            f"/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags", json={"reason": reason},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def test_import_preserves_all_catalog_entries_and_sources(self):
        with Session(self.app.state.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Part)), 400)
            self.assertEqual(session.scalar(select(func.count()).select_from(PartSource)), 422)
            self.assertEqual(session.scalar(select(func.count()).select_from(Toy)), 300)
            self.assertEqual(session.scalar(select(func.count()).select_from(FinisherToy)), 305)
        self.assertEqual(len(self.client.get("/api/finishers").json()), 8)

    def test_overview_uses_three_selects_for_different_catalog_sizes(self):
        statements = []

        def record(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        engine = self.app.state.engine
        event.listen(engine, "before_cursor_execute", record)
        try:
            sizes = []
            for finisher_id in ["FIN-001", "FIN-004"]:
                statements.clear()
                response = self.client.get(f"/api/finishers/{finisher_id}/overview")
                self.assertEqual(response.status_code, 200)
                sizes.append(len(response.json()["toys"]))
                self.assertEqual(len(statements), 3)
            self.assertNotEqual(*sizes)
        finally:
            event.remove(engine, "before_cursor_execute", record)

    def test_an_extra_factory_source_does_not_multiply_overview_counts(self):
        self.flag("FIN-001", "SUP-001")
        before = self.client.get("/api/finishers/FIN-001/overview").json()
        with Session(self.app.state.engine) as session:
            source = session.scalar(
                select(PartSource)
                .join(BillOfMaterial, BillOfMaterial.part_id == PartSource.part_id)
                .join(FinisherToy, FinisherToy.toy_id == BillOfMaterial.toy_id)
                .where(PartSource.supplier_id == "SUP-001", FinisherToy.finisher_id == "FIN-001")
            )
            self.assertIsNotNone(source)
            factory = Factory(
                id="FACT-EXTRA", supplier_id=source.supplier_id, name="Extra factory",
                city="Test city", country="Test country",
            )
            session.add(factory)
            session.flush()
            session.add(PartSource(
                part_id=source.part_id, supplier_id=source.supplier_id,
                factory_id=factory.id, unit_cost_usd=source.unit_cost_usd,
            ))
            session.commit()
        after = self.client.get("/api/finishers/FIN-001/overview").json()
        self.assertEqual(after, before)

    def test_overview_keeps_toys_without_a_bill_of_materials(self):
        with Session(self.app.state.engine) as session:
            session.add(Toy(id="TOY-EMPTY", name="Empty toy"))
            session.flush()
            session.add(FinisherToy(
                finisher_id="FIN-001", toy_id="TOY-EMPTY", retail_price_usd=10,
                units_per_year=100,
            ))
            session.commit()
        response = self.client.get("/api/finishers/FIN-001/overview").json()
        toy = next(toy for toy in response["toys"] if toy["id"] == "TOY-EMPTY")
        self.assertEqual(toy["part_count"], 0)
        self.assertEqual(toy["flagged_supplier_count"], 0)
        self.assertFalse(toy["affected"])

    def test_alternate_source_flags_toy_and_exposes_trace(self):
        with Session(self.app.state.engine) as session:
            part_id = session.scalar(
                select(PartSource.part_id).group_by(PartSource.part_id)
                .having(func.count(func.distinct(PartSource.supplier_id)) > 1).limit(1)
            )
            supplier_id = session.scalar(select(PartSource.supplier_id).where(PartSource.part_id == part_id))
            finisher_id, toy_id = session.execute(
                select(FinisherToy.finisher_id, FinisherToy.toy_id)
                .join(BillOfMaterial, BillOfMaterial.toy_id == FinisherToy.toy_id)
                .where(BillOfMaterial.part_id == part_id).limit(1)
            ).one()
        url = f"/api/finishers/{finisher_id}/toys/{toy_id}"
        self.assertFalse(self.client.get(url).json()["affected"])
        self.flag(finisher_id, supplier_id)
        detail = self.client.get(url).json()
        self.assertTrue(detail["affected"])
        part = next(p for p in detail["parts"] if p["id"] == part_id)
        self.assertTrue(part["affected"])
        self.assertGreater(len({source["supplier_id"] for source in part["sources"]}), 1)
        flagged = next(s for s in part["sources"] if s["supplier_id"] == supplier_id)
        self.assertEqual(flagged["flag_reason"], "Verified finding")
        overview = self.client.get(f"/api/finishers/{finisher_id}/overview").json()
        self.assertTrue(next(t for t in overview["toys"] if t["id"] == toy_id)["affected"])

    def test_shared_toy_id_keeps_both_finisher_listings(self):
        with Session(self.app.state.engine) as session:
            toy_id = session.scalar(
                select(FinisherToy.toy_id).group_by(FinisherToy.toy_id).having(func.count() > 1).limit(1)
            )
            listings = session.scalars(select(FinisherToy).where(FinisherToy.toy_id == toy_id)).all()
            finisher_ids = [listing.finisher_id for listing in listings]
            self.assertIs(listings[0].toy, listings[1].toy)
            prices = {listing.finisher_id: listing.retail_price_usd for listing in listings}
        self.assertEqual(len(finisher_ids), 2)
        details = [self.client.get(f"/api/finishers/{fid}/toys/{toy_id}").json() for fid in finisher_ids]
        self.assertEqual([p["id"] for p in details[0]["parts"]], [p["id"] for p in details[1]["parts"]])
        for fid, detail in zip(finisher_ids, details):
            self.assertEqual(detail["retail_price_usd"], prices[fid])
        self.assertEqual(self.client.get(f"/api/finishers/FIN-NOT-FOUND/toys/{toy_id}").status_code, 404)

    def test_invalid_flag_requests_are_rejected(self):
        url = "/api/finishers/FIN-001/suppliers/SUP-001/flags"
        for reason in ["  ", "x", "x" * 501, 123, None]:
            response = self.client.post(url, json={"reason": reason})
            self.assertEqual(response.status_code, 422, reason)
        self.assertEqual(self.client.post(url, content="{").status_code, 422)
        for unknown in ["/api/finishers/FIN-001/suppliers/UNKNOWN/flags", "/api/finishers/UNKNOWN/suppliers/SUP-001/flags"]:
            self.assertEqual(self.client.post(unknown, json={"reason": "Finding"}).status_code, 404)

    def test_a_flag_only_affects_the_finisher_that_raised_it(self):
        other_finisher = self.client.get("/api/finishers/FIN-004/overview").json()
        self.flag("FIN-001", "SUP-001")
        flagged = self.client.get("/api/finishers/FIN-001/overview").json()
        self.assertGreater(flagged["summary"]["affected_toy_count"], 0)
        self.assertEqual(self.client.get("/api/finishers/FIN-004/overview").json(), other_finisher)

    def test_a_flagged_supplier_cannot_be_flagged_again_after_restart(self):
        first = self.flag("FIN-001", "SUP-001", reason=" First finding ")
        self.assertEqual(first["reason"], "First finding")
        with TestClient(create_app(self.db_path)) as restarted:
            second = restarted.post("/api/finishers/FIN-001/suppliers/SUP-001/flags", json={"reason": "Second finding"})
        self.assertEqual(second.status_code, 409)
        self.assertIn("error", second.json())
        with Session(self.app.state.engine) as session:
            flags = session.scalars(select(SupplierFlag)).all()
            self.assertEqual([(flag.id, flag.reason) for flag in flags], [(first["id"], "First finding")])

    def test_the_database_allows_one_open_flag_per_finisher_and_supplier(self):
        with Session(self.app.state.engine) as first, Session(self.app.state.engine) as second:
            self.assertIsNotNone(flag_supplier(first, "FIN-001", "SUP-001", "First finding"))
            self.assertIsNone(flag_supplier(second, "FIN-001", "SUP-001", "Later finding"))
            self.assertIsNotNone(flag_supplier(second, "FIN-004", "SUP-001", "Own finding"))
        with Session(self.app.state.engine) as session:
            open_flags = session.scalars(select(SupplierFlag).where(SupplierFlag.resolved_at.is_(None))).all()
            self.assertEqual(
                sorted((flag.finisher_id, flag.reason) for flag in open_flags),
                [("FIN-001", "First finding"), ("FIN-004", "Own finding")],
            )

    def test_toy_trace_does_not_query_once_per_part(self):
        with Session(self.app.state.engine) as session:
            listings = session.execute(
                select(FinisherToy.finisher_id, FinisherToy.toy_id, func.count(BillOfMaterial.part_id))
                .join(BillOfMaterial, BillOfMaterial.toy_id == FinisherToy.toy_id)
                .group_by(FinisherToy.finisher_id, FinisherToy.toy_id)
                .order_by(func.count(BillOfMaterial.part_id))
            ).all()
        statements = []

        def record(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        engine = self.app.state.engine
        event.listen(engine, "before_cursor_execute", record)
        try:
            for finisher_id, toy_id, part_count in [listings[0], listings[-1]]:
                statements.clear()
                response = self.client.get(f"/api/finishers/{finisher_id}/toys/{toy_id}")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.json()["parts"]), part_count)
                self.assertEqual(len(statements), 2)
        finally:
            event.remove(engine, "before_cursor_execute", record)

    def test_catalog_scope_and_missing_resources_return_404(self):
        with Session(self.app.state.engine) as session:
            toy_id = session.scalar(
                select(Toy.id).where(~Toy.catalog_entries.any(FinisherToy.finisher_id == "FIN-001"))
            )
        self.assertIsNotNone(toy_id)
        for url in [
            "/api/finishers/UNKNOWN/overview",
            "/api/finishers/FIN-001/toys/UNKNOWN",
            f"/api/finishers/FIN-001/toys/{toy_id}",
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404)
            self.assertIn("error", response.json())

    def test_overview_and_trace_agree_for_every_toy_after_flags(self):
        for finisher_id, supplier_id in [("FIN-001", "SUP-001"), ("FIN-001", "SUP-043"), ("FIN-004", "SUP-043")]:
            self.flag(finisher_id, supplier_id)
        for finisher in self.client.get("/api/finishers").json():
            finisher_id = finisher["id"]
            overview = self.client.get(f"/api/finishers/{finisher_id}/overview").json()
            affected_count = 0
            for toy in overview["toys"]:
                detail = self.client.get(f"/api/finishers/{finisher_id}/toys/{toy['id']}").json()
                flagged_ids = {
                    source["supplier_id"] for part in detail["parts"] for source in part["sources"]
                    if source["flagged_at"] is not None
                }
                self.assertEqual(toy["part_count"], len(detail["parts"]))
                self.assertEqual(toy["flagged_supplier_count"], len(flagged_ids))
                self.assertEqual(toy["affected"], bool(flagged_ids))
                self.assertEqual(detail["affected"], bool(flagged_ids))
                affected_count += bool(flagged_ids)
            self.assertEqual(overview["summary"]["affected_toy_count"], affected_count)

    def test_failed_import_rolls_back_and_can_be_retried(self):
        bad_data = Path(self.temp.name) / "bad-data"
        shutil.copytree(DATA_DIR, bad_data)
        parts_file = bad_data / "parts.csv"
        content = parts_file.read_text(encoding="utf-8-sig")
        parts_file.write_text(content.replace("SUP-027", "UNKNOWN", 1), encoding="utf-8")
        engine = make_engine(Path(self.temp.name) / "retry.db")
        try:
            with self.assertRaises(ValueError):
                seed_database(engine, bad_data)
            with Session(engine) as session:
                self.assertEqual(session.scalar(select(func.count()).select_from(Finisher)), 0)
            seed_database(engine)
            with Session(engine) as session:
                self.assertEqual(session.scalar(select(func.count()).select_from(Finisher)), 8)
        finally:
            engine.dispose()

    def test_bom_rejects_a_nonexistent_toy(self):
        with Session(self.app.state.engine) as session:
            part_id = session.scalar(select(Part.id).limit(1))
            session.add(BillOfMaterial(toy_id="UNKNOWN", part_id=part_id, quantity=1))
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_database_rejects_a_factory_owned_by_another_supplier(self):
        with Session(self.app.state.engine) as session:
            source = session.scalar(select(PartSource).limit(1))
            another_factory = session.scalar(
                select(Factory).where(Factory.supplier_id != source.supplier_id).limit(1)
            )
            source.factory_id = another_factory.id
            with self.assertRaises(IntegrityError):
                session.commit()

    def test_conflicting_names_for_a_shared_toy_reject_the_csv_import(self):
        bad_data = Path(self.temp.name) / "bad-toys"
        shutil.copytree(DATA_DIR, bad_data)
        toys_file = bad_data / "toys.csv"
        with toys_file.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        seen = set()
        for row in rows:
            if row["toy_id"] in seen:
                row["toy_name"] = "Conflicting toy name"
                break
            seen.add(row["toy_id"])
        with toys_file.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        engine = make_engine(Path(self.temp.name) / "conflicting-toys.db")
        try:
            with self.assertRaisesRegex(ValueError, "Conflicting names for"):
                seed_database(engine, bad_data)
            with Session(engine) as session:
                self.assertEqual(session.scalar(select(func.count()).select_from(Toy)), 0)
                self.assertEqual(session.scalar(select(func.count()).select_from(FinisherToy)), 0)
        finally:
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
