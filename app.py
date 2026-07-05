import math
import re
import os
import sys

import streamlit as st
from streamlit.runtime.scriptrunner import get_script_run_ctx

from optimizer import (
    clean_notes,
    format_course,
    major_restriction_applies,
    residency_requirement,
    section_blocks_to_result,
    sort_minor_results,
    summarize_minor,
)
from scraper import (
    _get_requirements_from_minor_page,
    get_majors_list,
    get_minor_list,
)

st.set_page_config(
    page_title="Purdue University Minor Optimizer",
    page_icon="🎓",
    menu_items={
        "About": (
            "**Purdue University Minor Optimizer**  \n"
            "v0.2.0  \n\n"
            "**Arnav Sivakumar**  \n"
            "CS Student @ Purdue University  \n\n"
            "Made this app to explore optimizing overlapping minors and for fun.  \n\n"
            "Website: https://arnavsivakumar.com  \n"
            "LinkedIn: https://www.linkedin.com/in/arnavsivakumar/  \n"
            "Open Source: https://github.com/arnavsiva/Purdue-University-Minor-Optimizer  \n"
        )
    },
)


def main():
    # Reset optimization flag
    def reset_optimize():
        st.session_state.optimize = False

    def set_optimize():
        st.session_state.optimize = True

    def delete_course(idx):
        st.session_state.courses.pop(idx)
        st.session_state.optimize = False

    def clear_all():
        st.session_state.courses = []
        # reset optimization flag and inputs
        st.session_state.optimize = False
        # reset semester and major selections
        st.session_state.current_sem = 1
        st.session_state.major = "None"
        # clear input fields
        st.session_state.clear_input = False
        st.session_state.clear_external = False

    st.title("Purdue Minor Recommender v0.1.0")
    st.write(
        "Enter your completed courses and current semester to find the best minors you can pursue based on overlap and remaining requirements.\n\n"
        "This app is an open source project by Arnav Sivakumar, a CS student at Purdue University. It uses the [Purdue Course Catalog](https://catalog.purdue.edu/) to scrape minor requirements and compute recommendations based on your completed coursework.\n\n"
        "**Important:** This app has been tested with my courses and credits, but with over 100 Purdue minors, not everything has been fully tested. Please check the official Purdue minor page for each recommendation to ensure accuracy. If you find any issues or have suggestions, please report them on the [GitHub repository](https://github.com/arnavsiva/Purdue-University-Minor-Optimizer)."
    )

    # Sidebar - user information input and course management
    st.sidebar.header("Your Information")
    # select current major (used only for explicit catalog restrictions)
    majors = get_majors_list()
    major_options = ["None"] + majors
    if "major" not in st.session_state:
        st.session_state.major = "None"
    st.sidebar.selectbox(
        "Current major (optional)",
        major_options,
        index=0,
        key="major",
        on_change=reset_optimize,
    )
    semester = st.sidebar.selectbox(
        "Current semester",
        options=list(range(1, 9)),
        index=0,
        key="current_sem",
        on_change=reset_optimize,
    )
    # initialize stored course list
    if "courses" not in st.session_state:
        st.session_state.courses = []
    # handle clearing the input field after adding courses
    if "clear_input" not in st.session_state:
        st.session_state.clear_input = False
    if st.session_state.clear_input:
        st.session_state.new_courses_input = ""
        st.session_state.clear_input = False
    # form to add courses in bulk
    with st.sidebar.form("add_courses_form"):
        new_input = st.text_input(
            "Type all your courses taken at Purdue (separated by commas)",
            key="new_courses_input",
        )
        add_btn = st.form_submit_button("Add Courses", on_click=reset_optimize)
    if add_btn and new_input:
        for code in [
            c.strip().upper().replace(" ", "")
            for c in new_input.split(",")
            if c.strip()
        ]:
            if code not in [c["code"] for c in st.session_state.courses]:
                # default to semester 1 until user updates
                st.session_state.courses.append({"code": code, "sem": 1})
        # clear the form input and rerun
        st.session_state.clear_input = True
        st.rerun()
    # initialize and handle clearing the external input field before widget
    if "clear_external" not in st.session_state:
        st.session_state.clear_external = False
    if st.session_state.clear_external:
        st.session_state.external_courses_input = ""
        st.session_state.clear_external = False

    # link to transfer credit info
    st.sidebar.markdown(
        "For external/test course equivalency info, see [Purdue Transfer Credit](https://admissions.purdue.edu/transfercredit/)"
    )
    # External credits input form
    with st.sidebar.form("add_external_form"):
        ext_input = st.text_input(
            "Type your external (transfer/test) courses (comma-separated)",
            key="external_courses_input",
        )
        add_ext = st.form_submit_button("Add External Credits", on_click=reset_optimize)
    if add_ext and ext_input:
        for code in [
            c.strip().upper().replace(" ", "")
            for c in ext_input.split(",")
            if c.strip()
        ]:
            existing = [c["code"] for c in st.session_state.courses]
            if code not in existing:
                st.session_state.courses.append(
                    {"code": code, "sem": None, "origin": "external"}
                )
        # schedule external input clear and rerun
        st.session_state.clear_external = True
        st.rerun()
    # Experiences: allow marking Study Abroad or International Internship
    st.sidebar.header("Experiences")
    st.sidebar.checkbox("Study Abroad", key="study_abroad", on_change=reset_optimize)
    st.sidebar.checkbox(
        "International Internship", key="intl_internship", on_change=reset_optimize
    )

    # list and manage added courses
    if st.session_state.courses:
        st.sidebar.markdown("**Your Courses:**")
        # prepare sorted indices for Purdue and External courses
        purdue_idxs = sorted(
            [
                i
                for i, c in enumerate(st.session_state.courses)
                if c.get("origin", "purdue") == "purdue"
            ],
            key=lambda i: st.session_state.courses[i]["code"],
        )
        external_idxs = sorted(
            [
                i
                for i, c in enumerate(st.session_state.courses)
                if c.get("origin") == "external"
            ],
            key=lambda i: st.session_state.courses[i]["code"],
        )
        # display Purdue courses first
        if purdue_idxs:
            st.sidebar.markdown("*Purdue Courses:*")
            for idx in purdue_idxs:
                course = st.session_state.courses[idx]
                code_fmt = re.sub(r"([A-Za-z]+)(\d+)", r"\1 \2", course["code"])
                cols = st.sidebar.columns([3, 1])
                with cols[0]:
                    sem_val = st.selectbox(
                        f"Semester taken for {code_fmt}",
                        options=list(range(1, semester + 1)),
                        key=f"sem_{idx}",
                        index=(course.get("sem", 1) - 1),
                        on_change=reset_optimize,
                    )
                    st.session_state.courses[idx]["sem"] = sem_val
                with cols[1]:
                    st.button(
                        "🗑️", key=f"del_{idx}", on_click=delete_course, args=(idx,)
                    )
        # then External courses
        if external_idxs:
            st.sidebar.markdown("*External Courses:*")
            for idx in external_idxs:
                course = st.session_state.courses[idx]
                code_fmt = re.sub(r"([A-Za-z]+)(\d+)", r"\1 \2", course["code"])
                cols = st.sidebar.columns([3, 1])
                with cols[0]:
                    st.markdown(f"**{code_fmt}** (External)")
                with cols[1]:
                    st.button(
                        "🗑️", key=f"del_{idx}", on_click=delete_course, args=(idx,)
                    )
        # button to clear all entered courses
        st.sidebar.button("🧹 Reset Inputs", on_click=clear_all)

    # build taken set from stored courses
    taken = {c["code"] for c in st.session_state.courses}
    # add spacing after input forms
    st.sidebar.write("")
    # optimization trigger
    st.sidebar.header("Optimization")
    if "optimize" not in st.session_state:
        st.session_state.optimize = False
    _ = st.sidebar.button("Find minor optimization", on_click=set_optimize)
    # require at least one course and the optimization button pressed
    if not taken:
        st.sidebar.warning("Add at least one course to proceed.")
        return
    if not st.session_state.optimize:
        st.info(
            "Click 'Find minor optimization' in the sidebar to get recommendations."
        )
        return

    st.markdown(
        """
        <style>
        .boilerplate-wrap {
            margin-top: 0.75rem;
        }
        .rank-rail {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.75rem;
            margin: 0.75rem 0 1.5rem 0;
        }
        .rank-card {
            border-radius: 18px;
            padding: 0.9rem 1rem;
            border: 1px solid rgba(255,255,255,0.08);
            background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03));
            box-shadow: 0 12px 30px rgba(0,0,0,0.18);
        }
        .rank-card.active {
            border-color: rgba(255,184,0,0.6);
            box-shadow: 0 18px 36px rgba(255,184,0,0.18);
        }
        .rank-num {
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.75;
        }
        .rank-title {
            font-size: 1rem;
            font-weight: 700;
            margin-top: 0.35rem;
        }
        .rank-sub {
            font-size: 0.88rem;
            opacity: 0.75;
            margin-top: 0.25rem;
        }
        .minor-card {
            border-radius: 28px;
            padding: 1.5rem;
            background: radial-gradient(circle at top right, rgba(255,184,0,0.16), transparent 28%),
                        linear-gradient(180deg, rgba(20,20,20,0.96), rgba(8,8,8,0.98));
            border: 1px solid rgba(255,255,255,0.08);
            box-shadow: 0 24px 60px rgba(0,0,0,0.35);
            margin: 0.5rem 0 1rem 0;
        }
        .minor-card h2 {
            margin: 0;
            color: #fff;
            font-size: 2rem;
            line-height: 1.15;
        }
        .minor-card .meta-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.85rem;
            margin-bottom: 0.8rem;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            color: #fff;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .pill.gold { background: rgba(255,184,0,0.18); color: #ffd77a; }
        .pill.green { background: rgba(90,200,120,0.18); color: #8ef0ae; }
        .pill.blue { background: rgba(90,155,255,0.18); color: #9fc3ff; }
        .progress-shell {
            width: 100%;
            height: 12px;
            border-radius: 999px;
            background: rgba(255,255,255,0.08);
            overflow: hidden;
            margin: 0.75rem 0 1rem 0;
        }
        .progress-fill {
            height: 100%;
            border-radius: 999px;
            background: linear-gradient(90deg, #ffb800, #ffd77a);
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 0.75rem;
            margin-top: 0.8rem;
            margin-bottom: 1rem;
        }
        .stat-card {
            border-radius: 18px;
            padding: 0.9rem 1rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .stat-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.65;
        }
        .stat-value {
            font-size: 1.35rem;
            font-weight: 800;
            margin-top: 0.2rem;
            color: #fff;
        }
        .section-card {
            border-radius: 18px;
            padding: 0.9rem 1rem;
            margin: 0.6rem 0;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.08);
        }
        .section-card.complete { border-color: rgba(90,200,120,0.35); }
        .section-card.partial { border-color: rgba(255,184,0,0.35); }
        .section-card.manual { border-color: rgba(120,160,255,0.35); }
        .section-title { font-weight: 700; color: #fff; }
        .section-detail { margin-top: 0.35rem; opacity: 0.88; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # proceed once optimization triggered
    with st.spinner("Loading minor requirements..."):
        status = st.empty()
        minors_data = []
        for name, link in get_minor_list():
            status.text(f"Loading requirements for {name}...")
            try:
                sections, notes, restriction_text = _get_requirements_from_minor_page(link)
            except Exception:
                sections, notes, restriction_text = [], [], ""
            minors_data.append(
                {
                    "name": name,
                    "link": link,
                    "sections": sections,
                    "notes": notes,
                    "restriction_text": restriction_text,
                }
            )
        status.empty()

    with st.spinner("Computing top recommendations..."):
        status = st.empty()
        results = []
        skipped_minors = []
        for minor in minors_data:
            status.text(f"Checking {minor['name']} minor...")
            if major_restriction_applies(st.session_state.get("major"), minor.get("restriction_text", "")):
                skipped_minors.append(minor["name"])
                continue

            summary = summarize_minor(minor, taken, st.session_state.get("major"))
            if summary is not None:
                results.append(summary)
        status.empty()

    if skipped_minors:
        st.info(
            "Some minors were excluded because the selected major matches an explicit catalog restriction: "
            + ", ".join(sorted(skipped_minors))
        )

    results = sort_minor_results(results)

    if not results:
        st.info("No minors found with requirements.")
        return

    st.subheader("Recommended Minors")
    st.caption(f"{len(results)} minors match your completed coursework. Rank 1 is the closest match.")

    preview_count = min(3, len(results))
    preview_cols = st.columns(preview_count)
    for idx, (col, result) in enumerate(zip(preview_cols, results[:preview_count]), start=1):
        with col:
            active_class = " active" if idx == 1 else ""
            st.markdown(
                f"""
                <div class="rank-card{active_class}">
                    <div class="rank-num">Rank {idx}</div>
                    <div class="rank-title">{result['name']}</div>
                    <div class="rank-sub">{result['percent']:.1f}% complete</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    selected_rank = st.slider(
        "Browse ranked minors",
        min_value=1,
        max_value=len(results),
        value=1,
        help="Rank 1 is the closest completion match.",
    )
    selected = results[selected_rank - 1]
    notes = selected.get("notes", [])
    residency = residency_requirement(selected["total"], notes)

    st.markdown(
        f"""
        <div class="minor-card">
            <div class="meta-row">
                <span class="pill gold">Rank #{selected_rank}</span>
                <span class="pill green">{selected['percent']:.1f}% complete</span>
                <span class="pill blue">{selected['completed']} of {selected['total']} courses</span>
            </div>
            <h2>{selected['name']}</h2>
            <div class="progress-shell"><div class="progress-fill" style="width:{selected['percent']:.1f}%"></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Progress", f"{selected['percent']:.1f}%")
    with c2:
        st.metric("Completed", f"{selected['completed']} / {selected['total']}")
    with c3:
        st.metric("Taken courses", len(selected['taken_codes']))

    st.markdown(f"[View catalog page]({selected['link']})")

    if residency:
        req_pcnt, req_courses, allowed_ext = residency
        st.info(
            f"Residency requirement: at least {req_courses}/{selected['total']} courses at Purdue ({req_pcnt}%), up to {allowed_ext} external."
        )

    c_left, c_right = st.columns([1.05, 0.95])
    with c_left:
        st.markdown("**Courses already taken**")
        if selected["taken_codes"]:
            chips = " ".join(
                f'<span class="pill">{format_course(code)}</span>' for code in selected["taken_codes"]
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.caption("No completed courses overlap this minor yet.")

    with c_right:
        st.markdown("**What is left**")
        st.caption("Open any section below for a compact breakdown.")

    st.markdown("**Requirement breakdown**")
    for section_result in selected["section_results"]:
        if section_result["kind"] == "manual":
            status_label = "Manual"
            status_class = "manual"
        else:
            status_label = f"{section_result['completed']} / {section_result['total']}"
            status_class = "complete" if section_result["completed"] >= section_result["total"] else "partial"

        st.markdown(
            f"""
            <div class="section-card {status_class}">
                <div class="section-title">{section_result['title']}</div>
                <div class="section-detail">Status: {status_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.expander(section_result["title"], expanded=section_result["completed"] < section_result["total"]):
            if section_result["kind"] == "manual":
                st.write(section_result.get("description", ""))
            elif section_result["kind"] == "pool":
                remaining = section_result.get("remaining_options", [])
                if remaining:
                    st.write("Options still available:")
                    st.markdown(
                        " ".join(
                            f'<span class="pill">{format_course(code)}</span>' for code in remaining
                        ),
                        unsafe_allow_html=True,
                    )
                if section_result.get("children"):
                    st.write("Grouped options:")
                    for child in section_result["children"]:
                        child_codes = child.get("codes", []) or child.get("options", [])
                        if child_codes:
                            st.write(f"- {child.get('title', 'Option')}: {', '.join(format_course(code) for code in child_codes)}")
            else:
                pending_groups = section_result.get("pending_groups", [])
                if pending_groups:
                    for group in pending_groups:
                        options = group.get("options", [])
                        missing = group.get("missing", [])
                        if options:
                            st.write(f"- {', '.join(format_course(code) for code in options)}")
                        elif missing:
                            st.write(f"- {', '.join(format_course(code) for code in missing)}")
                else:
                    st.write("All grouped options are satisfied.")

    if notes:
        with st.expander("Notes", expanded=False):
            for cn in clean_notes(notes):
                st.write(f"- {cn}")


if __name__ == "__main__":
    if get_script_run_ctx() is None:
        os.execvp("streamlit", ["streamlit", "run", sys.argv[0], *sys.argv[1:]])
    main()
