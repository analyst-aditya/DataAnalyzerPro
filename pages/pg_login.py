"""
pg_login.py - Login and Signup pages
"""
import streamlit as st
from modules.auth import check_credentials, signup, login_user


def show_login():
    st.markdown("""
    <div style='text-align:center;padding:40px 0 10px'>
        <h1 style='font-size:2.5rem;font-weight:700;'>📊 Data Analyzer Pro</h1>
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
        st.markdown("Don't have an account?")
        if st.button("✨ Create an Account", use_container_width=True):
            st.session_state["mode"] = "signup"
            st.rerun()

        # st.markdown("""
        # <div style='text-align:center;margin-top:20px;color:#888;font-size:12px'>
        #     Default admin: <code>admin</code> / <code>Admin@12345</code>
        # </div>
        # """, unsafe_allow_html=True)


def show_signup():
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("### ✨ Create a New Account")
        with st.form("signup_form"):
            username  = st.text_input("Username", placeholder="3+ characters, letters/numbers/underscore only")
            password  = st.text_input("Password", type="password",
                                      placeholder="8+ chars, 1 uppercase, 1 number, 1 special character")
            confirm   = st.text_input("Confirm Password", type="password")
            submitted = st.form_submit_button("Create Account →", use_container_width=True, type="primary")

        if submitted:
            if not username or not password:
                st.error("All fields are required.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                ok, msg = signup(username.strip(), password)
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
