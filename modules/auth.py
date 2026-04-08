"""
auth.py - Secure authentication
"""
import re
import datetime
import bcrypt
import streamlit as st
from modules.database import get_db, log_activity

SESSION_TIMEOUT_MINUTES = 60
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


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


def check_credentials(username: str, password: str):
    """Returns (success, message, user_dict | None)."""
    if is_locked_out(username):
        return (
            False,
            f"This account is locked for {LOCKOUT_MINUTES} minutes due to too many failed attempts. Please try again later.",
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


def signup(username: str, password: str):
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
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed),
            )
        return True, "Account created successfully! You can now log in."
    except Exception:
        return False, "That username is already taken. Please choose another."


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
