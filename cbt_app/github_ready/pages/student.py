"""
pages/student.py  –  Student Portal  (v2 — text + image questions)
"""
import streamlit as st
import time
import random
from db import (
    get_client, get_profile, sign_out,
    get_subjects, get_exams, sample_questions,
    create_attempt, submit_attempt, get_student_results
)
from question_renderer import render_question

st.set_page_config(page_title="Student Portal – CBT", page_icon="🎒", layout="wide")

st.markdown("""
<style>
    #MainMenu, footer { visibility: hidden; }
    .stApp { background: #f0f4f8; }
    .timer-box { background:#1a73e8;color:white;padding:4px 14px;border-radius:6px;font-weight:700;font-size:16px;font-family:monospace; }
    .timer-urgent { background:#e74c3c !important; }
</style>
""", unsafe_allow_html=True)

NOT_VISITED = "not_visited"
NOT_ANSWERED = "not_answered"
ANSWERED = "answered"
MARKED = "marked"
ANSWERED_MARKED = "answered_marked"

STATUS_COLOR = {
    NOT_VISITED:    "#e0e0e0",
    NOT_ANSWERED:   "#e74c3c",
    ANSWERED:       "#27ae60",
    MARKED:         "#8e44ad",
    ANSWERED_MARKED:"#8e44ad",
}
STATUS_TEXT = {
    NOT_VISITED: "#333", NOT_ANSWERED: "white",
    ANSWERED: "white", MARKED: "white", ANSWERED_MARKED: "white",
}

# ── AUTH GUARD ───────────────────────────────────────────────
try:
    session = get_client().auth.get_session()
    if not session or not session.user:
        st.error("Please log in.")
        if st.button("Go to Login"): st.switch_page("app.py")
        st.stop()
    user    = session.user
    profile = get_profile(user.id)
    if not profile or profile["status"] != "approved":
        st.error("Access not approved yet.")
        st.stop()
except Exception as e:
    st.error(f"Auth error: {e}"); st.stop()

