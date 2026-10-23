from __future__ import annotations

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Finisher(Base):
    __tablename__ = "finisher"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    catalog_entries: Mapped[list[FinisherToy]] = relationship(back_populates="finisher")


class Supplier(Base):
    __tablename__ = "supplier"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    country: Mapped[str]
    factories: Mapped[list[Factory]] = relationship(back_populates="supplier")


class SupplierFlag(Base):
    __tablename__ = "supplier_flag"
    __table_args__ = (
        CheckConstraint("outcome IN ('recalled', 'flagged_in_error')", name="ck_flag_outcome"),
        CheckConstraint(
            "(resolved_at IS NULL) = (outcome IS NULL) AND (resolved_at IS NULL) = (resolution_note IS NULL)",
            name="ck_flag_resolution_complete",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    finisher_id: Mapped[str] = mapped_column(ForeignKey("finisher.id"))
    supplier_id: Mapped[str] = mapped_column(ForeignKey("supplier.id"))
    reason: Mapped[str]
    flagged_at: Mapped[str]
    resolved_at: Mapped[str | None]
    outcome: Mapped[str | None]
    resolution_note: Mapped[str | None]


# A finisher can have only one open flag per supplier.
Index(
    "uq_open_flag", SupplierFlag.finisher_id, SupplierFlag.supplier_id,
    unique=True, sqlite_where=SupplierFlag.resolved_at.is_(None),
)


class Factory(Base):
    __tablename__ = "factory"

    id: Mapped[str] = mapped_column(primary_key=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("supplier.id"), index=True)
    name: Mapped[str]
    city: Mapped[str]
    country: Mapped[str]
    supplier: Mapped[Supplier] = relationship(back_populates="factories")
    sources: Mapped[list[PartSource]] = relationship(back_populates="factory")


class Part(Base):
    __tablename__ = "part"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    sources: Mapped[list[PartSource]] = relationship(back_populates="part")
    bom_entries: Mapped[list[BillOfMaterial]] = relationship(back_populates="part")


class PartSource(Base):
    __tablename__ = "part_source"

    part_id: Mapped[str] = mapped_column(ForeignKey("part.id"), primary_key=True)
    factory_id: Mapped[str] = mapped_column(ForeignKey("factory.id"), primary_key=True, index=True)
    unit_cost_usd: Mapped[float] = mapped_column(Float)
    part: Mapped[Part] = relationship(back_populates="sources")
    factory: Mapped[Factory] = relationship(back_populates="sources")


class Toy(Base):
    __tablename__ = "toy"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    catalog_entries: Mapped[list[FinisherToy]] = relationship(back_populates="toy")
    bom_entries: Mapped[list[BillOfMaterial]] = relationship(back_populates="toy")


class FinisherToy(Base):
    __tablename__ = "finisher_toy"

    finisher_id: Mapped[str] = mapped_column(ForeignKey("finisher.id"), primary_key=True)
    toy_id: Mapped[str] = mapped_column(ForeignKey("toy.id"), primary_key=True, index=True)
    retail_price_usd: Mapped[float] = mapped_column(Float)
    units_per_year: Mapped[int] = mapped_column(Integer)
    finisher: Mapped[Finisher] = relationship(back_populates="catalog_entries")
    toy: Mapped[Toy] = relationship(back_populates="catalog_entries")


class BillOfMaterial(Base):
    __tablename__ = "bom"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_bom_quantity_positive"),
        Index("idx_bom_part", "part_id"),
    )

    toy_id: Mapped[str] = mapped_column(ForeignKey("toy.id"), primary_key=True)
    part_id: Mapped[str] = mapped_column(ForeignKey("part.id"), primary_key=True)
    quantity: Mapped[int] = mapped_column(Integer)
    part: Mapped[Part] = relationship(back_populates="bom_entries")
    toy: Mapped[Toy] = relationship(back_populates="bom_entries")
