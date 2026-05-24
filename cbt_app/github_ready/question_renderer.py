"""
question_renderer.py
──────────────────────────────────────────────────────────────
Call render_question(q, current_answer, on_select_callback)
inside the student exam page to display any question type.

Handles:
  - text          → plain text question + text options
  - image_question→ text + image above options
  - image_options → text question + 2×2 image grid options
"""
import streamlit as st


def render_question(q: dict, current_answer: str | None, on_answer_change):
    """
    q               : question dict from Supabase
    current_answer  : 'A'|'B'|'C'|'D' or None
    on_answer_change: callable(letter) called when student selects an option
    """
    q_type = q.get("question_type", "text")

    # ── Question text (always shown) ─────────────────────────
    st.markdown(
        f"<div style='padding:16px;background:white;border:1px solid #ddd;border-radius:8px;"
        f"margin-bottom:12px;font-size:15px;line-height:1.8;'>{q['question']}</div>",
        unsafe_allow_html=True
    )

    # ── Optional question image (Type 1) ─────────────────────
    if q_type == "image_question" and q.get("image_url"):
        st.image(
            q["image_url"],
            use_column_width=True,
            caption="Refer to the figure above"
        )
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Options ──────────────────────────────────────────────
    if q_type == "image_options":
        _render_image_options(q, current_answer, on_answer_change)
    else:
        _render_text_options(q, current_answer, on_answer_change)


def _render_text_options(q, current_answer, on_answer_change):
    """Standard A/B/C/D text options — 2-column layout."""
    options = [
        ("A", q.get("option_a", "")),
        ("B", q.get("option_b", "")),
        ("C", q.get("option_c", "")),
        ("D", q.get("option_d", "")),
    ]
    left, right = st.columns(2)
    for i, (letter, text) in enumerate(options):
        col = left if i % 2 == 0 else right
        is_sel = current_answer == letter
        border = "1.5px solid #1a73e8" if is_sel else "1.5px solid #ddd"
        bg     = "#e8f0fe" if is_sel else "#fafafa"
        with col:
            st.markdown(
                f"<div style='border:{border};background:{bg};padding:12px 16px;"
                f"border-radius:8px;margin:6px 0;font-size:15px;'>"
                f"<b style='color:#555;margin-right:8px;'>({letter})</b>{text}</div>",
                unsafe_allow_html=True
            )
            if st.button(f"Select ({letter})", key=f"opt_{q['id']}_{letter}", use_container_width=True):
                on_answer_change(letter)


def _render_image_options(q, current_answer, on_answer_change):
    """2×2 grid of image options — each image is a clickable card."""
    options = [
        ("A", q.get("option_a", "A"), q.get("option_a_image_url")),
        ("B", q.get("option_b", "B"), q.get("option_b_image_url")),
        ("C", q.get("option_c", "C"), q.get("option_c_image_url")),
        ("D", q.get("option_d", "D"), q.get("option_d_image_url")),
    ]
    row1 = st.columns(2)
    row2 = st.columns(2)
    grid = [row1[0], row1[1], row2[0], row2[1]]

    for i, (letter, label, img_url) in enumerate(options):
        is_sel = current_answer == letter
        border = "2px solid #1a73e8" if is_sel else "1.5px solid #ddd"
        bg     = "#e8f0fe" if is_sel else "white"
        with grid[i]:
            st.markdown(
                f"<div style='border:{border};background:{bg};border-radius:10px;"
                f"padding:10px;text-align:center;margin-bottom:4px;'>",
                unsafe_allow_html=True
            )
            if img_url:
                st.image(img_url, use_column_width=True)
            else:
                st.markdown(
                    f"<div style='height:120px;display:flex;align-items:center;"
                    f"justify-content:center;color:#aaa;font-size:13px;'>No image</div>",
                    unsafe_allow_html=True
                )
            st.markdown(
                f"<div style='font-size:12px;color:#555;margin-top:4px;'>({letter}) {label}</div></div>",
                unsafe_allow_html=True
            )
            if st.button(
                f"✓ Select ({letter})" if is_sel else f"Select ({letter})",
                key=f"img_opt_{q['id']}_{letter}",
                use_container_width=True,
                type="primary" if is_sel else "secondary"
            ):
                on_answer_change(letter)
