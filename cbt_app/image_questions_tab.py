"""
image_questions_tab.py
─────────────────────────────────────────────────────────────────
Paste this as a function and call it inside the Questions tab in admin.py.
Handles TWO image-question types:

  TYPE 1 — image_question:
    The question text + an image are shown together.
    Options A/B/C/D are plain text.
    Used for: anatomy diagrams, chemical structures, graphs,
              geography maps, physics diagrams.

  TYPE 2 — image_options:
    Question is plain text.
    Options are images (e.g. "Which of these is the correct structure?")
    Used for: molecular structures, circuit diagrams as options.
─────────────────────────────────────────────────────────────────
USAGE in admin.py questions tab:

    from image_questions_tab import render_image_question_uploader
    render_image_question_uploader(exam_id, user_id)
"""
import streamlit as st
import io
from db_v2 import (
    upload_question_image,
    insert_image_question,
    get_questions,
    delete_questions_for_exam
)


def render_image_question_uploader(exam_id: str, user_id: str):
    st.markdown("---")
    st.markdown("### 🖼️ Image-Based Questions")
    st.info("""
    **Two types of image questions supported:**

    | Type | When to use | Examples |
    |------|------------|---------|
    | **Image in Question** | Show a diagram/figure with the question text | Anatomy diagrams, chemical structures, graphs, maps, ECG strips |
    | **Images as Options** | Question is text, students pick the correct image | Identify correct molecular structure, match the graph |
    """)

    q_type = st.radio(
        "Select image question type:",
        ["Image in Question (text options)", "Images as Options (image options)"],
        horizontal=True,
        key="img_q_type"
    )

    # ── Get next question number ──────────────────────────────
    existing = get_questions(exam_id)
    next_num = max((q["q_number"] for q in existing), default=0) + 1

    st.markdown(f"*Next question will be Q{next_num}*")

    # ─────────────────────────────────────────────────────────
    if q_type == "Image in Question (text options)":
        _type1_form(exam_id, next_num)
    else:
        _type2_form(exam_id, next_num)

    # ── Preview existing image questions ─────────────────────
    image_qs = [q for q in existing if q.get("question_type") in ("image_question", "image_options")]
    if image_qs:
        st.markdown(f"#### Existing image questions ({len(image_qs)})")
        for q in image_qs:
            with st.expander(f"Q{q['q_number']}: {q['question'][:60]}... [{q['question_type']}]"):
                if q.get("image_url"):
                    st.image(q["image_url"], width=400, caption="Question image")
                cols = st.columns(4)
                for i, (letter, col) in enumerate(zip(["A","B","C","D"], cols)):
                    url_key = f"option_{letter.lower()}_image_url"
                    with col:
                        if q.get(url_key):
                            st.image(q[url_key], caption=f"Option {letter}", use_column_width=True)
                        else:
                            opt_key = f"option_{letter.lower()}"
                            st.write(f"**({letter})** {q.get(opt_key,'')}")
                st.write(f"✅ Correct Answer: **{q['answer']}**")