# ── SESSION STATE ────────────────────────────────────────────
for k, v in {
    "page": "dashboard", "exam_id": None, "attempt_id": None,
    "questions": [], "current_q": 0, "answers": {}, "q_status": {},
    "start_time": None, "exam_meta": None, "confirm_submit": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

def fmt_time(s):
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"

# ─────────────────────────────────────────────────────────────
#  DASHBOARD
# ─────────────────────────────────────────────────────────────
def show_dashboard():
    c1, c2 = st.columns([5,1])
    with c1:
        st.markdown(f"## 🎒 Welcome, {profile.get('full_name','Student')}!")
        st.caption(f"{user.email}  •  {profile.get('class','')}")
    with c2:
        if st.button("Sign Out", use_container_width=True):
            sign_out(); st.switch_page("app.py")
    st.divider()

    tabs = st.tabs(["📚 Available Exams", "📊 My Results"])
    with tabs[0]:
        subjects = get_subjects(profile.get("class"))
        if not subjects:
            st.info("No subjects available for your class yet.")
        for subj in subjects:
            st.markdown(f"### 📚 {subj['name']}")
            exams = get_exams(subj["id"])
            if not exams:
                st.caption("No exams available."); continue
            for exam in exams:
                c1, c2, c3, c4 = st.columns([3,1,1,1])
                with c1: st.write(f"**{exam['title']}**")
                with c2: st.write(f"⏱ {exam['duration_mins']} min")
                with c3: st.write(f"❓ {exam['total_questions']} Q")
                with c4:
                    if st.button("Start ▶", key=f"start_{exam['id']}", use_container_width=True):
                        start_exam(exam)
            st.divider()

    with tabs[1]:
        results = get_student_results(user.id)
        if not results:
            st.info("No exams taken yet.")
        for r in results:
            exam_name = (r.get("exams") or {}).get("title","—")
            subj_name = ((r.get("exams") or {}).get("subjects") or {}).get("name","—")
            score, total = r.get("score",0), r.get("total",0)
            pct = round(score/total*100,1) if total else 0
            date = (r.get("submitted_at") or "")[:10]
            c1, c2, c3 = st.columns([3,1,1])
            with c1:
                st.write(f"**{exam_name}** — {subj_name}")
                st.caption(date)
            with c2: st.metric("Score", f"{score}/{total}")
            with c3:
                color = "green" if pct>=60 else ("orange" if pct>=40 else "red")
                st.markdown(f"<span style='color:{color};font-size:20px;font-weight:700;'>{pct}%</span>", unsafe_allow_html=True)
            st.divider()


def start_exam(exam):
    questions = sample_questions(exam["id"], exam["total_questions"])
    if not questions:
        st.error("No questions found. Contact admin."); return
    attempt = create_attempt(user.id, exam["id"], [str(q["id"]) for q in questions])
    if not attempt:
        st.error("Could not create attempt."); return
    st.session_state.update({
        "page": "exam", "exam_id": exam["id"],
        "attempt_id": attempt["id"], "questions": questions,
        "current_q": 0, "answers": {},
        "q_status": {q["id"]: NOT_VISITED for q in questions},
        "start_time": time.time(), "exam_meta": exam,
    })
    st.rerun()

# ─────────────────────────────────────────────────────────────
#  EXAM
# ─────────────────────────────────────────────────────────────
def show_exam():
    questions  = st.session_state.questions
    exam       = st.session_state.exam_meta
    current    = st.session_state.current_q
    q          = questions[current]
    q_id       = q["id"]
    total      = len(questions)
    elapsed    = int(time.time() - st.session_state.start_time)
    remaining  = max(0, exam["duration_mins"]*60 - elapsed)

    if remaining == 0:
        do_submit(); return

    # Mark first visit
    if st.session_state.q_status.get(q_id) == NOT_VISITED:
        st.session_state.q_status[q_id] = NOT_ANSWERED

    # ── Header ───────────────────────────────────────────────
    h1, h2 = st.columns([4,1])
    with h1:
        subj = (exam.get("subjects") or {}).get("name","")
        st.markdown(f"""
        <div style="background:white;border:1px solid #ddd;border-radius:8px;padding:12px 18px;margin-bottom:8px;font-size:13px;line-height:2;">
            <b>Candidate:</b> {profile.get('full_name','')} &nbsp;|&nbsp;
            <b>Exam:</b> {exam['title']} &nbsp;|&nbsp;
            <b>Subject:</b> {subj} &nbsp;|&nbsp;
            <b>Remaining:</b>
            <span style="background:{'#e74c3c' if remaining<300 else '#1a73e8'};color:white;padding:2px 12px;border-radius:5px;font-weight:700;font-family:monospace;">
                {fmt_time(remaining)}
            </span>
        </div>""", unsafe_allow_html=True)
    with h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔴 Submit Exam", use_container_width=True):
            st.session_state.confirm_submit = True

    # ── Body ─────────────────────────────────────────────────
    left, right = st.columns([3,1])

    with left:
        st.markdown(f"#### Question {current+1} of {total}")

        # Render using shared renderer (handles text / image_question / image_options)
        def on_answer(letter):
            st.session_state.answers[q_id] = letter
            cur = st.session_state.q_status.get(q_id)
            st.session_state.q_status[q_id] = (
                ANSWERED_MARKED if cur in (MARKED, ANSWERED_MARKED) else ANSWERED
            )
            st.rerun()

        render_question(q, st.session_state.answers.get(q_id), on_answer)

        # Action buttons
        st.markdown("<br>", unsafe_allow_html=True)
        b1, b2, b3, b4 = st.columns(4)
        with b1:
            if st.button("✅ Save & Next", use_container_width=True):   save_and_next()
        with b2:
            if st.button("🗑️ Clear",       use_container_width=True):   clear_answer()
        with b3:
            if st.button("🔖 Save & Mark", use_container_width=True):   save_and_mark()
        with b4:
            if st.button("📌 Mark & Next", use_container_width=True):   mark_only()

        nav1, _, nav2 = st.columns([1,4,1])
        with nav1:
            if st.button("◀ Back", use_container_width=True) and current>0:
                st.session_state.current_q -= 1; st.rerun()
        with nav2:
            if st.button("Next ▶", use_container_width=True) and current<total-1:
                st.session_state.current_q += 1; st.rerun()

    with right:
        statuses = st.session_state.q_status
        counts   = {s: sum(1 for v in statuses.values() if v==s)
                    for s in [NOT_VISITED,NOT_ANSWERED,ANSWERED,MARKED,ANSWERED_MARKED]}
        legend = [
            (NOT_VISITED,    "#e0e0e0", "#333",  "Not Visited"),
            (NOT_ANSWERED,   "#e74c3c", "white", "Not Answered"),
            (ANSWERED,       "#27ae60", "white", "Answered"),
            (MARKED,         "#8e44ad", "white", "Marked"),
            (ANSWERED_MARKED,"#8e44ad", "white", "Answered & Marked"),
        ]
        html = '<div style="border:1px dashed #aaa;border-radius:8px;padding:12px;margin-bottom:14px;font-size:12px;">'
        for key, bg, tc, label in legend:
            html += f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;"><div style="width:26px;height:26px;background:{bg};border-radius:4px;color:{tc};display:flex;align-items:center;justify-content:center;font-weight:700;font-size:11px;flex-shrink:0;">{counts[key]}</div><span>{label}</span></div>'
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)

        st.markdown("**Questions:**")
        cols = st.columns(4)
        for idx, question in enumerate(questions):
            qid = question["id"]
            s   = statuses.get(qid, NOT_VISITED)
            bg  = "#1a73e8" if idx==current else STATUS_COLOR[s]
            tc  = "white"   if idx==current else STATUS_TEXT[s]
            with cols[idx % 4]:
                if st.button(str(idx+1).zfill(2), key=f"nav_{idx}", use_container_width=True):
                    st.session_state.current_q = idx; st.rerun()

    # ── Confirm submit ────────────────────────────────────────
    if st.session_state.confirm_submit:
        with st.container():
            statuses = st.session_state.q_status
            st.warning(f"""
            **Submit exam?**
            Answered: {counts[ANSWERED]+counts[ANSWERED_MARKED]} &nbsp;|&nbsp;
            Not answered: {counts[NOT_ANSWERED]} &nbsp;|&nbsp;
            Not visited: {counts[NOT_VISITED]}
            """)
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ Yes, Submit", use_container_width=True): do_submit()
            with cc2:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.confirm_submit = False; st.rerun()

