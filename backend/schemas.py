from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints


class Record(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class FinisherResponse(Record):
    id: str
    name: str
    country: str


Note = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=500)]
Outcome = Literal["recalled", "flagged_in_error"]


class FlagRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: Note


class ResolveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    outcome: Outcome
    note: Note


class FlagResponse(Record):
    id: int
    finisher_id: str
    supplier_id: str
    reason: str
    flagged_at: str
    resolved_at: str | None
    outcome: Outcome | None
    resolution_note: str | None


class SupplierSummary(Record):
    id: str
    name: str
    country: str
    flag: FlagResponse | None
    toy_count: int
    part_count: int


class ToyResponse(Record):
    id: str
    name: str
    retail_price_usd: float
    units_per_year: int


class ToySummary(ToyResponse):
    part_count: int
    flagged_supplier_count: int
    affected: bool


class SourceResponse(BaseModel):
    supplier_id: str
    supplier_name: str
    flagged_at: str | None
    flag_reason: str | None
    factory_id: str
    factory_name: str
    city: str
    country: str
    unit_cost_usd: float


class PartResponse(BaseModel):
    id: str
    name: str
    quantity: int
    affected: bool
    sources: list[SourceResponse]


class ToyDetail(ToyResponse):
    affected: bool
    parts: list[PartResponse]


class Summary(BaseModel):
    toy_count: int
    affected_toy_count: int
    supplier_count: int
    flagged_supplier_count: int


class Overview(BaseModel):
    finisher: FinisherResponse
    toys: list[ToySummary]
    suppliers: list[SupplierSummary]
    summary: Summary
