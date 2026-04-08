"""
pg_admin.py - Admin Panel (passwords are never exported)
"""
import io, datetime
import streamlit as st
import pandas as pd
from modules.database import get_db
from modules.auth import hash_password, validate_password_strength


def page_admin(user: dict):
    if not user.get("is_admin"):
        st.error("🚫 Access Denied — You do not have administrator privileges.")
        return

    st.title("⚙️ Admin Panel")
    st.markdown("---")

    tabs = st.tabs(["📊 Overview", "👥 Users", "💬 Feedback", "📈 Activity", "🔐 Security"])

    # ── Overview ──────────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### System Overview")
        with get_db() as conn:
            def count(q): return conn.execute(q).fetchone()[0]
            total_users    = count("SELECT COUNT(*) FROM users")
            active_users   = count("SELECT COUNT(*) FROM users WHERE is_active=1")
            total_feedback = count("SELECT COUNT(*) FROM feedback")
            total_dash     = count("SELECT COUNT(*) FROM saved_dashboards")
            total_act      = count("SELECT COUNT(*) FROM user_activity")
            fail_1h        = count("""
                SELECT COUNT(*) FROM login_attempts
                WHERE success=0 AND attempted_at > datetime('now','-1 hour')""")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Users",       total_users)
        c2.metric("Active Users",      active_users)
        c3.metric("Saved Dashboards",  total_dash)
        c4.metric("Feedback Entries",  total_feedback)

        st.markdown("---")
        c5, c6 = st.columns(2)
        c5.metric("Total Activity Events", f"{total_act:,}")
        c6.metric("Failed Logins (1 hr)",  fail_1h,
                  delta_color="inverse" if fail_1h > 5 else "normal")

        st.markdown("#### Recent Registrations")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, created_at, last_login, is_active FROM users ORDER BY created_at DESC LIMIT 10")
            rows = cur.fetchall()
        if rows:
            df_u = pd.DataFrame([dict(r) for r in rows])
            df_u.columns = ["Username", "Registered", "Last Login", "Active"]
            df_u["Active"] = df_u["Active"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(df_u, use_container_width=True)

    # ── Users ─────────────────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 👥 User Management")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, is_admin, is_active, created_at, last_login FROM users ORDER BY created_at DESC")
            users = [dict(r) for r in cur.fetchall()]

        for u in users:
            status = "👑 Admin" if u["is_admin"] else "👤 User"
            active = "✅ Active" if u["is_active"] else "❌ Inactive"
            with st.expander(f"{status} — **{u['username']}** | {active}"):
                ic1, ic2, ic3, ic4 = st.columns(4)
                ic1.markdown(f"**ID:** {u['id']}")
                ic2.markdown(f"**Joined:** {str(u['created_at'])[:10]}")
                ic3.markdown(f"**Last Login:** {str(u['last_login'] or 'Never')[:16]}")

                if u["username"] == user["username"]:
                    ic4.markdown("*(current user)*")
                    continue

                toggle_label = "❌ Deactivate" if u["is_active"] else "✅ Activate"
                if ic4.button(toggle_label, key=f"toggle_{u['id']}", use_container_width=True):
                    with get_db() as conn:
                        conn.execute("UPDATE users SET is_active=? WHERE id=?",
                                     (0 if u["is_active"] else 1, u["id"]))
                    st.rerun()

                adm_label = "🔽 Remove Admin Role" if u["is_admin"] else "👑 Grant Admin Role"
                if st.button(adm_label, key=f"admin_{u['id']}"):
                    with get_db() as conn:
                        conn.execute("UPDATE users SET is_admin=? WHERE id=?",
                                     (0 if u["is_admin"] else 1, u["id"]))
                    st.rerun()

                with st.form(f"reset_pwd_{u['id']}"):
                    st.markdown("**Reset Password:**")
                    new_pwd = st.text_input("New Password", type="password", key=f"npwd_{u['id']}")
                    if st.form_submit_button("🔐 Reset Password"):
                        ok, msg = validate_password_strength(new_pwd)
                        if ok:
                            with get_db() as conn:
                                conn.execute("UPDATE users SET password=? WHERE id=?",
                                             (hash_password(new_pwd), u["id"]))
                            st.success(f"✅ Password for '{u['username']}' has been reset.")
                        else:
                            st.error(msg)

        st.markdown("---")
        if st.button("📥 Export Users List (CSV)", use_container_width=True):
            with get_db() as conn:
                cur = conn.cursor()
                # Passwords are intentionally excluded
                cur.execute("SELECT id, username, is_admin, is_active, created_at, last_login FROM users ORDER BY created_at DESC")
                rows = cur.fetchall()
            df_exp = pd.DataFrame([dict(r) for r in rows])
            buf = io.StringIO()
            df_exp.to_csv(buf, index=False)
            st.download_button("⬇️ Download CSV", buf.getvalue(),
                               file_name=f"users_{datetime.date.today()}.csv",
                               mime="text/csv", use_container_width=True)

    # ── Feedback ──────────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 💬 User Feedback")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, feedback, rating, created_at FROM feedback ORDER BY created_at DESC LIMIT 200")
            feedbacks = cur.fetchall()

        if not feedbacks:
            st.info("No feedback has been submitted yet.")
        else:
            st.markdown(f"**{len(feedbacks)} feedback entry/entries**")
            for fb in feedbacks:
                stars = "⭐" * (fb["rating"] or 5)
                st.markdown(f"""
                <div class='chart-card'>
                    <strong>{fb['username']}</strong> &nbsp; {stars} &nbsp;
                    <small style='opacity:.7'>{str(fb['created_at'])[:16]}</small><br>
                    {fb['feedback']}
                </div>
                """, unsafe_allow_html=True)

            if st.button("📥 Export Feedback (CSV)"):
                df_fb = pd.DataFrame([dict(r) for r in feedbacks])
                buf   = io.StringIO()
                df_fb.to_csv(buf, index=False)
                st.download_button("⬇️ Download CSV", buf.getvalue(),
                                   file_name=f"feedback_{datetime.date.today()}.csv",
                                   mime="text/csv")

    # ── Activity ──────────────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📈 Activity Log")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT u.username, a.event_type, a.event_data, a.created_at
                FROM user_activity a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.created_at DESC LIMIT 500""")
            activities = cur.fetchall()

        if activities:
            df_act      = pd.DataFrame([dict(r) for r in activities])
            event_types = ["All"] + list(df_act["event_type"].unique())
            sel_event   = st.selectbox("Filter by event type:", event_types)
            if sel_event != "All":
                df_act = df_act[df_act["event_type"] == sel_event]
            st.dataframe(df_act, use_container_width=True, height=400)

            if st.button("📥 Export Activity Log (CSV)"):
                buf = io.StringIO()
                df_act.to_csv(buf, index=False)
                st.download_button("⬇️ Download CSV", buf.getvalue(),
                                   file_name=f"activity_{datetime.date.today()}.csv",
                                   mime="text/csv")
        else:
            st.info("No activity records found.")

    # ── Security ──────────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🔐 Login Attempts Monitor")
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT username, success, attempted_at FROM login_attempts ORDER BY attempted_at DESC LIMIT 200")
            attempts = cur.fetchall()

        if attempts:
            df_att           = pd.DataFrame([dict(r) for r in attempts])
            df_att["Status"] = df_att["success"].apply(lambda x: "✅ Success" if x else "❌ Failed")
            fails_24h        = df_att[
                (df_att["success"] == 0) &
                (pd.to_datetime(df_att["attempted_at"]) > pd.Timestamp.now() - pd.Timedelta(hours=24))
            ]
            st.metric("Failed Logins (last 24 hours)", len(fails_24h))

            fail_counts = df_att[df_att["success"] == 0]["username"].value_counts()
            suspicious  = fail_counts[fail_counts >= 5]
            if len(suspicious):
                st.warning(f"⚠️ {len(suspicious)} account(s) with 5 or more failed attempts:")
                for uname, count in suspicious.items():
                    st.markdown(f"  - `{uname}`: {count} failed attempt(s)")

            st.dataframe(df_att[["username","Status","attempted_at"]], use_container_width=True, height=400)
        else:
            st.info("No login attempt records found.")

        st.markdown("---")
        if st.button("🧹 Clear Old Login Attempts (older than 30 days)", type="secondary"):
            with get_db() as conn:
                conn.execute("DELETE FROM login_attempts WHERE attempted_at < datetime('now', '-30 days')")
            st.success("✅ Old login attempt records have been cleared.")
