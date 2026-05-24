"""
pages/admin.py  –  Admin Portal  (v2 — text + image questions)
"""
import streamlit as st
import pandas as pd
from db import (
    get_client, get_profile, sign_out,
    get_all_students, get_pending_requests, approve_request, reject_request,
    get_subjects, create_subject, delete_subject,
    get_exams, create_exam, update_exam,
    get_questions, bulk_insert_text_questions,
    get_all_results
)
from image_questions_tab import render_image_question_uploader

st.set_page_config(page_title="Admin Portal – CBT", page_icon="🔐", layout="wide")

ADMIN_EMAIL = "thebongscience@gmail.com"

st.markdown("""
<style>
    #MainMenu, footer {visibility: hidden;}
    .stApp { background: #f0f4f8; }
    .section-header {
        font-size: 18px; font-weight: 700; color: #1a1a2e;
        margin: 24px 0 16px; padding-bottom: 8px;
        border-bottom: 2px solid #1a73e8;
    }
</style>
""", unsafe_allow_html=True)

# ── AUTH GUARD ───────────────────────────────────────────────
try:
    session = get_client().auth.get_session()
    if not session or not session.user:
        st.error("Not logged in.")
        if st.button("Go to Login"): st.switch_page("app.py")
        st.stop()
    user = session.user
    profile = get_profile(user.id)
    if not profile or profile["role"] != "admin" or user.email != ADMIN_EMAIL:
        st.error("Access denied. Admin only.")
        st.stop()
except Exception as e:
    st.error(f"Auth error: {e}"); st.stop()

# ── HEADER ───────────────────────────────────────────────────
col1, col2 = st.columns([5, 1])
with col1:
    st.markdown("## 🔐 Admin Portal")
    st.caption(f"Logged in as: **{user.email}**")
with col2:
    if st.button("Sign Out", use_container_width=True):
        sign_out(); st.switch_page("app.py")

st.divider()

# ── METRICS ──────────────────────────────────────────────────
students    = get_all_students()
pending_req = get_pending_requests()
all_exams   = get_exams()
all_results = get_all_results()

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Total Students",   len([s for s in students if s["status"] == "approved"]))
with c2: st.metric("Pending Requests", len(pending_req))
with c3: st.metric("Active Exams",     len(all_exams))
with c4: st.metric("Total Attempts",   len(all_results))

st.divider()

# ── TABS ─────────────────────────────────────────────────────
tab_req, tab_students, tab_subjects, tab_exams, tab_questions, tab_results = st.tabs([
    "📨 Access Requests", "👥 Students", "📚 Subjects",
    "📝 Exams", "❓ Questions", "📊 Results"
])

# ── TAB 1: ACCESS REQUESTS ───────────────────────────────────
with tab_req:
    st.markdown('<div class="section-header">Pending Access Requests</div>', unsafe_allow_html=True)
    if not pending_req:
        st.info("No pending requests.")
    else:
        for req in pending_req:
            with st.expander(f"📩 {req['full_name']} — {req['email']} ({req['class']})"):
                st.write(f"**Email:** {req['email']}")
                st.write(f"**Class:** {req['class']}")
                st.write(f"**Message:** {req.get('message','—')}")
                st.write(f"**Requested:** {req['created_at'][:10]}")
                ca, cb = st.columns(2)
                with ca:
                    if st.button("✅ Approve", key=f"approve_{req['id']}", use_container_width=True):
                        approve_request(req["id"], req["email"], req["class"])
                        st.success("Approved!"); st.rerun()
                with cb:
                    if st.button("❌ Reject", key=f"reject_{req['id']}", use_container_width=True):
                        reject_request(req["id"], req["email"])
                        st.warning("Rejected."); st.rerun()

