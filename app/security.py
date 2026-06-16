import hashlib
import hmac
import os


PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 120_000

ROLE_LABELS = {
    "admin": "系统管理员",
    "manager": "项目经理",
    "finance": "财务专员",
    "staff": "实施工程师",
}


def hash_password(password, salt=None):
    if salt is None:
        salt_bytes = os.urandom(16)
    elif isinstance(salt, bytes):
        salt_bytes = salt
    else:
        salt_bytes = bytes.fromhex(salt)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_bytes.hex()}${digest.hex()}"


def verify_password(password, stored_hash):
    try:
        algorithm, iterations, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != PASSWORD_ALGORITHM:
            return False
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(computed, digest_hex)
    except (ValueError, TypeError):
        return False


def can_access(user_role, allowed_roles):
    if user_role == "admin":
        return True
    return user_role in allowed_roles
