import argparse
import csv
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .database import DB_PATH, make_engine
from .import_schemas import BomRow, CsvRecord, FactoryRow, FinisherRow, PartRow, SupplierRow, ToyRow
from .models import Base, BillOfMaterial, Factory, Finisher, FinisherToy, Part, PartSource, Supplier, Toy

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def read_csv(data_dir: Path, filename: str, record_type: type[CsvRecord]) -> list[dict]:
    with (data_dir / filename).open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames and len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"{filename}: duplicate column names")
        missing = set(record_type.model_fields) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{filename}: missing columns {', '.join(sorted(missing))}")
        records = []
        for row in reader:
            if None in row:
                raise ValueError(f"{filename}, line {reader.line_num}: too many columns")
            try:
                records.append(record_type.model_validate(row).model_dump())
            except ValidationError as exc:
                raise ValueError(f"{filename}, line {reader.line_num}: {exc}") from exc
        return records


def import_finishers(session: Session, data_dir: Path):
    rows = read_csv(data_dir, "finishers.csv", FinisherRow)
    if not rows:
        raise ValueError("finishers.csv: at least one finisher is required")
    session.add_all([
        Finisher(id=row["finisher_id"], name=row["finisher_name"], country=row["hq_country"])
        for row in rows
    ])


def import_suppliers(session: Session, data_dir: Path):
    session.add_all([
        Supplier(id=row["supplier_id"], name=row["supplier_name"], country=row["hq_country"])
        for row in read_csv(data_dir, "suppliers.csv", SupplierRow)
    ])


def import_factories(session: Session, data_dir: Path) -> dict[str, Factory]:
    factories = {}
    for row in read_csv(data_dir, "factories.csv", FactoryRow):
        factory = Factory(
            id=row["factory_id"], supplier_id=row["supplier_id"], name=row["factory_name"],
            city=row["city"], country=row["country"],
        )
        if factory.id in factories:
            raise ValueError(f"Duplicate factory {factory.id}")
        factories[factory.id] = factory
        session.add(factory)
    return factories


def import_parts(session: Session, data_dir: Path, factories: dict[str, Factory]):
    parts: dict[str, Part] = {}
    for row in read_csv(data_dir, "parts.csv", PartRow):
        part_id = row["part_id"]
        if part_id in parts and parts[part_id].name != row["part_name"]:
            raise ValueError(f"Conflicting names for {part_id}")
        if part_id not in parts:
            parts[part_id] = Part(id=part_id, name=row["part_name"])

        factory = factories.get(row["factory_id"])
        if factory is None or factory.supplier_id != row["supplier_id"]:
            raise ValueError(f"Factory/supplier mismatch for {part_id}")
        session.add(PartSource(
            part=parts[part_id], supplier_id=row["supplier_id"], factory=factory,
            unit_cost_usd=row["unit_cost_usd"],
        ))


def import_toys(session: Session, data_dir: Path) -> set[str]:
    toys: dict[str, Toy] = {}
    for row in read_csv(data_dir, "toys.csv", ToyRow):
        toy_id = row["toy_id"]
        if toy_id in toys and toys[toy_id].name != row["toy_name"]:
            raise ValueError(f"Conflicting names for {toy_id}")
        if toy_id not in toys:
            toys[toy_id] = Toy(id=toy_id, name=row["toy_name"])
        session.add(FinisherToy(
            finisher_id=row["finisher_id"], toy=toys[toy_id],
            retail_price_usd=row["retail_price_usd"], units_per_year=row["units_per_year"],
        ))
    return set(toys)


def import_bill_of_materials(session: Session, data_dir: Path, toy_ids: set[str]):
    for row in read_csv(data_dir, "bill_of_materials.csv", BomRow):
        if row["toy_id"] not in toy_ids:
            raise ValueError(f"BOM references unknown toy {row['toy_id']}")
        session.add(BillOfMaterial(
            toy_id=row["toy_id"], part_id=row["part_id"], quantity=row["quantity"],
        ))


def seed_database(engine: Engine, data_dir: Path = DATA_DIR) -> bool:
    Base.metadata.create_all(engine)
    with Session(engine) as session, session.begin():
        if session.scalar(select(Finisher.id).limit(1)):
            return False

        import_finishers(session, data_dir)
        import_suppliers(session, data_dir)
        factories = import_factories(session, data_dir)
        import_parts(session, data_dir, factories)
        toy_ids = import_toys(session, data_dir)
        import_bill_of_materials(session, data_dir, toy_ids)
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import the six CSV files into an empty database.")
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    args = parser.parse_args()
    engine = make_engine(args.database)
    try:
        imported = seed_database(engine, args.data_dir)
        print("CSV data imported." if imported else "Database already seeded; existing data and flags kept.")
    finally:
        engine.dispose()
