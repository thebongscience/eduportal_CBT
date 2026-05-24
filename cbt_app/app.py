"""
app.py  –  CBT Exam Portal  |  Main Entry / Login Page
Run:  streamlit run app.py
"""
import streamlit as st
import urllib.parse
from db import get_client, get_profile, submit_access_request, sign_in_with_google, sign_out

st.set_page_config(
    page_title="CBT Exam Portal",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed",
)

ADMIN_EMAIL = "thebongscience@gmail.com"

# ── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    #MainMenu, footer, header {visibility: hidden;}
    .stApp { background: #f0f4f8; }
    .login-card {
        background: white;
        border-radius: 16px;
        padding: 40px 48px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        margin: 40px auto;
        max-width: 480px;
    }
    .portal-btn {
        display: block;
        width: 100%;
        padding: 14px;
        margin: 10px 0;
        border-radius: 8px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        border: none;
        text-align: center;
    }
    .google-btn {
        background: #fff;
        color: #333;
        border: 1px solid #ddd !important;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
        padding: 12px;
        border-radius: 8px;
        font-size: 15px;
        font-weight: 500;
        cursor: pointer;
        width: 100%;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
    }
    .badge-pending  { background: #fff3cd; color: #856404; }
    .badge-approved { background: #d4edda; color: #155724; }
    .badge-rejected { background: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)


# ── HANDLE OAUTH CALLBACK ────────────────────────────────────
def handle_oauth_callback():
    """Pick up the access_token from URL after Google redirect."""
    params = st.query_params
    if "access_token" in params:
        token = params["access_token"]
        try:
            sb = get_client()
            sb.auth.set_session(token, params.get("refresh_token", ""))
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Auth error: {e}")


handle_oauth_callback()


# ── SESSION CHECK ────────────────────────────────────────────
def get_current_session():
    try:
        session = get_client().auth.get_session()
        return session
    except Exception:
        return None


session = get_current_session()

if session and session.user:
    user = session.user
    profile = get_profile(user.id)

    # Route to correct page
    if profile and profile["role"] == "admin":
        st.switch_page("pages/admin.py")
    elif profile and profile["status"] == "approved":
        st.switch_page("pages/student.py")
    elif profile and profile["status"] == "pending":
        st.markdown(f"""
        <div class="login-card" style="text-align:center;">
            <div style="font-size:56px;margin-bottom:16px;">⏳</div>
            <h2 style="margin:0 0 8px;color:#1a1a2e;">Request Pending</h2>
            <p style="color:#666;margin:0 0 24px;">
                Your access request is awaiting admin approval.<br>
                You'll be notified once <strong>{ADMIN_EMAIL}</strong> approves your account.
            </p>
            <div class="status-badge badge-pending">Pending Approval</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            sign_out()
            st.rerun()
    elif profile and profile["status"] == "rejected":
        st.markdown("""
        <div class="login-card" style="text-align:center;">
            <div style="font-size:56px;margin-bottom:16px;">❌</div>
            <h2 style="color:#dc3545;">Access Denied</h2>
            <p style="color:#666;">Your request was not approved. Contact the administrator.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign Out", use_container_width=True):
            sign_out()
            st.rerun()
    st.stop()


# ── LOGIN PAGE ───────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;margin-top:48px;margin-bottom:8px;">
    <div style="font-size:52px;">🎓</div>
    <h1 style="margin:8px 0 4px;color:#1a1a2e;font-size:28px;font-weight:700;">CBT Exam Portal</h1>
    <p style="color:#666;margin:0;">Computer Based Test Platform</p>
</div>
""", unsafe_allow_html=True)

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    tab1, tab2 = st.tabs(["🎒 Student Login", "🔐 Admin Login"])

    # ── STUDENT TAB ──────────────────────────────────────────
    with tab1:
        st.markdown("#### Sign in with Google")
        st.markdown("*Use your Gmail account. First-time users must request access.*")

        if st.button("🔵  Continue with Google", use_container_width=True, key="student_google"):
            try:
                url = sign_in_with_google()
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                st.markdown(f"[Click here if not redirected]({url})")
            except Exception as e:
                st.error(f"Could not initiate login: {e}")

        st.divider()
        st.markdown("**New student? Request access below:**")
        with st.form("access_form"):
            req_name = st.text_input("Full Name")
            req_email = st.text_input("Gmail Address")
            req_class = st.selectbox("Class", ["Class 11", "Class 12", "Dropper", "Other"])
            req_msg = st.text_area("Message (optional)", height=80)
            if st.form_submit_button("📨 Send Access Request", use_container_width=True):
                if req_name and req_email:
                    try:
                        submit_access_request(req_email, req_name, req_class, req_msg)
                        st.success("✅ Request sent! Admin will review and approve shortly.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                else:
                    st.warning("Please fill in name and email.")

    # ── ADMIN TAB ────────────────────────────────────────────
    with tab2:
        st.markdown(f"#### Admin Access")
        st.info(f"Only **{ADMIN_EMAIL}** can access the admin portal.", icon="🔐")

        if st.button("🔵  Sign in as Admin (Google)", use_container_width=True, key="admin_google"):
            try:
                url = sign_in_with_google()
                st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
                st.markdown(f"[Click here if not redirected]({url})")
            except Exception as e:
                st.error(f"Could not initiate login: {e}")

st.markdown("""
<div style="text-align:center;margin-top:32px;color:#aaa;font-size:12px;">
    CBT Exam Portal • Powered by Streamlit + Supabase
</div>
""", unsafe_allow_html=True)
