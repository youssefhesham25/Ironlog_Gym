#!/usr/bin/env python3
"""
IRONLOG Gym Management System - Authentication & Cryptography Utilities
"""

import hashlib
import secrets
import datetime
import jwt

SECRET_KEY = "ironlog_production_permanent_secret_key_2026"
ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    """Hash password using PBKDF2 SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    db_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}:{db_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against its PBKDF2 hash."""
    try:
        salt, hash_val = hashed_password.split(":")
        db_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return db_hash.hex() == hash_val
    except Exception:
        return False

def create_access_token(data: dict, expires_in_minutes: int = 52560000) -> str:
    """Generates a secure JWT token containing user metadata."""
    to_encode = data.copy()
    expire = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=expires_in_minutes)
    to_encode.update({"exp": int(expire.timestamp())})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodes and validates a JWT token. Returns payload or None if invalid."""
    try:
        # jwt.decode automatically checks the "exp" claim against the current time
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None
