"""
pg_admin.py — Comprehensive Admin Panel
Full visibility: feedback (content+ratings), active users, activity, security,
dashboard stats, and admin password change.
"""
import io
import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
from modules.database import get_db
from modules.auth import hash_password, validate_password_strength, verify_password


def page_admin(user: dict):
    # Security: DB is_admin check (never inferred from username)
    if not user.get("is_admin"):
        st.error("🚫 Access Denied — You do not have administrator privileges.")
        return

    st.title("👑 Admin Dashboard")
    st.markdown(f"Welcome back, **{user['username']}**. Full system access enabled.")
    st.markdown("---")

    tabs = st.tabs([
        "📊 Overview",
        "👥 Active Users",
        "💬 Feedback",
        "📈 Activity Log",
        "🔐 Security",
        "💼 Dashboards",
        "⚙️ Admin Settings",
    ])

    # ── TAB 1: OVERVIEW ────────────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### 📊 System Overview")

        with get_db() as conn:
            def cnt(q, params=()): return conn.execute(q, params).fetchone()[0]

            total_users    = cnt("SELECT COUNT(*) FROM users")
            active_users   = cnt("SELECT COUNT(*) FROM users WHERE is_active=1")
            inactive_users = total_users - active_users
            admin_users    = cnt("SELECT COUNT(*) FROM users WHERE is_admin=1")
            total_feedback = cnt("SELECT COUNT(*) FROM feedback")
            avg_rating_row = conn.execute("SELECT AVG(rating) FROM feedback").fetchone()[0]
            avg_rating     = round(avg_rating_row, 1) if avg_rating_row else 0
            total_dash     = cnt("SELECT COUNT(*) FROM saved_dashboards")
            total_act      = cnt("SELECT COUNT(*) FROM user_activity")
            fail_1h        = cnt("""SELECT COUNT(*) FROM login_attempts
                                   WHERE success=0 AND attempted_at > datetime('now','-1 hour')""")
            new_today      = cnt("""SELECT COUNT(*) FROM users
                                   WHERE DATE(created_at)=DATE('now')""")
            logins_today   = cnt("""SELECT COUNT(*) FROM login_attempts
                                   WHERE success=1 AND DATE(attempted_at)=DATE('now')""")

        # KPI row 1
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Users",      total_users)
        k2.metric("Active Users",     active_users, delta=f"+{new_today} today")
        k3.metric("Inactive Users",   inactive_users)
        k4.metric("Admin Accounts",   admin_users)
        k5.metric("New Today",        new_today)

        st.markdown("---")

        # KPI row 2
        k6, k7, k8, k9, k10 = st.columns(5)
        k6.metric("Total Feedback",       total_feedback)
        k7.metric("Avg Rating",           f"{avg_rating} ⭐")
        k8.metric("Saved Dashboards",     total_dash)
        k9.metric("Activity Events",      f"{total_act:,}")
        k10.metric("Failed Logins (1hr)", fail_1h,
                   delta_color="inverse" if fail_1h > 5 else "normal")

        st.markdown("---")
        c1, c2 = st.columns(2)

        # Recent registrations
        with c1:
            st.markdown("#### 📅 Recent Registrations")
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT username, created_at, last_login, is_active, is_admin FROM users ORDER BY created_at DESC LIMIT 10"
                ).fetchall()
            if rows:
                df_reg = pd.DataFrame([dict(r) for r in rows])
                df_reg["is_active"] = df_reg["is_active"].apply(lambda x: "✅" if x else "❌")
                df_reg["is_admin"]  = df_reg["is_admin"].apply(lambda x: "👑" if x else "—")
                df_reg.columns      = ["Username", "Registered", "Last Login", "Active", "Admin"]
                st.dataframe(df_reg, use_container_width=True, height=280)

        # Login trend (last 7 days)
        with c2:
            st.markdown("#### 📈 Login Activity (Last 7 Days)")
            with get_db() as conn:
                rows7 = conn.execute("""
                    SELECT DATE(attempted_at) as day, COUNT(*) as cnt
                    FROM login_attempts WHERE success=1
                    AND attempted_at > datetime('now','-7 days')
                    GROUP BY day ORDER BY day
                """).fetchall()
            if rows7:
                df7 = pd.DataFrame([dict(r) for r in rows7])
                fig7 = px.bar(df7, x="day", y="cnt", title="Successful Logins per Day",
                              color_discrete_sequence=["#3b82f6"])
                fig7.update_layout(height=280, margin=dict(l=10, r=10, t=40, b=10),
                                   showlegend=False)
                st.plotly_chart(fig7, use_container_width=True)
            else:
                st.info("No login data for the last 7 days.")

    # ── TAB 2: ACTIVE USERS ────────────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 👥 User Management")

        # Filter controls
        fc1, fc2, fc3 = st.columns(3)
        filter_status = fc1.selectbox("Filter by Status:", ["All", "Active", "Inactive"])
        filter_role   = fc2.selectbox("Filter by Role:",   ["All", "Users", "Admins"])
        search_user   = fc3.text_input("Search username:", placeholder="type to filter...")

        with get_db() as conn:
            all_users = [dict(r) for r in conn.execute(
                "SELECT id, username, is_admin, is_active, created_at, last_login FROM users ORDER BY created_at DESC"
            ).fetchall()]

        # Apply filters
        if filter_status == "Active":
            all_users = [u for u in all_users if u["is_active"]]
        elif filter_status == "Inactive":
            all_users = [u for u in all_users if not u["is_active"]]
        if filter_role == "Admins":
            all_users = [u for u in all_users if u["is_admin"]]
        elif filter_role == "Users":
            all_users = [u for u in all_users if not u["is_admin"]]
        if search_user:
            all_users = [u for u in all_users if search_user.lower() in u["username"].lower()]

        st.markdown(f"**{len(all_users)} user(s) found**")

        for u in all_users:
            role_icon = "👑 Admin" if u["is_admin"] else "👤 User"
            status    = "✅ Active" if u["is_active"] else "❌ Inactive"
            with st.expander(f"{role_icon} — **{u['username']}** | {status}"):
                ic1, ic2, ic3 = st.columns(3)
                ic1.markdown(f"**ID:** {u['id']}")
                ic2.markdown(f"**Joined:** {str(u['created_at'])[:10]}")
                ic3.markdown(f"**Last Login:** {str(u['last_login'] or 'Never')[:16]}")

                if u["username"] == user["username"]:
                    st.info("*(This is your account)*")
                    continue

                a1, a2, a3, a4 = st.columns(4)

                # Activate / Deactivate
                if a1.button("❌ Deactivate" if u["is_active"] else "✅ Activate",
                              key=f"toggle_{u['id']}", use_container_width=True):
                    with get_db() as conn:
                        conn.execute("UPDATE users SET is_active=? WHERE id=?",
                                     (0 if u["is_active"] else 1, u["id"]))
                    st.rerun()

                # Grant / Remove admin
                if a2.button("🔽 Remove Admin" if u["is_admin"] else "👑 Make Admin",
                              key=f"admin_{u['id']}", use_container_width=True):
                    with get_db() as conn:
                        conn.execute("UPDATE users SET is_admin=? WHERE id=?",
                                     (0 if u["is_admin"] else 1, u["id"]))
                    st.rerun()

                # Delete user (with confirmation)
                confirm_del_key = f"confirm_del_{u['id']}"
                if not st.session_state.get(confirm_del_key):
                    if a3.button("🗑️ Delete User", key=f"del_{u['id']}", use_container_width=True):
                        st.session_state[confirm_del_key] = True
                        st.rerun()
                else:
                    a3.warning("Confirm?")
                    da1, da2 = st.columns(2)
                    if da1.button("✅ Yes", key=f"yes_del_{u['id']}"):
                        with get_db() as conn:
                            conn.execute("DELETE FROM users WHERE id=?", (u["id"],))
                        st.session_state.pop(confirm_del_key, None)
                        st.success(f"User '{u['username']}' deleted.")
                        st.rerun()
                    if da2.button("❌ No", key=f"no_del_{u['id']}"):
                        st.session_state.pop(confirm_del_key, None)
                        st.rerun()

                # Reset password
                with st.form(f"reset_pwd_{u['id']}"):
                    new_pwd = st.text_input("Reset Password:", type="password",
                                             key=f"npwd_{u['id']}")
                    if st.form_submit_button("🔐 Reset", use_container_width=True):
                        ok, msg = validate_password_strength(new_pwd)
                        if ok:
                            with get_db() as conn:
                                conn.execute("UPDATE users SET password=? WHERE id=?",
                                             (hash_password(new_pwd), u["id"]))
                            st.success(f"✅ Password for '{u['username']}' reset.")
                        else:
                            st.error(msg)

        st.markdown("---")
        if st.button("📥 Export Users CSV (no passwords)", use_container_width=True):
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT id, username, is_admin, is_active, created_at, last_login FROM users ORDER BY created_at DESC"
                ).fetchall()
            buf = io.StringIO()
            pd.DataFrame([dict(r) for r in rows]).to_csv(buf, index=False)
            st.download_button("⬇️ Download", buf.getvalue(),
                               file_name=f"users_{datetime.date.today()}.csv",
                               mime="text/csv", use_container_width=True)

    # ── TAB 3: FEEDBACK ────────────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 💬 All User Feedback")

        with get_db() as conn:
            fb_rows = conn.execute(
                "SELECT username, feedback, rating, created_at FROM feedback ORDER BY created_at DESC"
            ).fetchall()

        if not fb_rows:
            st.info("No feedback submitted yet.")
        else:
            st.markdown(f"**{len(fb_rows)} feedback entry/entries total**")

            # Rating distribution chart
            ratings = [r["rating"] or 5 for r in fb_rows]
            rating_df = pd.DataFrame({"Rating": ratings})
            rc = rating_df["Rating"].value_counts().sort_index().reset_index()
            rc.columns = ["Rating", "Count"]

            ch1, ch2 = st.columns([1, 2])
            with ch1:
                avg_r = sum(ratings) / len(ratings)
                st.metric("Total Feedback", len(fb_rows))
                st.metric("Average Rating", f"{avg_r:.1f} ⭐")
                stars_map = {5: "⭐⭐⭐⭐⭐", 4: "⭐⭐⭐⭐", 3: "⭐⭐⭐", 2: "⭐⭐", 1: "⭐"}
                for _, row in rc.iterrows():
                    st.markdown(f"{stars_map.get(int(row['Rating']),'')} — **{int(row['Count'])}** responses")

            with ch2:
                fig_r = px.bar(rc, x="Rating", y="Count", title="Feedback Rating Distribution",
                               color_discrete_sequence=["#f59e0b"], text="Count")
                fig_r.update_layout(height=260, margin=dict(l=10,r=10,t=40,b=10),
                                    showlegend=False, xaxis_tickmode="linear")
                st.plotly_chart(fig_r, use_container_width=True)

            st.markdown("---")
            st.markdown("#### All Feedback Entries")

            # Filter by rating
            filter_rating = st.selectbox("Filter by rating:", ["All", "5 ⭐", "4 ⭐", "3 ⭐", "2 ⭐", "1 ⭐"])
            rating_filter_map = {"All": None, "5 ⭐": 5, "4 ⭐": 4, "3 ⭐": 3, "2 ⭐": 2, "1 ⭐": 1}
            selected_rating   = rating_filter_map[filter_rating]

            for fb in fb_rows:
                r = fb["rating"] or 5
                if selected_rating is not None and r != selected_rating:
                    continue
                stars = "⭐" * r
                # Color code by rating
                bg_color = {"5":"#f0fdf4","4":"#f0fdf4","3":"#fefce8","2":"#fff7ed","1":"#fef2f2"}.get(str(r),"#f8fafc")
                st.markdown(f"""
                <div style='background:{bg_color};padding:12px 16px;border-radius:10px;
                     margin:6px 0;border:1px solid #e2e8f0'>
                    <div style='display:flex;justify-content:space-between;margin-bottom:6px'>
                        <strong style='color:#1e293b'>👤 {fb['username']}</strong>
                        <span>{stars} &nbsp; <small style='color:#64748b'>{str(fb['created_at'])[:16]}</small></span>
                    </div>
                    <div style='color:#334155'>{fb['feedback']}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            if st.button("📥 Export Feedback CSV"):
                df_fb = pd.DataFrame([dict(r) for r in fb_rows])
                buf   = io.StringIO()
                df_fb.to_csv(buf, index=False)
                st.download_button("⬇️ Download", buf.getvalue(),
                                   file_name=f"feedback_{datetime.date.today()}.csv",
                                   mime="text/csv", use_container_width=True)

    # ── TAB 4: ACTIVITY LOG ────────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 📈 Activity Log")

        with get_db() as conn:
            act_rows = conn.execute("""
                SELECT u.username, a.event_type, a.event_data, a.created_at
                FROM user_activity a
                LEFT JOIN users u ON a.user_id = u.id
                ORDER BY a.created_at DESC LIMIT 500
            """).fetchall()

        if not act_rows:
            st.info("No activity records yet.")
        else:
            df_act = pd.DataFrame([dict(r) for r in act_rows])

            # Filters
            af1, af2 = st.columns(2)
            event_types = ["All"] + sorted(df_act["event_type"].dropna().unique().tolist())
            sel_event   = af1.selectbox("Filter by event:", event_types)
            sel_user_a  = af2.text_input("Filter by username:", placeholder="type to filter...")

            if sel_event != "All":
                df_act = df_act[df_act["event_type"] == sel_event]
            if sel_user_a:
                df_act = df_act[df_act["username"].fillna("").str.contains(sel_user_a, case=False)]

            st.markdown(f"**{len(df_act)} event(s) shown**")
            st.dataframe(df_act, use_container_width=True, height=400)

            if st.button("📥 Export Activity CSV"):
                buf = io.StringIO()
                df_act.to_csv(buf, index=False)
                st.download_button("⬇️ Download", buf.getvalue(),
                                   file_name=f"activity_{datetime.date.today()}.csv",
                                   mime="text/csv", use_container_width=True)

    # ── TAB 5: SECURITY ────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 🔐 Security Monitor")

        with get_db() as conn:
            attempts = conn.execute(
                "SELECT username, success, attempted_at FROM login_attempts ORDER BY attempted_at DESC LIMIT 300"
            ).fetchall()

        if not attempts:
            st.info("No login attempt records.")
        else:
            df_att = pd.DataFrame([dict(r) for r in attempts])
            df_att["Status"] = df_att["success"].apply(lambda x: "✅ Success" if x else "❌ Failed")

            # Metrics
            total_attempts = len(df_att)
            total_fails    = int((df_att["success"] == 0).sum())
            total_success  = total_attempts - total_fails
            attempted_at_24h = pd.to_datetime(df_att["attempted_at"], errors="coerce")
            fails_24h      = int(
                ((df_att["success"] == 0) &
                 (attempted_at_24h > pd.Timestamp.now() - pd.Timedelta(hours=24)))
                .sum()
            ) if total_fails > 0 else 0

            sc1, sc2, sc3, sc4 = st.columns(4)
            sc1.metric("Total Login Attempts",   total_attempts)
            sc2.metric("Successful Logins",      total_success)
            sc3.metric("Failed Logins",          total_fails)
            sc4.metric("Failed in Last 24h",     fails_24h)

            # Suspicious accounts (5+ failures)
            fail_counts = df_att[df_att["success"] == 0]["username"].value_counts()
            suspicious  = fail_counts[fail_counts >= 5]
            if len(suspicious):
                st.warning(f"⚠️ {len(suspicious)} account(s) with 5+ failed attempts:")
                for uname, cnt in suspicious.items():
                    sc1b, sc2b = st.columns([3, 1])
                    sc1b.markdown(f"  `{uname}` — **{cnt}** failed attempts")
                    if sc2b.button("🔒 Force Lock Review", key=f"lock_{uname}"):
                        st.info(f"To lock {uname}: use User Management tab to deactivate.")

            st.dataframe(df_att[["username", "Status", "attempted_at"]],
                         use_container_width=True, height=350)

            st.markdown("---")
            if st.button("🧹 Clear Login Attempts Older Than 30 Days", type="secondary"):
                with get_db() as conn:
                    conn.execute(
                        "DELETE FROM login_attempts WHERE attempted_at < datetime('now','-30 days')"
                    )
                st.success("Old login attempt records cleared.")
                st.rerun()

    # ── TAB 6: DASHBOARDS ─────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### 💼 Saved Dashboards — All Users")

        with get_db() as conn:
            dash_rows = conn.execute("""
                SELECT u.username, s.dashboard_name, s.description,
                       s.created_at, s.updated_at
                FROM saved_dashboards s
                LEFT JOIN users u ON s.user_id = u.id
                ORDER BY s.updated_at DESC
            """).fetchall()

        if not dash_rows:
            st.info("No saved dashboards yet.")
        else:
            df_dash = pd.DataFrame([dict(r) for r in dash_rows])
            st.metric("Total Saved Dashboards", len(df_dash))

            # Per-user breakdown
            per_user = df_dash["username"].value_counts().reset_index()
            per_user.columns = ["Username", "Dashboards"]

            dc1, dc2 = st.columns([1, 2])
            with dc1:
                st.markdown("#### Per-User Count")
                st.dataframe(per_user, use_container_width=True, height=260)
            with dc2:
                fig_d = px.bar(per_user.head(15), x="Username", y="Dashboards",
                               title="Dashboards per User",
                               color_discrete_sequence=["#8b5cf6"])
                fig_d.update_layout(height=260, margin=dict(l=10,r=10,t=40,b=10))
                st.plotly_chart(fig_d, use_container_width=True)

            st.markdown("#### All Dashboards")
            st.dataframe(df_dash, use_container_width=True, height=350)

    # ── TAB 7: ADMIN SETTINGS ─────────────────────────────────────────────────
    with tabs[6]:
        st.markdown("### ⚙️ Admin Settings")

        # Change admin password
        st.markdown("#### 🔑 Change Admin Password")
        st.info("Only the admin can change this password.")

        with st.form("admin_change_pwd"):
            curr = st.text_input("Current Password", type="password")
            new1 = st.text_input("New Password", type="password",
                                  placeholder="8+ chars, uppercase, digit, special")
            new2 = st.text_input("Confirm New Password", type="password")
            submitted_pwd = st.form_submit_button("🔐 Update Password", type="primary",
                                                   use_container_width=True)

        if submitted_pwd:
            if not curr or not new1 or not new2:
                st.error("All fields required.")
            elif new1 != new2:
                st.error("New passwords do not match.")
            else:
                # Verify current password
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT password FROM users WHERE username=?", (user["username"],)
                    ).fetchone()
                if not row or not verify_password(curr, row["password"]):
                    st.error("Current password is incorrect.")
                else:
                    ok, msg = validate_password_strength(new1)
                    if not ok:
                        st.error(msg)
                    else:
                        with get_db() as conn:
                            conn.execute(
                                "UPDATE users SET password=? WHERE username=?",
                                (hash_password(new1), user["username"])
                            )
                        st.success("✅ Admin password updated successfully!")

        st.markdown("---")
        st.markdown("#### 🗄️ Database Maintenance")

        m1, m2, m3 = st.columns(3)
        if m1.button("🧹 Clear Old Login Attempts (30d)", use_container_width=True):
            with get_db() as conn:
                conn.execute("DELETE FROM login_attempts WHERE attempted_at < datetime('now','-30 days')")
            st.success("Old login attempts cleared.")

        if m2.button("🧹 Clear Expired Reset Tokens", use_container_width=True):
            with get_db() as conn:
                conn.execute("DELETE FROM password_reset_tokens WHERE expires_at < datetime('now')")
            st.success("Expired tokens cleared.")

        if m3.button("📊 DB Stats", use_container_width=True):
            with get_db() as conn:
                tables = ["users","login_attempts","feedback",
                          "saved_dashboards","user_activity","password_reset_tokens"]
                stats  = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
            for t, c in stats.items():
                st.markdown(f"  - **{t}**: {c:,} rows")
