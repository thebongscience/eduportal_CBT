"""
db.py  –  Supabase client wrapper for CBT Portal  (v2 – image question support)
"""
import streamlit as st
from supabase import create_client, Client
import random


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ── AUTH ──────────────────────────────────────────────────────

def sign_in_with_google():
    sb = get_client()
    redirect = st.secrets.get("auth", {}).get("redirect_url", "http://localhost:8501")
    res = sb.auth.sign_in_with_oauth({"provider": "google", "options": {"redirect_to": redirect}})
    return res.url


def get_session():
    return get_client().auth.get_session()


def get_user():
    session = get_session()
    return session.user if session else None


def sign_out():
    get_client().auth.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]


# ── PROFILES ─────────────────────────────────────────────────

def get_profile(user_id: str):
    res = get_client().table("profiles").select("*").eq("id", user_id).single().execute()
    return res.data


def update_profile(user_id: str, data: dict):
    return get_client().table("profiles").update(data).eq("id", user_id).execute()


def get_all_students():
    return get_client().table("profiles").select("*").eq("role", "student").order("created_at", desc=True).execute().data


# ── ACCESS REQUESTS ──────────────────────────────────────────

def submit_access_request(email, full_name, class_name, message=""):
    return get_client().table("access_requests").insert({
        "email": email, "full_name": full_name,
        "class": class_name, "message": message, "status": "pending"
    }).execute()


def get_pending_requests():
    return get_client().table("access_requests").select("*").eq("status", "pending").order("created_at", desc=True).execute().data


def approve_request(request_id, email, class_name):
    get_client().table("access_requests").update({"status": "approved"}).eq("id", request_id).execute()
    get_client().table("profiles").update({"status": "approved", "class": class_name}).eq("email", email).execute()


def reject_request(request_id, email):
    get_client().table("access_requests").update({"status": "rejected"}).eq("id", request_id).execute()
    get_client().table("profiles").update({"status": "rejected"}).eq("email", email).execute()


# ── SUBJECTS ─────────────────────────────────────────────────

def get_subjects(class_filter=None):
    q = get_client().table("subjects").select("*")
    if class_filter:
        q = q.or_(f"class.eq.{class_filter},class.eq.All")
    return q.order("name").execute().data


def create_subject(name, class_name, created_by, has_image_qs=False):
    return get_client().table("subjects").insert({
        "name": name, "class": class_name,
        "created_by": created_by, "has_image_qs": has_image_qs
    }).execute()


def delete_subject(subject_id):
    return get_client().table("subjects").delete().eq("id", subject_id).execute()


# ── EXAMS ─────────────────────────────────────────────────────

def get_exams(subject_id=None):
    q = get_client().table("exams").select("*, subjects(name, class, has_image_qs)")
    if subject_id:
        q = q.eq("subject_id", subject_id)
    return q.eq("is_active", True).order("created_at", desc=True).execute().data


def create_exam(subject_id, title, total_questions, duration_mins, created_by):
    return get_client().table("exams").insert({
        "subject_id": subject_id, "title": title,
        "total_questions": total_questions, "duration_mins": duration_mins,
        "created_by": created_by
    }).execute()


def update_exam(exam_id, data):
    return get_client().table("exams").update(data).eq("id", exam_id).execute()


# ── QUESTIONS ────────────────────────────────────────────────

def get_questions(exam_id):
    return get_client().table("questions").select("*").eq("exam_id", exam_id).order("q_number").execute().data


def sample_questions(exam_id, n):
    """Randomly sample n questions from pool."""
    all_q = get_questions(exam_id)
    return random.sample(all_q, min(n, len(all_q)))


