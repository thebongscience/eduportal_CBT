# CBT Exam Portal — Setup Guide

## Project Structure
```
cbt_app/
├── app.py                    ← Main login page (entry point)
├── db.py                     ← Supabase client + all DB functions
├── requirements.txt
├── supabase_schema.sql       ← Run this in Supabase SQL editor
├── .streamlit/
│   ├── config.toml           ← Streamlit theme
│   └── secrets.toml          ← YOUR credentials go here (never commit)
└── pages/
    ├── admin.py              ← Admin portal
    └── student.py            ← Student exam portal
```

---

## STEP 1 — Create Supabase Project

1. Go to https://supabase.com → New Project
2. Note your **Project URL** and **anon key** (Settings → API)
3. Go to **SQL Editor** → paste contents of `supabase_schema.sql` → Run

---

## STEP 2 — Enable Google OAuth in Supabase

1. Supabase Dashboard → Authentication → Providers → Google → Enable
2. Go to https://console.cloud.google.com
   - Create a project → APIs & Services → Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Authorized redirect URIs: `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback`
3. Copy Client ID and Secret back into Supabase Google provider settings
4. In Supabase → Authentication → URL Configuration:
   - Site URL: `http://localhost:8501`
   - Redirect URLs: `http://localhost:8501`

---

## STEP 3 — Configure Secrets

Edit `.streamlit/secrets.toml`:
```toml
[supabase]
url = "https://YOUR_PROJECT_REF.supabase.co"
key = "YOUR_ANON_KEY_HERE"

[auth]
admin_email = "thebongscience@gmail.com"
redirect_url = "http://localhost:8501"
```

---

## STEP 4 — Install & Run Locally

```bash
cd cbt_app
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

---

## STEP 5 — Test Flow

### Admin flow:
1. Open login page → click Admin tab → Sign in with Google (thebongscience@gmail.com)
2. Goes to Admin Portal → create a Subject → create an Exam → upload questions Excel

### Excel format (A to G columns, no header row or use exact header names):
| A: question_number | B: question | C: option_a | D: option_b | E: option_c | F: option_d | G: answer |
```
1, What is NaCl?, Sodium Chloride, Sugar, Water, Salt, A
2, ...
```

### Student flow:
1. Login page → Student tab → fill access request form
2. Admin approves from Admin Portal → Access Requests tab
3. Student signs in with Google → sees available exams → takes exam

---

## STEP 6 — Deploy to Streamlit Cloud

1. Push to GitHub (make sure `.streamlit/secrets.toml` is in `.gitignore`)
2. Go to https://share.streamlit.io → New app → select repo → `app.py`
3. Add secrets in Streamlit Cloud dashboard (paste your secrets.toml content)
4. Update Supabase redirect URLs to your Streamlit Cloud URL

---

## Excel Question Upload Format

The admin uploads an Excel file with **7 columns (A to G)**:

| Column | Field | Example |
|--------|-------|---------|
| A | question_number | 1 |
| B | question | The heating of phenyl-methyl ethers with HI produces: |
| C | option_a | Ethyl chloride |
| D | option_b | Iodobenzene |
| E | option_c | Phenol |
| F | option_d | Benzene |
| G | answer | C |

- Upload as many as 250+ questions per exam
- Admin controls how many questions are served per test (e.g. randomly pick 100 from 250)

---

## Scoring (NEET-style)
- Correct answer: **+4 marks**
- Wrong answer: **-1 mark**
- Not attempted: **0 marks**
