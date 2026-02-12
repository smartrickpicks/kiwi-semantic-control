import base64
import hashlib
import hmac
import json
import os
import time
import logging

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_EXPIRY_SECONDS = 86400  # 24 hours


def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s):
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def sign_jwt(payload):
    if not JWT_SECRET:
        raise ValueError("JWT_SECRET environment variable is not set")

    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = dict(payload)
    payload["iat"] = now
    payload["exp"] = now + JWT_EXPIRY_SECONDS

    header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))

    signing_input = "%s.%s" % (header_b64, payload_b64)
    signature = hmac.new(
        JWT_SECRET.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64url_encode(signature)

    return "%s.%s" % (signing_input, sig_b64)


def verify_jwt(token):
    if not JWT_SECRET:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    try:
        signing_input = "%s.%s" % (parts[0], parts[1])
        expected_sig = hmac.new(
            JWT_SECRET.encode("utf-8"),
            signing_input.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        actual_sig = _b64url_decode(parts[2])

        if not hmac.compare_digest(expected_sig, actual_sig):
            logger.warning("JWT signature mismatch")
            return None

        payload = json.loads(_b64url_decode(parts[1]))

        exp = payload.get("exp", 0)
        if exp < int(time.time()):
            logger.info("JWT expired")
            return None

        return payload

    except Exception as e:
        logger.warning("JWT decode error: %s", e)
        return None
