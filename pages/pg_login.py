"""
pg_login.py  — Login, Signup, Forgot Password, and Admin Login pages
All pages show theme toggle in top-right corner.
"""
import streamlit as st
from modules.auth import (
    check_credentials, signup, login_user,
    get_security_question, verify_security_answer,
    reset_password_with_answer, hash_password, validate_password_strength
)
from modules.theme_utils import apply_theme


SECURITY_QUESTIONS = [
    "What was the name of your first pet?",
    "What city were you born in?",
    "What is your mother's maiden name?",
    "What was the name of your primary school?",
    "What is your favorite childhood movie?",
    "What street did you grow up on?",
    "What was the make of your first car?",
    "What is the name of your oldest sibling?",
]


def _theme_toggle_top():
    """Render a lightweight theme toggle in top-right without sidebar."""
    current = st.session_state.get("app_theme", "light")
    label   = "🌙 Dark" if current == "light" else "🌞 Light"
    cols    = st.columns([8, 1])
    with cols[1]:
        if st.button(label, key="login_theme_btn"):
            st.session_state["app_theme"] = "dark" if current == "light" else "light"
            st.rerun()


# ─── LOGIN ─────────────────────────────────────────────────────────────────────

def show_login():
    apply_theme()
    _theme_toggle_top()

    st.markdown("""
    <div style='text-align:center;padding:30px 0 8px'>
        <h1 style='font-size:2.4rem;font-weight:700;'>📊 Data Analyzer Pro</h1>
        <p style='color:#888;font-size:1rem;'>Enterprise Data Analysis Platform</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login_form"):
            username  = st.text_input("Username", placeholder="Enter your username")
            password  = st.text_input("Password", type="password", placeholder="Enter your password")
            submitted = st.form_submit_button("Login →", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Both username and password are required.")
            else:
                ok, msg, user = check_credentials(username.strip(), password)
                if ok:
                    login_user(user)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")

        bc1, bc2 = st.columns(2)
        if bc1.button("✨ Create Account", use_container_width=True):
            st.session_state["mode"] = "signup"
            st.rerun()
        if bc2.button("🔑 Forgot Password?", use_container_width=True):
            st.session_state["mode"] = "forgot"
            st.rerun()

        st.markdown("---")
        if st.button("👑 Admin Login", use_container_width=True, type="secondary"):
            st.session_state["mode"] = "admin_login"
            st.rerun()


# ─── SIGN UP ───────────────────────────────────────────────────────────────────

def show_signup():
    apply_theme()
    _theme_toggle_top()

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### ✨ Create a New Account")
        with st.form("signup_form"):
            username  = st.text_input("Username", placeholder="3+ characters, letters/numbers/underscore only")
            password  = st.text_input("Password", type="password",
                                      placeholder="8+ chars, 1 uppercase, 1 number, 1 special")
            confirm   = st.text_input("Confirm Password", type="password")

            st.markdown("#### 🔐 Security Question (for password recovery)")
            sec_q = st.selectbox("Select a security question:", SECURITY_QUESTIONS)
            sec_a = st.text_input("Your answer:", placeholder="Case-insensitive")

            submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("All fields are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            elif not sec_a.strip():
                st.error("Please provide an answer to your security question.")
            else:
                ok, msg = signup(username.strip(), password, sec_q, sec_a)
                if ok:
                    st.success(msg)
                    st.balloons()
                    st.session_state["mode"] = "login"
                    st.rerun()
                else:
                    st.error(msg)

        st.markdown("---")
        if st.button("← Back to Login", use_container_width=True):
            st.session_state["mode"] = "login"
            st.rerun()

        with st.expander("🔒 Password Requirements"):
            st.markdown("""
            - ✅ At least 8 characters
            - ✅ At least one uppercase letter (A–Z)
            - ✅ At least one digit (0–9)
            - ✅ At least one special character (!@#$%^&*)

            **Example:** `MyPass@2024`
            """)


# ─── FORGOT PASSWORD ───────────────────────────────────────────────────────────

def show_forgot_password():
    apply_theme()
    _theme_toggle_top()

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### 🔑 Forgot Password")
        st.info("Enter your username to retrieve your security question.")

        # Step 1 — enter username
        fp_step = st.session_state.get("fp_step", 1)

        if fp_step == 1:
            with st.form("fp_step1"):
                fp_user = st.text_input("Username:", key="fp_username_input")
                go = st.form_submit_button("Continue →", type="primary", use_container_width=True)
            if go:
                if not fp_user.strip():
                    st.error("Please enter your username.")
                else:
                    question = get_security_question(fp_user.strip())
                    if question:
                        st.session_state["fp_username"] = fp_user.strip()
                        st.session_state["fp_question"] = question
                        st.session_state["fp_step"]     = 2
                        st.rerun()
                    else:
                        st.error("Username not found or no security question set. Contact admin.")

        elif fp_step == 2:
            fp_user     = st.session_state.get("fp_username", "")
            fp_question = st.session_state.get("fp_question", "")
            st.markdown(f"**Username:** `{fp_user}`")
            st.markdown(f"**Security Question:** {fp_question}")
            with st.form("fp_step2"):
                answer   = st.text_input("Your answer:", placeholder="Case-insensitive")
                new_pass = st.text_input("New Password:", type="password",
                                         placeholder="8+ chars, 1 uppercase, 1 number, 1 special")
                confirm  = st.text_input("Confirm New Password:", type="password")
                go2      = st.form_submit_button("Reset Password →", type="primary", use_container_width=True)
            if go2:
                if not answer.strip() or not new_pass or not confirm:
                    st.error("All fields are required.")
                elif new_pass != confirm:
                    st.error("Passwords do not match.")
                elif not verify_security_answer(fp_user, answer):
                    st.error("Incorrect answer. Please try again.")
                else:
                    ok, msg = reset_password_with_answer(fp_user, new_pass)
                    if ok:
                        st.success(f"✅ {msg}")
                        # Clear forgot password state
                        for k in ["fp_step","fp_username","fp_question"]:
                            st.session_state.pop(k, None)
                        st.session_state["mode"] = "login"
                        st.rerun()
                    else:
                        st.error(msg)

            if st.button("← Start Over"):
                for k in ["fp_step","fp_username","fp_question"]:
                    st.session_state.pop(k, None)
                st.rerun()

        st.markdown("---")
        if st.button("← Back to Login", use_container_width=True):
            for k in ["fp_step","fp_username","fp_question"]:
                st.session_state.pop(k, None)
            st.session_state["mode"] = "login"
            st.rerun()


# ─── ADMIN LOGIN (separate, private) ──────────────────────────────────────────

def show_admin_login():
    """
    Dedicated admin login page — separate from the regular user login.
    Only the true admin (is_admin=1, username='admin') can pass.
    """
    apply_theme()
    _theme_toggle_top()

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style='text-align:center;padding:10px 0 20px'>
            <div style='font-size:48px'>👑</div>
            <h2 style='font-weight:700;'>Admin Portal</h2>
            <p style='color:#888;font-size:13px;'>Restricted access — authorized personnel only</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("admin_login_form"):
            username = st.text_input("Admin Username", placeholder="admin username")
            password = st.text_input("Admin Password", type="password", placeholder="admin password")
            submitted = st.form_submit_button("🔐 Admin Login", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("Both fields are required.")
            else:
                ok, msg, user = check_credentials(username.strip(), password)
                if ok and user.get("is_admin"):
                    login_user(user)
                    st.session_state["page"] = "Admin"
                    st.success("Welcome, Admin!")
                    st.rerun()
                elif ok and not user.get("is_admin"):
                    # Logged in as non-admin — reject and log out
                    from modules.auth import logout_user
                    logout_user()
                    st.error("Access denied. This portal is for administrators only.")
                else:
                    st.error(msg)

        # Admin password change — shown only if already knows current password
        with st.expander("🔑 Change Admin Password"):
            with st.form("admin_pwd_change"):
                curr_pwd  = st.text_input("Current Admin Password", type="password")
                new_pwd   = st.text_input("New Password", type="password",
                                           placeholder="8+ chars, 1 uppercase, 1 number, 1 special")
                conf_pwd  = st.text_input("Confirm New Password", type="password")
                submitted2 = st.form_submit_button("Update Password", type="primary",
                                                    use_container_width=True)
            if submitted2:
                if not curr_pwd or not new_pwd or not conf_pwd:
                    st.error("All fields required.")
                elif new_pwd != conf_pwd:
                    st.error("New passwords do not match.")
                else:
                    # Verify current password against admin account
                    ok2, _, admin_user = check_credentials("admin", curr_pwd)
                    if not ok2 or not admin_user:
                        st.error("Current password is incorrect.")
                    else:
                        ok3, msg3 = validate_password_strength(new_pwd)
                        if not ok3:
                            st.error(msg3)
                        else:
                            from modules.database import get_db
                            hashed = hash_password(new_pwd)
                            with get_db() as conn:
                                conn.execute(
                                    "UPDATE users SET password=? WHERE username='admin'",
                                    (hashed,)
                                )
                            st.success("✅ Admin password updated successfully!")

        st.markdown("---")
        if st.button("← Back to User Login", use_container_width=True):
            st.session_state["mode"] = "login"
            st.rerun()
