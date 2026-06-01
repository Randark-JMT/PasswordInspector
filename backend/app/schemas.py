from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CredentialOut(BaseModel):
    id: int
    url: str
    domain: str
    username: str
    password: str
    first_seen: datetime
    source_file: str

    model_config = {"from_attributes": True}


class CredentialQuery(BaseModel):
    q: str = ""
    field: str = "all"   # all | domain | username | password
    exact: bool = False
    page: int = 1
    page_size: int = 50


class QueryResult(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[CredentialOut]


class FailedLineOut(BaseModel):
    id: int
    raw: str
    upload_id: str
    source_file: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ResolveRequest(BaseModel):
    url: str = ""
    username: str
    password: str


class UploadJobOut(BaseModel):
    id: str
    filename: str
    status: str
    total_bytes: int
    processed_bytes: int
    total_lines: int
    imported_lines: int
    failed_lines: int
    error_message: str
    created_at: datetime
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}
