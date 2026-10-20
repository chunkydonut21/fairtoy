import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import make_engine
from backend.models import Finisher
from backend.seed import DATA_DIR, seed_database


class SeedValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1])
        self.folder = Path(self.temp.name)
        self.data_dir = self.folder / "data"
        shutil.copytree(DATA_DIR, self.data_dir)

    def tearDown(self):
        self.temp.cleanup()

    def test_invalid_records_report_the_file_and_line_and_roll_back(self):
        cases = [
            ("parts.csv", "part_id", "  "),
            ("parts.csv", "part_name", ""),
            ("parts.csv", "unit_cost_usd", "-1"),
            ("parts.csv", "unit_cost_usd", "nan"),
            ("parts.csv", "unit_cost_usd", "inf"),
            ("toys.csv", "retail_price_usd", "-1"),
            ("toys.csv", "units_per_year", "-1"),
            ("bill_of_materials.csv", "quantity", "0"),
            ("bill_of_materials.csv", "quantity", "1.5"),
        ]
        for index, (filename, column, value) in enumerate(cases):
            with self.subTest(filename=filename, column=column, value=value):
                with (DATA_DIR / filename).open(encoding="utf-8-sig", newline="") as file:
                    reader = csv.DictReader(file)
                    rows = list(reader)
                    fields = reader.fieldnames
                rows[0][column] = value
                target = self.data_dir / filename
                with target.open("w", encoding="utf-8", newline="") as file:
                    writer = csv.DictWriter(file, fieldnames=fields)
                    writer.writeheader()
                    writer.writerows(rows)
                engine = make_engine(self.folder / f"invalid-{index}.db")
                try:
                    with self.assertRaises(ValueError) as raised:
                        seed_database(engine, self.data_dir)
                    self.assertIn(f"{filename}, line 2:", str(raised.exception))
                    with Session(engine) as session:
                        self.assertEqual(session.scalar(select(func.count()).select_from(Finisher)), 0)
                    self.assertTrue(seed_database(engine))
                finally:
                    engine.dispose()
                    shutil.copyfile(DATA_DIR / filename, target)

    def test_empty_finishers_and_invalid_headers_are_rejected(self):
        target = self.data_dir / "finishers.csv"
        cases = [
            ("finisher_id,finisher_name,hq_country\n", "at least one finisher"),
            ("finisher_id,finisher_name\n", "missing columns hq_country"),
            ("finisher_id,finisher_name,hq_country,finisher_id\n", "duplicate column names"),
            ("finisher_id,finisher_name,hq_country\nF,Name,Country,extra\n", "too many columns"),
        ]
        for index, (content, message) in enumerate(cases):
            with self.subTest(message=message):
                target.write_text(content, encoding="utf-8")
                engine = make_engine(self.folder / f"headers-{index}.db")
                try:
                    with self.assertRaisesRegex(ValueError, message):
                        seed_database(engine, self.data_dir)
                finally:
                    engine.dispose()


if __name__ == "__main__":
    unittest.main()
