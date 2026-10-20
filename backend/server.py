import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import exposure, suppliers
from .seed import seed_database
from .database import DB_PATH, make_engine
from .models import Finisher, Supplier, SupplierFlag
from .schemas import FinisherResponse, FlagRequest, FlagResponse, Overview, ResolveRequest, ToyDetail


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


Database = Annotated[Session, Depends(get_session)]


def require_finisher_and_supplier(session: Session, finisher_id: str, supplier_id: str):
    if session.get(Finisher, finisher_id) is None:
        raise HTTPException(status_code=404, detail="Finisher not found")
    if session.get(Supplier, supplier_id) is None:
        raise HTTPException(status_code=404, detail="Supplier not found")


def create_app(db_path: str | Path = DB_PATH) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(db_path)
        try:
            seed_database(engine)
            app.state.engine = engine
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="FairToy API", version="0.2.0", lifespan=lifespan)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail}, headers=exc.headers)

    @app.get("/api/health")
    def health():
        return {"ok": True}

    @app.get("/api/finishers", response_model=list[FinisherResponse])
    def list_finishers(session: Database):
        return session.scalars(select(Finisher).order_by(Finisher.name)).all()

    @app.get("/api/finishers/{finisher_id}/overview", response_model=Overview)
    def get_overview(finisher_id: str, session: Database):
        result = exposure.overview(session, finisher_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Finisher not found")
        return result

    @app.get("/api/finishers/{finisher_id}/toys/{toy_id}", response_model=ToyDetail)
    def get_toy(finisher_id: str, toy_id: str, session: Database):
        result = exposure.toy_detail(session, finisher_id, toy_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Toy not found")
        return result

    @app.post(
        "/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags", response_model=FlagResponse, status_code=201,
    )
    def flag_supplier(finisher_id: str, supplier_id: str, body: FlagRequest, session: Database):
        flag = suppliers.flag_supplier(session, finisher_id, supplier_id, body.reason)
        if flag is None:
            require_finisher_and_supplier(session, finisher_id, supplier_id)
            raise HTTPException(
                status_code=409, detail="This supplier is already flagged. Resolve the current flag first.",
            )
        return flag

    @app.post("/api/finishers/{finisher_id}/flags/{flag_id}/resolve", response_model=FlagResponse)
    def resolve_flag(finisher_id: str, flag_id: int, body: ResolveRequest, session: Database):
        flag = suppliers.resolve_flag(session, finisher_id, flag_id, body.outcome, body.note)
        if flag is None:
            existing = session.get(SupplierFlag, flag_id)
            if existing is None or existing.finisher_id != finisher_id:
                raise HTTPException(status_code=404, detail="Flag not found")
            raise HTTPException(status_code=409, detail="This flag is already resolved. Refresh the catalog.")
        return flag

    @app.get("/api/finishers/{finisher_id}/suppliers/{supplier_id}/flags", response_model=list[FlagResponse])
    def list_flags(finisher_id: str, supplier_id: str, session: Database):
        require_finisher_and_supplier(session, finisher_id, supplier_id)
        return session.scalars(
            select(SupplierFlag)
            .where(SupplierFlag.finisher_id == finisher_id, SupplierFlag.supplier_id == supplier_id)
            .order_by(SupplierFlag.id.desc())
        ).all()

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.server:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")))
