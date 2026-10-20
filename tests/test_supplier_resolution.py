import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.models import SupplierFlag
from backend.server import create_app


class SupplierResolutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.db_path = Path(self.temp.name) / "test.db"
        self.app = create_app(self.db_path)
        self.context = TestClient(self.app)
        self.client = self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.temp.cleanup()

    def flag(self, finisher_id="FIN-001", supplier_id="SUP-001", reason="Original audit finding"):
        response = self.client.post(
            f"/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags", json={"reason": reason},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()

    def resolve(self, flag, note="Affected toys recalled", outcome="recalled"):
        return self.client.post(
            f"/api/finishers/{flag['finisher_id']}/flags/{flag['id']}/resolve",
            json={"outcome": outcome, "note": note},
        )

    def history(self, finisher_id="FIN-001", supplier_id="SUP-001"):
        return self.client.get(f"/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags")

    def overviews(self):
        return {
            finisher["id"]: self.client.get(f"/api/finishers/{finisher['id']}/overview").json()
            for finisher in self.client.get("/api/finishers").json()
        }

    def test_resolution_clears_exposure_and_keeps_the_original_finding_after_restart(self):
        before = self.overviews()
        flag = self.flag()
        self.assertNotEqual(self.overviews(), before)
        response = self.resolve(flag, note=" Recall confirmed: reference R-101 ")
        self.assertEqual(response.status_code, 200)
        resolved = response.json()
        self.assertEqual(
            (resolved["id"], resolved["flagged_at"], resolved["reason"]),
            (flag["id"], flag["flagged_at"], flag["reason"]),
        )
        self.assertEqual(resolved["resolution_note"], "Recall confirmed: reference R-101")
        self.assertEqual(resolved["outcome"], "recalled")
        self.assertIsNotNone(resolved["resolved_at"])
        self.assertEqual(self.overviews(), before)
        with TestClient(create_app(self.db_path)) as restarted:
            history = restarted.get("/api/finishers/FIN-001/suppliers/SUP-001/flags")
            self.assertEqual(history.json(), [resolved])
            repeated = restarted.post(
                "/api/finishers/FIN-001/suppliers/SUP-001/flags", json={"reason": "New audit finding"},
            )
            self.assertEqual(repeated.status_code, 201)
            self.assertNotEqual(repeated.json()["id"], flag["id"])

    def test_a_recall_by_one_finisher_does_not_clear_another_finishers_flag(self):
        before = self.overviews()
        first = self.flag("FIN-001")
        self.flag("FIN-004", reason="Separate audit finding")
        flagged = self.overviews()
        self.assertEqual(self.resolve(first).status_code, 200)
        after = self.overviews()
        self.assertEqual(after["FIN-001"], before["FIN-001"])
        self.assertEqual(after["FIN-004"], flagged["FIN-004"])
        self.assertGreater(after["FIN-004"]["summary"]["affected_toy_count"], 0)

    def test_resolving_one_supplier_keeps_exposure_from_other_flagged_suppliers(self):
        self.flag(supplier_id="SUP-043", reason="Separate audit finding")
        before = self.overviews()
        flag = self.flag()
        self.assertEqual(self.resolve(flag).status_code, 200)
        self.assertEqual(self.overviews(), before)

    def test_a_resolved_flag_cannot_be_resolved_again(self):
        first = self.flag()
        self.assertEqual(self.resolve(first, "Wrong supplier was selected", "flagged_in_error").status_code, 200)
        self.assertEqual(self.resolve(first).status_code, 409)
        second = self.flag(reason="New finding")
        self.assertEqual(self.resolve(first).status_code, 409)
        with Session(self.app.state.engine) as session:
            still_open = session.scalar(select(SupplierFlag).where(SupplierFlag.resolved_at.is_(None)))
            self.assertEqual((still_open.id, still_open.reason), (second["id"], "New finding"))
        self.assertEqual(self.resolve(second).status_code, 200)
        history = self.history().json()
        self.assertEqual([flag["id"] for flag in history], [second["id"], first["id"]])
        self.assertEqual(history[1]["outcome"], "flagged_in_error")

    def test_invalid_resolution_requests_do_not_resolve_the_flag(self):
        flag = self.flag()
        valid = {"outcome": "recalled", "note": "Recall confirmed"}
        url = f"/api/finishers/FIN-001/flags/{flag['id']}/resolve"
        for change in [
            {"note": "  "}, {"note": "x" * 501}, {"note": 123},
            {"outcome": "reviewed"}, {"outcome": None}, {"unexpected": True},
        ]:
            with self.subTest(change=change):
                self.assertEqual(self.client.post(url, json={**valid, **change}).status_code, 422)
        self.assertEqual(self.client.post("/api/finishers/FIN-001/flags/abc/resolve", json=valid).status_code, 422)
        self.assertEqual(self.client.post("/api/finishers/FIN-001/flags/999/resolve", json=valid).status_code, 404)
        other_finisher = f"/api/finishers/FIN-004/flags/{flag['id']}/resolve"
        self.assertEqual(self.client.post(other_finisher, json=valid).status_code, 404)
        self.assertEqual(self.history(supplier_id="UNKNOWN").status_code, 404)
        self.assertEqual(self.history(finisher_id="UNKNOWN").status_code, 404)
        self.assertEqual(self.history().json(), [flag])

    def test_database_rejects_a_partly_resolved_flag(self):
        flag = self.flag()
        with Session(self.app.state.engine) as session:
            session.get(SupplierFlag, flag["id"]).resolved_at = "2026-10-21T00:00:00+00:00"
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main()
