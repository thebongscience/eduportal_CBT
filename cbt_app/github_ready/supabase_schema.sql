-- ============================================================
--  CBT EXAM PORTAL  –  Supabase Schema  (v2 – image support)
--  Paste this into: Supabase Dashboard → SQL Editor → Run
-- ============================================================

-- ── 1. USER PROFILES ────────────────────────────────────────
create table if not exists public.profiles (
  id          uuid primary key references auth.users(id) on delete cascade,
  email       text unique not null,
  full_name   text,
  avatar_url  text,
  role        text not null default 'student',
  class       text,
  status      text not null default 'pending',
  created_at  timestamptz default now()
);

-- ── 2. SUBJECTS ──────────────────────────────────────────────
create table if not exists public.subjects (
  id              uuid primary key default gen_random_uuid(),
  name            text not null,
  class           text not null,
  has_image_qs    boolean default false,   -- flag: this subject uses image questions
  created_by      uuid references public.profiles(id),
  created_at      timestamptz default now()
);

-- ── 3. EXAMS ─────────────────────────────────────────────────
create table if not exists public.exams (
  id              uuid primary key default gen_random_uuid(),
  subject_id      uuid references public.subjects(id) on delete cascade,
  title           text not null,
  total_questions int not null default 100,
  duration_mins   int not null default 180,
  is_active       boolean default true,
  created_by      uuid references public.profiles(id),
  created_at      timestamptz default now()
);

-- ── 4. QUESTIONS  ────────────────────────────────────────────
--   question_type: 'text' | 'image_question' | 'image_options'
--
--   text          → standard text question, text options  (Excel upload)
--   image_question→ question has an image, text options   (image upload separately)
--   image_options → question is text, options have images (image upload separately)
--
--   image_url: Supabase Storage public URL of the question image
--   option_X_image_url: Supabase Storage public URL for each option image
-- ─────────────────────────────────────────────────────────────
create table if not exists public.questions (
  id                  uuid primary key default gen_random_uuid(),
  exam_id             uuid references public.exams(id) on delete cascade,
  q_number            int not null,
  question_type       text not null default 'text',   -- 'text' | 'image_question' | 'image_options'
  question            text not null,
  image_url           text,             -- URL if question has an image
  option_a            text not null,
  option_b            text not null,
  option_c            text not null,
  option_d            text not null,
  option_a_image_url  text,             -- URL if option A is/has an image
  option_b_image_url  text,
  option_c_image_url  text,
  option_d_image_url  text,
  answer              text not null,    -- 'A' | 'B' | 'C' | 'D'
  created_at          timestamptz default now()
);

-- ── 5. EXAM ATTEMPTS ─────────────────────────────────────────
create table if not exists public.attempts (
  id              uuid primary key default gen_random_uuid(),
  student_id      uuid references public.profiles(id),
  exam_id         uuid references public.exams(id),
  question_ids    uuid[] not null,
  started_at      timestamptz default now(),
  submitted_at    timestamptz,
  time_taken_secs int,
  score           int,
  total           int,
  status          text default 'in_progress'
);

-- ── 6. RESPONSES ─────────────────────────────────────────────
create table if not exists public.responses (
  id          uuid primary key default gen_random_uuid(),
  attempt_id  uuid references public.attempts(id) on delete cascade,
  question_id uuid references public.questions(id),
  answer      text,
  is_marked   boolean default false,
  is_correct  boolean,
  created_at  timestamptz default now()
);

-- ── 7. ACCESS REQUESTS ───────────────────────────────────────
create table if not exists public.access_requests (
  id          uuid primary key default gen_random_uuid(),
  email       text not null,
  full_name   text,
  class       text,
  message     text,
  status      text default 'pending',
  created_at  timestamptz default now()
);

-- ============================================================
--  ROW LEVEL SECURITY
-- ============================================================
alter table public.profiles        enable row level security;
alter table public.subjects        enable row level security;
alter table public.exams           enable row level security;
alter table public.questions       enable row level security;
alter table public.attempts        enable row level security;
alter table public.responses       enable row level security;
alter table public.access_requests enable row level security;

create or replace function is_admin()
returns boolean language sql security definer as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

-- PROFILES
create policy "Users read own profile"    on public.profiles for select using (auth.uid() = id);
create policy "Admin reads all profiles"  on public.profiles for select using (is_admin());
create policy "Admin updates profiles"    on public.profiles for update using (is_admin());
create policy "Insert own profile"        on public.profiles for insert with check (auth.uid() = id);

-- SUBJECTS
create policy "Approved students read subjects" on public.subjects for select
  using (exists (select 1 from public.profiles where id = auth.uid() and status = 'approved'));
create policy "Admin manages subjects" on public.subjects for all using (is_admin());

-- EXAMS
create policy "Approved students read exams" on public.exams for select
  using (exists (select 1 from public.profiles where id = auth.uid() and status = 'approved'));
create policy "Admin manages exams" on public.exams for all using (is_admin());

-- QUESTIONS
create policy "Approved students read questions" on public.questions for select
  using (exists (select 1 from public.profiles where id = auth.uid() and status = 'approved'));
create policy "Admin manages questions" on public.questions for all using (is_admin());

-- ATTEMPTS
create policy "Students manage own attempts" on public.attempts for all using (auth.uid() = student_id);
create policy "Admin reads all attempts"     on public.attempts for select using (is_admin());

-- RESPONSES
create policy "Students manage own responses" on public.responses for all
  using (exists (select 1 from public.attempts where id = attempt_id and student_id = auth.uid()));
create policy "Admin reads all responses" on public.responses for select using (is_admin());

-- ACCESS REQUESTS
create policy "Anyone can request access" on public.access_requests for insert with check (true);
create policy "Admin manages requests"    on public.access_requests for all using (is_admin());

-- ============================================================
--  SUPABASE STORAGE  (run separately or via Dashboard)
-- ============================================================
-- 1. Go to Supabase Dashboard → Storage → New Bucket
-- 2. Create bucket named: "question-images"
-- 3. Make it PUBLIC (toggle on)
-- 4. Optionally set file size limit: 5MB, allowed types: image/png, image/jpeg, image/gif
--
-- Storage RLS policies (paste these too):
-- insert into storage.buckets (id, name, public) values ('question-images', 'question-images', true);
--
-- create policy "Admin uploads images" on storage.objects for insert
--   with check (bucket_id = 'question-images' and is_admin());
--
-- create policy "Anyone reads images" on storage.objects for select
--   using (bucket_id = 'question-images');

-- ============================================================
--  TRIGGER: auto-create profile on signup
-- ============================================================
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url, role, status)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'avatar_url',
    case when new.email = 'thebongscience@gmail.com' then 'admin' else 'student' end,
    case when new.email = 'thebongscience@gmail.com' then 'approved' else 'pending' end
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