# ── TAB 2: STUDENTS ──────────────────────────────────────────
with tab_students:
    st.markdown('<div class="section-header">All Students</div>', unsafe_allow_html=True)
    if students:
        df = pd.DataFrame(students)[["full_name","email","class","status","created_at"]]
        df.columns = ["Name","Email","Class","Status","Joined"]
        df["Joined"] = pd.to_datetime(df["Joined"]).dt.strftime("%Y-%m-%d")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.markdown("**Change student status:**")
        sel_email  = st.selectbox("Select student", [s["email"] for s in students])
        sel_status = st.selectbox("New status", ["approved","pending","rejected"])
        if st.button("Update Status"):
            s = next(x for x in students if x["email"] == sel_email)
            get_client().table("profiles").update({"status": sel_status}).eq("id", s["id"]).execute()
            st.success(f"Updated {sel_email} to {sel_status}"); st.rerun()
    else:
        st.info("No students yet.")

# ── TAB 3: SUBJECTS ──────────────────────────────────────────
with tab_subjects:
    st.markdown('<div class="section-header">Manage Subjects</div>', unsafe_allow_html=True)
    with st.form("new_subject"):
        c1, c2, c3 = st.columns(3)
        with c1: sub_name  = st.text_input("Subject Name", placeholder="Chemistry, Physics…")
        with c2: sub_class = st.selectbox("For Class", ["Class 11","Class 12","Dropper","All"])
        with c3: sub_img   = st.checkbox("Has image-based questions?", value=False)
        if st.form_submit_button("➕ Add Subject", use_container_width=True):
            if sub_name:
                create_subject(sub_name, sub_class, user.id, sub_img)
                st.success(f"Subject '{sub_name}' added!"); st.rerun()

    subjects = get_subjects()
    if subjects:
        for subj in subjects:
            c1, c2, c3, c4 = st.columns([3, 2, 1, 1])
            with c1: st.write(f"📚 **{subj['name']}**")
            with c2: st.write(subj["class"])
            with c3: st.write("🖼️ Images" if subj.get("has_image_qs") else "📝 Text")
            with c4:
                if st.button("🗑️", key=f"del_sub_{subj['id']}"):
                    delete_subject(subj["id"]); st.rerun()
    else:
        st.info("No subjects yet.")

# ── TAB 4: EXAMS ─────────────────────────────────────────────
with tab_exams:
    st.markdown('<div class="section-header">Create & Manage Exams</div>', unsafe_allow_html=True)
    subjects = get_subjects()
    if not subjects:
        st.warning("Create a subject first.")
    else:
        sub_map = {s["name"]: s["id"] for s in subjects}
        with st.form("new_exam"):
            c1, c2 = st.columns(2)
            with c1:
                exam_title   = st.text_input("Exam Title", placeholder="NEET Mock Test 1")
                exam_subject = st.selectbox("Subject", list(sub_map.keys()))
            with c2:
                exam_questions = st.number_input("Questions to serve from pool", min_value=1, max_value=500, value=100)
                exam_duration  = st.number_input("Duration (minutes)", min_value=5, max_value=360, value=180)
            if st.form_submit_button("➕ Create Exam", use_container_width=True):
                if exam_title:
                    create_exam(sub_map[exam_subject], exam_title, exam_questions, exam_duration, user.id)
                    st.success(f"Exam '{exam_title}' created!"); st.rerun()

        st.markdown("#### Existing Exams")
        exams = get_exams()
        for exam in exams:
            subj_name = (exam.get("subjects") or {}).get("name","")
            with st.expander(f"📝 {exam['title']} — {subj_name} ({exam['total_questions']}Q / {exam['duration_mins']}min)"):
                c1, c2, c3 = st.columns(3)
                with c1: new_q = st.number_input("Questions", value=exam["total_questions"], key=f"eq_{exam['id']}")
                with c2: new_d = st.number_input("Duration (min)", value=exam["duration_mins"], key=f"ed_{exam['id']}")
                with c3: new_a = st.checkbox("Active", value=exam["is_active"], key=f"ea_{exam['id']}")
                if st.button("💾 Save", key=f"save_{exam['id']}"):
                    update_exam(exam["id"], {"total_questions": new_q, "duration_mins": new_d, "is_active": new_a})
                    st.success("Updated!"); st.rerun()

