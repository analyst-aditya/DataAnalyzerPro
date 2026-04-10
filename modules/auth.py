"""
auth.py - Secure authentication with forgot password support
"""
import re
import secrets
import datetime
import bcrypt
import streamlit as st
from modules.database import get_db, log_activity

SESSION_TIMEOUT_MINUTES = 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RESET_TOKEN_MINUTES = 30


# ─── Password helpers ──────────────────────────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


def validate_password_strength(password: str):
    """Returns (is_valid, message)."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character (!@#$% etc.)."
    return True, "Strong password"


# ─── Rate limiting ─────────────────────────────────────────────────────────────

def _count_recent_failures(username: str) -> int:
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(minutes=LOCKOUT_MINUTES)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    with get_db() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE username=? AND success=0 AND attempted_at > ?",
            (username, cutoff),
        )
        return cur.fetchone()[0]


def _record_attempt(username: str, success: bool):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO login_attempts (username, success) VALUES (?, ?)",
            (username, 1 if success else 0),
        )


def is_locked_out(username: str) -> bool:
    return _count_recent_failures(username) >= MAX_LOGIN_ATTEMPTS


# ─── Login / Signup ────────────────────────────────────────────────────────────

def check_credentials(username: str, password: str):
    """Returns (success, message, user_dict | None)."""
    if is_locked_out(username):
        return (
            False,
            f"This account is locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts.",
            None,
        )

    with get_db() as conn:
        cur = conn.execute(
            "SELECT id, username, password, is_admin, is_active FROM users WHERE username=?",
            (username,),
        )
        row = cur.fetchone()

    if not row:
        _record_attempt(username, False)
        return False, "Invalid username or password.", None

    if not row["is_active"]:
        return False, "Your account has been disabled. Please contact an administrator.", None

    if not verify_password(password, row["password"]):
        _record_attempt(username, False)
        failures  = _count_recent_failures(username)
        remaining = MAX_LOGIN_ATTEMPTS - failures
        if remaining <= 0:
            return False, f"Account is now locked for {LOCKOUT_MINUTES} minutes.", None
        return False, f"Incorrect password. {remaining} attempt(s) remaining.", None

    _record_attempt(username, True)
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET last_login=? WHERE id=?",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row["id"]),
        )

    user = {"id": row["id"], "username": row["username"], "is_admin": bool(row["is_admin"])}
    log_activity(user["id"], "login", "Login successful")
    return True, "Login successful!", user


def signup(username: str, password: str, security_question: str = "", security_answer: str = ""):
    """Returns (success, message)."""
    username = username.strip()
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username may only contain letters, numbers, and underscores."
    if username.lower() == "admin":
        return False, "That username is reserved."

    ok, msg = validate_password_strength(password)
    if not ok:
        return False, msg

    hashed = hash_password(password)
    hashed_answer = hash_password(security_answer.strip().lower()) if security_answer.strip() else ""

    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password, security_question, security_answer) VALUES (?, ?, ?, ?)",
                (username, hashed, security_question, hashed_answer),
            )
        return True, "Account created successfully! You can now log in."
    except Exception:
        return False, "That username is already taken. Please choose another."


# ─── Forgot Password ───────────────────────────────────────────────────────────

def get_security_question(username: str):
    """Returns the security question for a username, or None."""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT security_question FROM users WHERE username=? AND is_active=1",
            (username,)
        )
        row = cur.fetchone()
    if row and row["security_question"]:
        return row["security_question"]
    return None


def verify_security_answer(username: str, answer: str) -> bool:
    """Returns True if the answer matches the stored hash."""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT security_answer FROM users WHERE username=?",
            (username,)
        )
        row = cur.fetchone()
    if not row or not row["security_answer"]:
        return False
    return verify_password(answer.strip().lower(), row["security_answer"])


def generate_reset_token(username: str) -> str:
    """Creates a single-use reset token valid for RESET_TOKEN_MINUTES minutes."""
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.utcnow() + datetime.timedelta(minutes=RESET_TOKEN_MINUTES)
               ).strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        # Invalidate old tokens for this user
        conn.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE username=?",
            (username,)
        )
        conn.execute(
            "INSERT INTO password_reset_tokens (username, token, expires_at) VALUES (?, ?, ?)",
            (username, token, expires)
        )
    return token


def verify_reset_token(username: str, token: str) -> bool:
    """Returns True if token is valid and not expired."""
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    with get_db() as conn:
        cur = conn.execute(
            """SELECT id FROM password_reset_tokens
               WHERE username=? AND token=? AND used=0 AND expires_at > ?""",
            (username, token, now)
        )
        return cur.fetchone() is not None


def consume_reset_token(username: str, token: str):
    """Marks the token as used."""
    with get_db() as conn:
        conn.execute(
            "UPDATE password_reset_tokens SET used=1 WHERE username=? AND token=?",
            (username, token)
        )


def reset_password_with_answer(username: str, new_password: str) -> tuple:
    """Reset password after security answer verified. Returns (ok, message)."""
    ok, msg = validate_password_strength(new_password)
    if not ok:
        return False, msg
    hashed = hash_password(new_password)
    with get_db() as conn:
        conn.execute("UPDATE users SET password=? WHERE username=?", (hashed, username))
    log_activity(0, "password_reset", f"User {username} reset password via security question")
    return True, "Password reset successfully! You can now log in."


# ─── Session management ────────────────────────────────────────────────────────

def login_user(user: dict):
    st.session_state["auth_user"] = user
    st.session_state["auth_time"] = datetime.datetime.utcnow().isoformat()


def logout_user():
    for key in ["auth_user", "auth_time"]:
        st.session_state.pop(key, None)


def current_user():
    user = st.session_state.get("auth_user")
    if not user:
        return None
    auth_time_str = st.session_state.get("auth_time")
    if auth_time_str:
        auth_time = datetime.datetime.fromisoformat(auth_time_str)
        elapsed   = (datetime.datetime.utcnow() - auth_time).total_seconds() / 60
        if elapsed > SESSION_TIMEOUT_MINUTES:
            logout_user()
            return None
    return user


def refresh_session():
    if st.session_state.get("auth_user"):
        st.session_state["auth_time"] = datetime.datetime.utcnow().isoformat()
