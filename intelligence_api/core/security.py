import hashlib
import re

def hash_pii(text: str) -> str:
    """Hashes potentially sensitive identifiers like usernames."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()

def clean_content(text: str) -> str:
    """Strips common PII patterns (e.g., emails) from text."""
    # Simple regex for email stripping as an example
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    return re.sub(email_pattern, "[EMAIL_REDACTED]", text)
