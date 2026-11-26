"""Raw HTTP header cardinality checks for authentication and idempotency boundaries.

Starlette's Request.headers.getlist() exposes repeated ASGI header fields. Do
not log or echo the returned values. An upstream proxy that coalesces repeated
fields before ASGI must enforce the same policy at its own ingress boundary.
"""
from fastapi import HTTPException, Request


def require_single_raw_header(
    request: Request,
    header_name: str,
    *,
    status_code: int,
    detail: str,
) -> str:
    """Return one raw header value or fail closed when it is missing/duplicated."""
    values = request.headers.getlist(header_name)
    if len(values) != 1:
        raise HTTPException(status_code=status_code, detail=detail)
    return values[0]