def _type1_form(exam_id: str, next_num: int):
    """Type 1: Image shown with the question, text options."""
    st.markdown("#### Type 1 — Question has an image")
    st.caption("Upload one image (diagram/figure) that appears alongside the question text.")

    with st.form(f"img_q_form_{next_num}"):
        q_num   = st.number_input("Question number", min_value=1, value=next_num)
        q_text  = st.text_area("Question text", placeholder="The diagram shows which type of cell division?", height=80)
        q_image = st.file_uploader("Question image (PNG/JPG)", type=["png","jpg","jpeg","gif","webp"])

        st.markdown("**Options (text):**")
        c1, c2 = st.columns(2)
        with c1:
            opt_a = st.text_input("Option A")
            opt_c = st.text_input("Option C")
        with c2:
            opt_b = st.text_input("Option B")
            opt_d = st.text_input("Option D")

        answer = st.selectbox("Correct Answer", ["A","B","C","D"])

        submitted = st.form_submit_button("➕ Add Image Question", use_container_width=True)
        if submitted:
            if not q_text:
                st.error("Question text is required.")
            elif not q_image:
                st.error("Please upload an image.")
            elif not all([opt_a, opt_b, opt_c, opt_d]):
                st.error("All four options are required.")
            else:
                with st.spinner("Uploading image..."):
                    img_bytes = q_image.read()
                    filename  = f"q{q_num}_{q_image.name}"
                    img_url   = upload_question_image(img_bytes, filename, exam_id)
                insert_image_question(exam_id, {
                    "q_number":      q_num,
                    "question_type": "image_question",
                    "question":      q_text,
                    "image_url":     img_url,
                    "option_a":      opt_a,
                    "option_b":      opt_b,
                    "option_c":      opt_c,
                    "option_d":      opt_d,
                    "answer":        answer,
                })
                st.success(f"✅ Q{q_num} added with image!")
                st.rerun()


def _type2_form(exam_id: str, next_num: int):
    """Type 2: Text question, image options."""
    st.markdown("#### Type 2 — Options are images")
    st.caption("Upload one image per option. The question is plain text.")

    with st.form(f"img_opts_form_{next_num}"):
        q_num  = st.number_input("Question number", min_value=1, value=next_num)
        q_text = st.text_area("Question text", placeholder="Which of the following correctly shows the structure of benzene?", height=80)

        st.markdown("**Upload one image per option:**")
        c1, c2 = st.columns(2)
        with c1:
            img_a = st.file_uploader("Option A image", type=["png","jpg","jpeg","gif","webp"], key="opt_img_a")
            img_c = st.file_uploader("Option C image", type=["png","jpg","jpeg","gif","webp"], key="opt_img_c")
        with c2:
            img_b = st.file_uploader("Option B image", type=["png","jpg","jpeg","gif","webp"], key="opt_img_b")
            img_d = st.file_uploader("Option D image", type=["png","jpg","jpeg","gif","webp"], key="opt_img_d")

        st.markdown("**Option labels (optional short text under each image):**")
        lc1, lc2 = st.columns(2)
        with lc1:
            lbl_a = st.text_input("Label A", value="Option A")
            lbl_c = st.text_input("Label C", value="Option C")
        with lc2:
            lbl_b = st.text_input("Label B", value="Option B")
            lbl_d = st.text_input("Label D", value="Option D")

        answer = st.selectbox("Correct Answer", ["A","B","C","D"])

        submitted = st.form_submit_button("➕ Add Image-Option Question", use_container_width=True)
        if submitted:
            if not q_text:
                st.error("Question text is required.")
            elif not all([img_a, img_b, img_c, img_d]):
                st.error("Please upload images for all four options.")
            else:
                with st.spinner("Uploading images..."):
                    url_a = upload_question_image(img_a.read(), f"q{q_num}_optA_{img_a.name}", exam_id)
                    url_b = upload_question_image(img_b.read(), f"q{q_num}_optB_{img_b.name}", exam_id)
                    url_c = upload_question_image(img_c.read(), f"q{q_num}_optC_{img_c.name}", exam_id)
                    url_d = upload_question_image(img_d.read(), f"q{q_num}_optD_{img_d.name}", exam_id)
                insert_image_question(exam_id, {
                    "q_number":           q_num,
                    "question_type":      "image_options",
                    "question":           q_text,
                    "option_a":           lbl_a,
                    "option_b":           lbl_b,
                    "option_c":           lbl_c,
                    "option_d":           lbl_d,
                    "option_a_image_url": url_a,
                    "option_b_image_url": url_b,
                    "option_c_image_url": url_c,
                    "option_d_image_url": url_d,
                    "answer":             answer,
                })
                st.success(f"✅ Q{q_num} added with image options!")
                st.rerun()
