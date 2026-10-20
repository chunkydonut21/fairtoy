from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Money = Annotated[float, Field(ge=0)]


class CsvRecord(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)


class FinisherRow(CsvRecord):
    finisher_id: Text
    finisher_name: Text
    hq_country: Text


class SupplierRow(CsvRecord):
    supplier_id: Text
    supplier_name: Text
    hq_country: Text


class FactoryRow(CsvRecord):
    factory_id: Text
    supplier_id: Text
    factory_name: Text
    # Six sites in the export have no city.
    city: str
    country: Text


class PartRow(CsvRecord):
    part_id: Text
    part_name: Text
    supplier_id: Text
    factory_id: Text
    unit_cost_usd: Money


class ToyRow(CsvRecord):
    toy_id: Text
    finisher_id: Text
    toy_name: Text
    retail_price_usd: Money
    units_per_year: Annotated[int, Field(ge=0)]


class BomRow(CsvRecord):
    toy_id: Text
    part_id: Text
    quantity: Annotated[int, Field(gt=0)]