# ── TAB 5: QUESTIONS ─────────────────────────────────────────
with tab_questions:
    st.markdown('<div class="section-header">Upload Questions</div>', unsafe_allow_html=True)

    exams = get_exams()
    if not exams:
        st.warning("Create an exam first (Exams tab).")
    else:
        exam_map = {
            f"{e['title']} — {(e.get('subjects') or {}).get('name','')}": e["id"]
            for e in exams
        }
        sel_exam_label = st.selectbox("Select Exam", list(exam_map.keys()))
        sel_exam_id    = exam_map[sel_exam_label]

        q_tab1, q_tab2 = st.tabs(["📊 Text Questions (Excel)", "🖼️ Image Questions"])

        # ── TEXT QUESTIONS ────────────────────────────────────
        with q_tab1:
            st.markdown("#### Upload Excel sheet")
            st.info("""
**Excel columns A → G (exact format):**

| A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|
| Question No | Question | Option A | Option B | Option C | Option D | Correct Option |

Row 1 = header row. Answer column must contain **A, B, C, or D**.
Upload as many questions as needed (250+). Admin controls how many are served per test.
            """)

            uploaded = st.file_uploader("Upload .xlsx file", type=["xlsx","xls"])
            if uploaded:
                try:
                    df = pd.read_excel(uploaded, header=0)
                    st.success(f"✅ Found **{len(df)} questions** in the file.")

                    # Preview with correct column labels
                    preview = df.head(5).copy()
                    st.dataframe(preview, use_container_width=True, hide_index=True)
                    st.caption(f"Showing first 5 of {len(df)} rows.")

                    if st.button(f"⬆️ Upload all {len(df)} questions", use_container_width=True):
                        bulk_insert_text_questions(sel_exam_id, df)
                        st.success(f"✅ {len(df)} questions uploaded!"); st.rerun()
                except Exception as e:
                    st.error(f"Error reading file: {e}")

            # Preview existing text questions
            existing = [q for q in get_questions(sel_exam_id) if q.get("question_type","text") == "text"]
            if existing:
                st.markdown(f"#### Existing text questions: **{len(existing)}** in pool")
                df_ex = pd.DataFrame(existing)[["q_number","question","option_a","option_b","option_c","option_d","answer"]]
                df_ex.columns = ["#","Question","A","B","C","D","Answer"]
                st.dataframe(df_ex, use_container_width=True, hide_index=True, height=300)

        # ── IMAGE QUESTIONS ───────────────────────────────────
        with q_tab2:
            render_image_question_uploader(sel_exam_id, user.id)

# ── TAB 6: RESULTS ───────────────────────────────────────────
with tab_results:
    st.markdown('<div class="section-header">All Student Results</div>', unsafe_allow_html=True)
    if all_results:
        rows = []
        for r in all_results:
            rows.append({
                "Student": (r.get("profiles") or {}).get("full_name","—"),
                "Email":   (r.get("profiles") or {}).get("email","—"),
                "Exam":    (r.get("exams") or {}).get("title","—"),
                "Subject": ((r.get("exams") or {}).get("subjects") or {}).get("name","—"),
                "Score":   r.get("score",0),
                "Total":   r.get("total",0),
                "Time (min)": round((r.get("time_taken_secs") or 0) / 60, 1),
                "Submitted":  (r.get("submitted_at") or "")[:10],
            })
        df_res = pd.DataFrame(rows)
        st.dataframe(df_res, use_container_width=True, hide_index=True)
        csv = df_res.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download CSV", csv, "results.csv", "text/csv", use_container_width=True)
    else:
        st.info("No results yet.")