# ── Exam action helpers ───────────────────────────────────────
def save_and_next():
    q_id = st.session_state.questions[st.session_state.current_q]["id"]
    if st.session_state.answers.get(q_id):
        cur = st.session_state.q_status.get(q_id)
        st.session_state.q_status[q_id] = ANSWERED_MARKED if cur in (MARKED,ANSWERED_MARKED) else ANSWERED
    else:
        st.session_state.q_status[q_id] = NOT_ANSWERED
    if st.session_state.current_q < len(st.session_state.questions)-1:
        st.session_state.current_q += 1
    st.rerun()

def clear_answer():
    q_id = st.session_state.questions[st.session_state.current_q]["id"]
    st.session_state.answers.pop(q_id, None)
    st.session_state.q_status[q_id] = NOT_ANSWERED
    st.rerun()

def save_and_mark():
    q_id = st.session_state.questions[st.session_state.current_q]["id"]
    st.session_state.q_status[q_id] = ANSWERED_MARKED if st.session_state.answers.get(q_id) else MARKED
    if st.session_state.current_q < len(st.session_state.questions)-1:
        st.session_state.current_q += 1
    st.rerun()

def mark_only():
    q_id = st.session_state.questions[st.session_state.current_q]["id"]
    st.session_state.q_status[q_id] = ANSWERED_MARKED if st.session_state.answers.get(q_id) else MARKED
    st.rerun()

def do_submit():
    questions = st.session_state.questions
    answers   = st.session_state.answers
    elapsed   = int(time.time() - st.session_state.start_time)
    responses = {}
    score = 0
    total = len(questions) * 4
    for q in questions:
        q_id   = q["id"]
        given  = answers.get(q_id)
        is_correct = bool(given and given.upper() == q["answer"].upper())
        if is_correct:   score += 4
        elif given:      score -= 1
        responses[q_id] = {
            "answer":    given,
            "is_marked": st.session_state.q_status.get(q_id) in (MARKED, ANSWERED_MARKED),
            "is_correct": is_correct,
        }
    submit_attempt(st.session_state.attempt_id, responses, score, total, elapsed)
    correct = sum(1 for r in responses.values() if r["is_correct"])
    wrong   = sum(1 for r in responses.values() if r["answer"] and not r["is_correct"])
    st.session_state.update({
        "page": "result", "last_score": score, "last_total": total,
        "last_correct": correct, "last_wrong": wrong,
        "confirm_submit": False,
    })
    st.rerun()

# ─────────────────────────────────────────────────────────────
#  RESULT
# ─────────────────────────────────────────────────────────────
def show_result():
    score   = st.session_state.get("last_score",0)
    total   = st.session_state.get("last_total",0)
    correct = st.session_state.get("last_correct",0)
    wrong   = st.session_state.get("last_wrong",0)
    pct     = round(score/total*100,1) if total else 0

    st.markdown("# 🎓 Exam Submitted!")
    st.success("Your responses have been recorded.")
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Score",     f"{score}/{total}")
    with c2: st.metric("Percentage",f"{pct}%")
    with c3: st.metric("Correct",   correct)
    with c4: st.metric("Wrong",     wrong)

    if st.button("🏠 Back to Dashboard", use_container_width=True):
        st.session_state.page = "dashboard"; st.rerun()

# ── ROUTER ────────────────────────────────────────────────────
page = st.session_state.get("page","dashboard")
if   page == "exam":   show_exam()
elif page == "result": show_result()
else:                  show_dashboard()
