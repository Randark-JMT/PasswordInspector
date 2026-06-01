import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Credential, FailedLine, UploadJob
from ..parser import parse_line
from ..schemas import FailedLineOut, ResolveRequest, UploadJobOut

router = APIRouter(prefix="/upload", tags=["upload"])

CHUNK = 64 * 1024        # 64 KB read chunks
DB_BATCH = 2000          # rows per bulk insert


@router.post("/start", response_model=UploadJobOut)
async def start_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    job_id = str(uuid.uuid4())
    filename = file.filename or "unknown"

    # Stream the uploaded file to a temp file BEFORE returning the response.
    # FastAPI closes UploadFile after the response is sent, so the background
    # task must not hold a reference to the original UploadFile object.
    tmp_fd, tmp_path = tempfile.mkstemp(prefix="pi_upload_")
    os.close(tmp_fd)
    total_bytes = 0
    async with aiofiles.open(tmp_path, "wb") as tmp:
        while True:
            chunk = await file.read(CHUNK)
            if not chunk:
                break
            await tmp.write(chunk)
            total_bytes += len(chunk)

    job = UploadJob(
        id=job_id,
        filename=filename,
        status="processing",
        total_bytes=total_bytes,
        processed_bytes=0,
    )
    db.add(job)
    await db.commit()

    # Fire-and-forget: process from temp file so UploadFile lifetime doesn't matter
    asyncio.create_task(_process_upload(job_id, tmp_path, filename, total_bytes))

    return UploadJobOut.model_validate(job)


async def _process_upload(job_id: str, tmp_path: str, filename: str, total_bytes: int):
    from ..database import AsyncSessionLocal

    leftover = b""
    imported = 0
    failed = 0
    total_lines = 0
    processed_bytes = 0
    cred_buf: list[Credential] = []
    fail_buf: list[FailedLine] = []

    async def flush(session: AsyncSession):
        nonlocal imported, failed
        if cred_buf:
            session.add_all(cred_buf)
            imported += len(cred_buf)
            cred_buf.clear()
        if fail_buf:
            session.add_all(fail_buf)
            failed += len(fail_buf)
            fail_buf.clear()
        await session.commit()

    try:
        async with AsyncSessionLocal() as session:
            async with aiofiles.open(tmp_path, "rb") as fp:
                while True:
                    chunk = await fp.read(CHUNK)
                    if not chunk:
                        break
                    processed_bytes += len(chunk)

                    raw = leftover + chunk
                    lines = raw.split(b"\n")
                    leftover = lines[-1]

                    for raw_line in lines[:-1]:
                        total_lines += 1
                        try:
                            line = raw_line.decode("utf-8", errors="replace")
                            record = parse_line(line)
                            if record is None:
                                continue
                            cred_buf.append(
                                Credential(
                                    url=record["url"],
                                    domain=record["domain"],
                                    username=record["username"],
                                    password=record["password"],
                                    source_file=filename,
                                    first_seen=datetime.now(timezone.utc),
                                )
                            )
                        except ValueError as exc:
                            fail_buf.append(
                                FailedLine(
                                    raw=str(exc),
                                    upload_id=job_id,
                                    source_file=filename,
                                    created_at=datetime.now(timezone.utc),
                                )
                            )

                        if len(cred_buf) + len(fail_buf) >= DB_BATCH:
                            await flush(session)

                    # progress tick
                    await session.execute(
                        update(UploadJob)
                        .where(UploadJob.id == job_id)
                        .values(
                            processed_bytes=processed_bytes,
                            total_lines=total_lines,
                            imported_lines=imported,
                            failed_lines=failed,
                        )
                    )
                    await session.commit()

            # handle last partial line
            if leftover:
                total_lines += 1
                try:
                    line = leftover.decode("utf-8", errors="replace")
                    record = parse_line(line)
                    if record is not None:
                        cred_buf.append(
                            Credential(
                                url=record["url"],
                                domain=record["domain"],
                                username=record["username"],
                                password=record["password"],
                                source_file=filename,
                                first_seen=datetime.now(timezone.utc),
                            )
                        )
                except ValueError as exc:
                    fail_buf.append(
                        FailedLine(
                            raw=str(exc),
                            upload_id=job_id,
                            source_file=filename,
                            created_at=datetime.now(timezone.utc),
                        )
                    )

            await flush(session)

            await session.execute(
                update(UploadJob)
                .where(UploadJob.id == job_id)
                .values(
                    status="done",
                    total_bytes=total_bytes,
                    processed_bytes=processed_bytes,
                    total_lines=total_lines,
                    imported_lines=imported,
                    failed_lines=failed,
                    finished_at=datetime.now(timezone.utc),
                )
            )
            await session.commit()

    except Exception as exc:  # noqa: BLE001
        async with AsyncSessionLocal() as session:
            await session.execute(
                update(UploadJob)
                .where(UploadJob.id == job_id)
                .values(status="error", error_message=str(exc))
            )
            await session.commit()
    finally:
        # Always clean up the temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


@router.get("/job/{job_id}", response_model=UploadJobOut)
async def get_job(job_id: str, db: AsyncSession = Depends(get_db)):
    row = await db.get(UploadJob, job_id)
    if not row:
        raise HTTPException(404, "Job not found")
    return UploadJobOut.model_validate(row)


@router.get("/job/{job_id}/failed", response_model=list[FailedLineOut])
async def get_failed_lines(job_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(FailedLine)
        .where(FailedLine.upload_id == job_id, FailedLine.resolved == False)  # noqa: E712
        .order_by(FailedLine.id)
        .limit(500)
    )
    return [FailedLineOut.model_validate(r) for r in result.scalars()]


@router.post("/job/{job_id}/failed/{line_id}/resolve")
async def resolve_failed_line(
    job_id: str,
    line_id: int,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(FailedLine, line_id)
    if not row or row.upload_id != job_id:
        raise HTTPException(404)

    from ..parser import _extract_domain
    db.add(
        Credential(
            url=body.url,
            domain=_extract_domain(body.url),
            username=body.username,
            password=body.password,
            source_file=row.source_file,
            first_seen=datetime.now(timezone.utc),
        )
    )
    row.resolved = True
    await db.commit()
    return {"ok": True}


@router.delete("/job/{job_id}/failed/{line_id}")
async def discard_failed_line(
    job_id: str, line_id: int, db: AsyncSession = Depends(get_db)
):
    row = await db.get(FailedLine, line_id)
    if not row or row.upload_id != job_id:
        raise HTTPException(404)
    row.resolved = True
    await db.commit()
    return {"ok": True}
