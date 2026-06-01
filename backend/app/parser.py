import re
from typing import TypedDict


class ParsedRecord(TypedDict):
    url: str
    domain: str
    username: str
    password: str


_ILLEGAL = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")


def _extract_domain(url: str) -> str:
    if not url:
        return ""
    u = url.replace("http://", "").replace("https://", "")
    return u.split("/")[0].split("?")[0].lower()


def parse_line(line: str) -> ParsedRecord | None:
    """
    Attempt to parse a credential line into (url, domain, username, password).
    Returns None if the line should be silently skipped (headers, cookies, blanks).
    Raises ValueError if the line looks like a credential but can't be parsed.
    """
    if _ILLEGAL.search(line):
        return None
    line = line.strip()
    if not line:
        return None
    if line.startswith("TOTAL_"):
        return None
    if ";" in line:
        return None  # cookie line

    # normalise pipe and spaced-colon separators
    if line.count("|") == 2:
        line = line.replace("|", ":")
    if line.count(" : ") == 2:
        line = line.replace(" : ", ":")

    record = _try_parse(line)
    if record is None:
        raise ValueError(line)
    return record


def _try_parse(line: str) -> ParsedRecord | None:
    colon_count = line.count(":")
    space_count = line.count(" ")

    # username:password  (no URL)
    if colon_count == 1 and space_count == 0:
        u, p = line.split(":", 1)
        return _make(url="", username=u, password=p)

    # bare domain:username:password  (no http, no spaces, exactly 2 colons)
    if not line.startswith("http") and colon_count == 2 and space_count == 0:
        parts = line.split(":", 2)
        return _make(url=parts[0], username=parts[1], password=parts[2])

    # "domain user:pass" or "user:pass domain"
    if colon_count == 1 and space_count == 1:
        ci, si = line.index(":"), line.index(" ")
        if ci > si:
            # domain user:pass
            domain_part, cred = line.split(" ", 1)
            u, p = cred.split(":", 1)
            return _make(url=domain_part, username=u, password=p)
        else:
            # user:pass domain
            cred, domain_part = line.split(" ", 1)
            u, p = cred.split(":", 1)
            return _make(url=domain_part, username=u, password=p)

    # "https://domain user:pass" or "user:pass https://domain"  (2 colons, 1 space)
    if "http" in line and colon_count == 2 and space_count == 1:
        parts = line.split(" ", 1)
        url_part = next((p for p in parts if "http" in p), "")
        cred_part = next((p for p in parts if "http" not in p), "")
        if ":" in cred_part:
            u, p = cred_part.split(":", 1)
            return _make(url=url_part, username=u, password=p)

    # domain:user:pass with 3+ colons (password may contain colons)
    if colon_count >= 3 and space_count == 0:
        # split from right so password keeps its colons
        rev = line[::-1]
        parts_rev = rev.split(":", 2)
        parts = [s[::-1] for s in parts_rev]
        return _make(url=parts[2], username=parts[1], password=parts[0])

    return None


def _make(*, url: str, username: str, password: str) -> ParsedRecord:
    url = url.strip()
    username = username.strip()
    password = password.strip()
    return ParsedRecord(
        url=url,
        domain=_extract_domain(url),
        username=username,
        password=password,
    )
