import csv
import io
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Credential
from ..schemas import CredentialOut, CredentialQuery, QueryResult

router = APIRouter(prefix="/query", tags=["query"])


def _build_filter(q: str, field: str, exact: bool):
    if not q:
        return None
    cols = {
        "domain": Credential.domain,
        "username": Credential.username,
        "password": Credential.password,
    }
    if exact:
        if field == "all":
            return or_(
                Credential.domain == q,
                Credential.username == q,
                Credential.password == q,
            )
        return cols[field] == q
    else:
        pattern = q  # use pg ILIKE
        if field == "all":
            return or_(
                Credential.domain.ilike(f"%{pattern}%"),
                Credential.username.ilike(f"%{pattern}%"),
                Credential.password.ilike(f"%{pattern}%"),
            )
        return cols[field].ilike(f"%{pattern}%")


@router.get("", response_model=QueryResult)
async def query_credentials(
    q: str = Query(default=""),
    field: str = Query(default="all"),
    exact: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    flt = _build_filter(q, field, exact)
    base = select(Credential)
    count_q = select(func.count()).select_from(Credential)
    if flt is not None:
        base = base.where(flt)
        count_q = count_q.where(flt)

    total = (await db.execute(count_q)).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Credential.domain, Credential.username)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return QueryResult(
        total=total,
        page=page,
        page_size=page_size,
        items=[CredentialOut.model_validate(r) for r in rows],
    )


@router.get("/export")
async def export_credentials(
    q: str = Query(default=""),
    field: str = Query(default="all"),
    exact: bool = Query(default=False),
    fmt: str = Query(default="csv"),
    db: AsyncSession = Depends(get_db),
):
    flt = _build_filter(q, field, exact)
    stmt = select(Credential)
    if flt is not None:
        stmt = stmt.where(flt)
    stmt = stmt.order_by(Credential.domain, Credential.username)

    rows = (await db.execute(stmt)).scalars().all()

    if fmt == "json":
        import json
        data = json.dumps(
            [CredentialOut.model_validate(r).model_dump(mode="json") for r in rows],
            ensure_ascii=False,
            indent=2,
        )
        return StreamingResponse(
            io.BytesIO(data.encode()),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="export.json"'},
        )

    # default CSV
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=["id", "url", "domain", "username", "password", "first_seen", "source_file"]
    )
    writer.writeheader()
    for r in rows:
        obj = CredentialOut.model_validate(r)
        writer.writerow(obj.model_dump(mode="json"))

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="export.csv"'},
    )
