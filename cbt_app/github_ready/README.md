# 🎓 CBT Exam Portal

A Computer Based Test (CBT) platform built with **Streamlit + Supabase**, designed for NEET / JEE style online exams.

## ✨ Features

### Admin Portal
- 📚 Create Subjects and Classes (Subject → Class hierarchy)
- 📝 Create Exams per class with custom timer and question count
- ❓ Upload questions via Excel (250+ questions, random sampling per test)
- 🖼️ Image-based questions — Type 1 (diagram in question) & Type 2 (image options)
- 👥 Approve / Reject student access requests + assign to Subject & Class
- 📊 Analytics — per-student and per-class performance dashboard
- 🏆 Full results table with CSV export

### Student Portal
- 🎒 Request access to the portal (admin approves)
- 📝 NEET-style CBT exam (countdown timer, question palette, mark for review)
- 📊 Personal analytics — score trend, accuracy %, performance band
- 📋 Full exam history

### Exam Interface (NEET-style)
- ⏱️ Countdown timer with auto-submit
- 🟢🔴🟣 Question palette (Not Visited / Not Answered / Answered / Marked for Review)
- Save & Next · Clear · Save & Mark for Review · Mark & Next
- Confirm-before-submit summary popup

## 🗂️ Project Structure

```
cbt_app/
├── app.py                      ← Main entry / Login page
├── db.py                       ← Supabase database wrapper
├── question_renderer.py        ← Renders text + image questions
├── image_questions_tab.py      ← Admin image question uploader
├── requirements.txt
├── supabase_schema.sql         ← Run in Supabase SQL Editor
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.template   ← Copy → secrets.toml, fill credentials
└── pages/
    ├── admin.py                ← Admin portal
    └── student.py              ← Student portal + exam engine
```

## 🚀 Local Setup

```bash
# 1. Install
pip install -r requirements.txt

# 2. Configure secrets
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Fill in your Supabase URL and anon key

# 3. Run
streamlit run app.py
```

## ☁️ Supabase Setup

1. Create project at [supabase.com](https://supabase.com)
2. SQL Editor → paste `supabase_schema.sql` → Run
3. Authentication → Providers → Google → Enable
4. Add your Streamlit app URL to Authentication → URL Configuration

## ☁️ Deploy to Streamlit Cloud

1. Push this repo to GitHub (secrets.toml is gitignored — safe to push)
2. [share.streamlit.io](https://share.streamlit.io) → New app → select repo → `app.py`
3. Settings → Secrets → paste your secrets.toml content

## 📊 Excel Question Format

Row 1 = headers, columns A → G:

| A: Question No | B: Question | C: Option A | D: Option B | E: Option C | F: Option D | G: Correct Option |
|---|---|---|---|---|---|---|
| 1 | Sample question | Option A | Option B | Option C | Option D | A |

## ⚙️ Scoring (NEET)
- ✅ Correct: **+4**  ❌ Wrong: **−1**  ⬜ Skipped: **0**

## 🔐 Admin Access
Only `thebongscience@gmail.com` gets admin role — set automatically by Supabase trigger on first login.
