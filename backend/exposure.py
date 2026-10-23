from itertools import groupby
from operator import itemgetter

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from .models import BillOfMaterial, Factory, Finisher, FinisherToy, Part, PartSource, Supplier, SupplierFlag, Toy
from .schemas import (
    FinisherResponse, FlagResponse, Overview, PartResponse, SourceResponse, Summary, SupplierSummary,
    ToyDetail, ToySummary,
)


def open_flag(finisher_id: str, supplier_id):
    # Joins the finisher's open flag on a supplier. The unique index allows at most one.
    return and_(
        SupplierFlag.supplier_id == supplier_id,
        SupplierFlag.finisher_id == finisher_id,
        SupplierFlag.resolved_at.is_(None),
    )


def toy_summaries(session: Session, finisher_id: str) -> list[ToySummary]:
    part_count = (
        select(func.count())
        .select_from(BillOfMaterial)
        .where(BillOfMaterial.toy_id == Toy.id)
        .scalar_subquery()
    )
    # A toy is affected when any source of any of its parts has an open flag.
    flagged_supplier_count = (
        select(func.count(Factory.supplier_id.distinct()))
        .select_from(BillOfMaterial)
        .join(PartSource, PartSource.part_id == BillOfMaterial.part_id)
        .join(Factory, Factory.id == PartSource.factory_id)
        .join(SupplierFlag, open_flag(finisher_id, Factory.supplier_id))
        .where(BillOfMaterial.toy_id == Toy.id)
        .scalar_subquery()
    )
    statement = (
        select(
            Toy.id, Toy.name, FinisherToy.retail_price_usd, FinisherToy.units_per_year,
            part_count.label("part_count"), flagged_supplier_count.label("flagged_supplier_count"),
        )
        .select_from(FinisherToy)
        .join(Toy, Toy.id == FinisherToy.toy_id)
        .where(FinisherToy.finisher_id == finisher_id)
        .order_by(Toy.name, Toy.id)
    )

    return [
        ToySummary(**row, affected=row["flagged_supplier_count"] > 0)
        for row in session.execute(statement).mappings()
    ]


def supplier_summaries(session: Session, finisher_id: str) -> list[SupplierSummary]:
    catalog_parts = (
        select(BillOfMaterial.toy_id, BillOfMaterial.part_id)
        .join(FinisherToy, FinisherToy.toy_id == BillOfMaterial.toy_id)
        .where(FinisherToy.finisher_id == finisher_id)
        .subquery()
    )

    # A supplier can make several parts of one toy, and one part in several factories,
    # so toys and parts are each counted once.
    statement = (
        select(
            Supplier, SupplierFlag,
            func.count(catalog_parts.c.toy_id.distinct()).label("toy_count"),
            func.count(catalog_parts.c.part_id.distinct()).label("part_count"),
        )
        .join(Factory, Factory.supplier_id == Supplier.id)
        .join(PartSource, PartSource.factory_id == Factory.id)
        .join(catalog_parts, catalog_parts.c.part_id == PartSource.part_id)
        .outerjoin(SupplierFlag, open_flag(finisher_id, Supplier.id))
        .group_by(Supplier.id)
        .order_by(SupplierFlag.id.is_(None), Supplier.name)
    )
    summaries = []
    for row in session.execute(statement).mappings():
        supplier = row[Supplier]
        flag = row[SupplierFlag]
        summaries.append(SupplierSummary(
            id=supplier.id, name=supplier.name, country=supplier.country,
            flag=FlagResponse.model_validate(flag) if flag else None,
            toy_count=row["toy_count"], part_count=row["part_count"],
        ))
    return summaries


def overview(session: Session, finisher_id: str) -> Overview | None:
    finisher = session.get(Finisher, finisher_id)
    if finisher is None:
        return None
    toys = toy_summaries(session, finisher_id)
    suppliers = supplier_summaries(session, finisher_id)
    return Overview(
        finisher=FinisherResponse.model_validate(finisher), toys=toys, suppliers=suppliers,
        summary=Summary(
            toy_count=len(toys), affected_toy_count=sum(toy.affected for toy in toys),
            supplier_count=len(suppliers),
            flagged_supplier_count=sum(supplier.flag is not None for supplier in suppliers),
        ),
    )


def toy_detail(session: Session, finisher_id: str, toy_id: str) -> ToyDetail | None:
    listing = session.get(FinisherToy, (finisher_id, toy_id), options=[joinedload(FinisherToy.toy)])
    if listing is None:
        return None
    # One row per part source: toy -> part -> source -> supplier and factory.
    # Outer joins keep a part that has no recorded source.
    statement = (
        select(
            Part.id.label("part_id"), Part.name.label("part_name"), BillOfMaterial.quantity,
            Supplier.id.label("supplier_id"), Supplier.name.label("supplier_name"),
            SupplierFlag.flagged_at, SupplierFlag.reason.label("flag_reason"),
            Factory.id.label("factory_id"), Factory.name.label("factory_name"), Factory.city, Factory.country,
            PartSource.unit_cost_usd,
        )
        .select_from(BillOfMaterial)
        .join(Part, Part.id == BillOfMaterial.part_id)
        .outerjoin(PartSource, PartSource.part_id == Part.id)
        .outerjoin(Factory, Factory.id == PartSource.factory_id)
        .outerjoin(Supplier, Supplier.id == Factory.supplier_id)
        .outerjoin(SupplierFlag, open_flag(finisher_id, Supplier.id))
        .where(BillOfMaterial.toy_id == toy_id)
        .order_by(Part.name, Part.id, SupplierFlag.id.is_(None), Supplier.name, Factory.id)
    )
    rows = session.execute(statement).mappings()
    parts = []
    # The ORDER BY keeps each part's source rows adjacent, as groupby requires.
    for (part_id, name, quantity), part_rows in groupby(rows, key=itemgetter("part_id", "part_name", "quantity")):
        sources = [SourceResponse.model_validate(row) for row in part_rows if row["supplier_id"] is not None]
        parts.append(PartResponse(
            id=part_id, name=name, quantity=quantity, sources=sources,
            affected=any(source.flagged_at is not None for source in sources),
        ))
    return ToyDetail(
        id=listing.toy.id, name=listing.toy.name, retail_price_usd=listing.retail_price_usd,
        units_per_year=listing.units_per_year, parts=parts, affected=any(part.affected for part in parts),
    )
