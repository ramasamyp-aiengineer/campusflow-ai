import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def rate_limit_key(request: Request) -> str:
    """Prefer an unforgeable session identity over proxy-derived client IPs."""
    authorization = request.headers.get("authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() == "bearer" and token.strip():
        digest = hashlib.sha256(token.strip().encode()).hexdigest()
        return f"session:{digest}"
    return f"client:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key, headers_enabled=True)
