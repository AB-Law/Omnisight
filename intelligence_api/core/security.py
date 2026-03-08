import hashlib
import re
import logging
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from intelligence_api.core.database import get_db
from intelligence_api.core.config import settings

logger = logging.getLogger(__name__)


# ── PII utilities (pre-existing) ──────────────────────────────────────────────

def hash_pii(text: str) -> str:
    """Hashes potentially sensitive identifiers like usernames."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


def clean_content(text: str) -> str:
    """Strips common PII patterns (e.g., emails) from text."""
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    return re.sub(email_pattern, "[EMAIL_REDACTED]", text)


# ── JWT Authentication ────────────────────────────────────────────────────────

def _decode_bearer_token(request: Request) -> dict:
    """Extract and verify the HS256 JWT signed by the Next.js frontend."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token,
            settings.NEXTAUTH_SECRET,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")

    return payload


def get_current_user(request: Request, db: Session = Depends(get_db)):
    """FastAPI dependency — decodes the JWT and upserts the User row.

    Returns the User ORM object for the authenticated caller.
    Raises HTTP 401 if the token is missing/invalid.
    """
    from intelligence_api.domain.models import User  # local import to avoid circular

    payload = _decode_bearer_token(request)

    google_sub: Optional[str] = payload.get("sub")
    if not google_sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    user = db.query(User).filter(User.google_sub == google_sub).first()
    if not user:
        user = User(
            google_sub=google_sub,
            email=payload.get("email") or "",
            name=payload.get("name"),
            picture_url=payload.get("picture"),
        )
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
        except Exception:
            db.rollback()
            # Race condition — another request created the user first
            user = db.query(User).filter(User.google_sub == google_sub).first()
            if not user:
                raise HTTPException(status_code=500, detail="Failed to create user")

    return user