def bulk_insert_text_questions(exam_id: str, df):
    """
    Parse the exact Excel format from the screenshot:
    Column A: Question No
    Column B: Question
    Column C: Option A
    Column D: Option B
    Column E: Option C
    Column F: Option D
    Column G: Correct Option  (value is A, B, C, or D)
    """
    # Normalize column names — handle both exact headers and positional
    col_map = {
        0: "q_number",
        1: "question",
        2: "option_a",
        3: "option_b",
        4: "option_c",
        5: "option_d",
        6: "answer",
    }
    # If dataframe has named columns matching the screenshot headers
    header_aliases = {
        "question no": "q_number",
        "question number": "q_number",
        "q no": "q_number",
        "question": "question",
        "option a": "option_a",
        "option b": "option_b",
        "option c": "option_c",
        "option d": "option_d",
        "correct option": "answer",
        "answer": "answer",
        "correct answer": "answer",
    }
    # Rename columns by matching lowercase header names
    rename = {}
    for col in df.columns:
        clean = str(col).lower().strip()
        if clean in header_aliases:
            rename[col] = header_aliases[clean]
    if rename:
        df = df.rename(columns=rename)
    else:
        # Fall back to positional (columns A-G by index)
        df.columns = list(col_map.values())[:len(df.columns)]

    df = df.dropna(subset=["question"])

    rows = []
    for _, row in df.iterrows():
        rows.append({
            "exam_id": exam_id,
            "q_number": int(row.get("q_number", 0)),
            "question_type": "text",
            "question": str(row["question"]).strip(),
            "option_a": str(row.get("option_a", "")).strip(),
            "option_b": str(row.get("option_b", "")).strip(),
            "option_c": str(row.get("option_c", "")).strip(),
            "option_d": str(row.get("option_d", "")).strip(),
            "answer": str(row.get("answer", "A")).upper().strip()[0],  # ensure single letter
        })

    # Replace existing questions
    get_client().table("questions").delete().eq("exam_id", exam_id).execute()
    return get_client().table("questions").insert(rows).execute()


# ── IMAGE QUESTIONS ──────────────────────────────────────────

def upload_question_image(file_bytes: bytes, filename: str, exam_id: str) -> str:
    """
    Upload image to Supabase Storage bucket 'question-images'.
    Returns public URL of uploaded image.
    """
    sb = get_client()
    path = f"{exam_id}/{filename}"
    sb.storage.from_("question-images").upload(
        path, file_bytes,
        {"content-type": "image/png", "upsert": "true"}
    )
    url = sb.storage.from_("question-images").get_public_url(path)
    return url


def insert_image_question(exam_id: str, q_data: dict) -> None:
    """
    Insert a single image-type question.

    q_data keys:
        q_number        int
        question_type   'image_question' | 'image_options'
        question        str  (text of the question or label like "Identify the structure:")
        image_url       str  (Supabase Storage URL — for image_question type)
        option_a/b/c/d  str  (text labels — always required)
        option_a/b/c/d_image_url  str  (URLs — for image_options type, optional)
        answer          str  'A'|'B'|'C'|'D'
    """
    row = {
        "exam_id": exam_id,
        "q_number": q_data["q_number"],
        "question_type": q_data.get("question_type", "image_question"),
        "question": q_data.get("question", ""),
        "image_url": q_data.get("image_url"),
        "option_a": q_data.get("option_a", ""),
        "option_b": q_data.get("option_b", ""),
        "option_c": q_data.get("option_c", ""),
        "option_d": q_data.get("option_d", ""),
        "option_a_image_url": q_data.get("option_a_image_url"),
        "option_b_image_url": q_data.get("option_b_image_url"),
        "option_c_image_url": q_data.get("option_c_image_url"),
        "option_d_image_url": q_data.get("option_d_image_url"),
        "answer": str(q_data.get("answer", "A")).upper().strip()[0],
    }
    get_client().table("questions").insert(row).execute()


def delete_questions_for_exam(exam_id: str):
    get_client().table("questions").delete().eq("exam_id", exam_id).execute()


# ── ATTEMPTS ─────────────────────────────────────────────────

def create_attempt(student_id, exam_id, question_ids):
    res = get_client().table("attempts").insert({
        "student_id": student_id, "exam_id": exam_id,
        "question_ids": question_ids, "status": "in_progress"
    }).execute()
    return res.data[0] if res.data else None


def submit_attempt(attempt_id, responses, score, total, time_taken):
    from datetime import datetime
    rows = []
    for qid, resp in responses.items():
        rows.append({
            "attempt_id": attempt_id, "question_id": qid,
            "answer": resp.get("answer"),
            "is_marked": resp.get("is_marked", False),
            "is_correct": resp.get("is_correct", False),
        })
    if rows:
        get_client().table("responses").insert(rows).execute()
    return get_client().table("attempts").update({
        "status": "submitted",
        "submitted_at": datetime.utcnow().isoformat(),
        "time_taken_secs": time_taken,
        "score": score, "total": total
    }).eq("id", attempt_id).execute()


def get_student_results(student_id):
    return get_client().table("attempts").select("*, exams(title, subjects(name))").eq("student_id", student_id).eq("status", "submitted").order("submitted_at", desc=True).execute().data


def get_all_results():
    return get_client().table("attempts").select("*, profiles(full_name, email), exams(title, subjects(name))").eq("status", "submitted").order("submitted_at", desc=True).execute().data
