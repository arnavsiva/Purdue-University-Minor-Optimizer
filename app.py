import re
from scraper import (
    get_minor_list,
    _get_requirements_from_minor_page,
)
import streamlit as st

st.set_page_config(
    page_title="Purdue University Minor Optimizer",
    page_icon="🎓",
    menu_items={
        "About": \
            "**Arnav Sivakumar**  \n"
            "CS Student @ Purdue University  \n\n"
            "Made this app to explore optimizing overlapping minors and for fun.  \n\n"
            "Website: https://arnavsivakumar.com  \n"
            "LinkedIn: https://www.linkedin.com/in/arnavsivakumar/  \n"
    }
)


def assign_remaining_courses(remaining, current_semester, per_semester=4):
    """
    Assign remaining courses into future semesters in chunks of size per_semester.
    Returns a dict mapping semester number to list of courses.
    """
    schedule = {}
    sem = current_semester + 1
    for i in range(0, len(remaining), per_semester):
        chunk = remaining[i:i+per_semester]
        schedule[f"Semester {sem}"] = chunk
        sem += 1
    return schedule


def main():
    # callbacks to manage optimization flag, deletion, and clearing all courses
    def reset_optimize():
        st.session_state.optimize = False
    def set_optimize():
        st.session_state.optimize = True
    def delete_course(idx):
        st.session_state.courses.pop(idx)
        st.session_state.optimize = False
    def clear_all():
        st.session_state.courses = []
        st.session_state.optimize = False

    st.title("Purdue Minor Recommender")
    st.write("Enter your completed courses and current semester to find the best minors you can pursue based on overlap and remaining requirements.")

    # Sidebar — user information input and course management
    st.sidebar.header("Your Information")
    semester = st.sidebar.selectbox(
        "Current semester for scheduling remaining courses",
        options=list(range(1, 9)),
        index=0,
        key="current_sem",
        on_change=reset_optimize
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
            "Type all your courses (separated by commas)", key="new_courses_input"
        )
        add_btn = st.form_submit_button("Add Courses", on_click=reset_optimize)
    if add_btn and new_input:
        for code in [c.strip().upper().replace(" ", "") for c in new_input.split(",") if c.strip()]:
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
    st.sidebar.markdown("For external/test course equivalency info, see [Purdue Transfer Credit](https://admissions.purdue.edu/transfercredit/)")
    # External credits input form
    with st.sidebar.form("add_external_form"):
        ext_input = st.text_input(
            "Type your external (transfer/test) courses (comma-separated)",
            key="external_courses_input"
        )
        add_ext = st.form_submit_button("Add External Credits", on_click=reset_optimize)
    if add_ext and ext_input:
        for code in [c.strip().upper().replace(" ", "") for c in ext_input.split(",") if c.strip()]:
            existing = [c["code"] for c in st.session_state.courses]
            if code not in existing:
                st.session_state.courses.append({"code": code, "sem": None, "origin": "external"})
        # schedule external input clear and rerun
        st.session_state.clear_external = True
        st.rerun()

    # add spacing after input forms
    st.sidebar.write("")

    # list and manage added courses
    if st.session_state.courses:
        st.sidebar.markdown("**Your Courses:**")
        for idx, course in enumerate(st.session_state.courses):
            code = course["code"]
            origin = course.get("origin", "purdue")
            cols = st.sidebar.columns([3, 1])
            with cols[0]:
                # format code
                code_fmt = re.sub(r'([A-Za-z]+)(\d+)', r'\1 \2', code)
                if origin == "purdue":
                    sem_val = st.selectbox(
                        f"Semester taken for {code_fmt} (Purdue)",
                        options=list(range(1, semester + 1)),
                        key=f"sem_{idx}",
                        index=(course.get("sem",1) - 1),
                        on_change=reset_optimize
                    )
                    st.session_state.courses[idx]["sem"] = sem_val
                else:
                    st.markdown(f"**{code_fmt}** (External)")
            with cols[1]:
                st.button(
                    "🗑️",
                    key=f"del_{idx}",
                    on_click=delete_course,
                    args=(idx,)
                )
        # button to clear all entered courses
        st.sidebar.button("🧹 Clear All Courses", on_click=clear_all)

    # build taken set from stored courses
    taken = {c["code"] for c in st.session_state.courses}
    # add spacing before optimization section
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
        st.info("Click 'Find minor optimization' in the sidebar to get recommendations.")
        return

    # proceed once optimization triggered
    with st.spinner("Loading minor requirements..."):
        status = st.empty()
        minors_data = []
        for name, link in get_minor_list():
            status.text(f"Loading requirements for {name}...")
            try:
                sections = _get_requirements_from_minor_page(link)
            except Exception:
                sections = {}
            minors_data.append({"name": name, "link": link, "sections": sections})
        status.empty()

    # compute recommendations
    with st.spinner("Computing top recommendations..."):
        status = st.empty()
        results = []
        for minor in minors_data:
            name = minor["name"]
            link = minor["link"]
            status.text(f"Checking {name} minor...")
            sections = minor["sections"]
            # calculate per-section requirements
            # flatten codes (including nested OR groups) into a single list
            raw_codes = []
            for codes in sections.values():
                if isinstance(codes, list) and codes and isinstance(codes[0], list):
                    for group in codes:
                        raw_codes.extend(group)
                else:
                    raw_codes.extend(codes)
            # find taken codes intersecting required set
            taken_codes = sorted(set(raw_codes) & taken)
            if not taken_codes:
                continue
            total = len(raw_codes)
            completed = len(taken_codes)
            percent = (completed / total) * 100 if total else 0
            # compute pending courses per section, disallow reusing chosen courses for multiple choose-one sections
            available_taken = set(taken_codes)
            pending_sections = {}
            for sec, codes in sections.items():
                lower = sec.lower()
                codes_set = set(codes)
                if "choose" in lower:
                    # parse how many courses to select
                    # try numeric e.g. 'choose 2'
                    m = re.search(r'choose\s+(\d+)', lower)
                    if m:
                        req = int(m.group(1))
                    else:
                        # try word numbers e.g. 'choose two'
                        m2 = re.search(r'choose\s+(one|two|three|four|five)', lower)
                        word_map = {'one':1,'two':2,'three':3,'four':4,'five':5}
                        req = word_map.get(m2.group(1), 1) if m2 else None
                    if req is None:
                        # fallback: use credits in parentheses / 3
                        m3 = re.search(r'\((\d+)\s+credits', sec, re.IGNORECASE)
                        credits = int(m3.group(1)) if m3 else 3
                        req = max(1, credits // 3)
                    chosen = available_taken & codes_set
                    if len(chosen) >= req:
                        # section fulfilled: consume chosen courses
                        for sel in list(chosen)[:req]:
                            available_taken.remove(sel)
                        pending_sections[sec] = []
                    else:
                        # still need to pick courses: show only untaken options
                        pending_sections[sec] = [c for c in codes if c not in taken]
                else:
                    # standard section: pending are those not taken
                    pending_sections[sec] = [c for c in codes if c not in taken]
            results.append({
                "name": name,
                "link": link,
                "taken_codes": taken_codes,
                "pending_sections": pending_sections,
                "sections": sections,
                "total": total,
                "completed": completed,
                "percent": percent,
            })
        status.empty()

    # sort by number of courses completed desc
    results = sorted(results, key=lambda x: x["percent"], reverse=True)

    if not results:
        st.info("No minors found with requirements.")
        return

    st.subheader("Recommended Minors")
    st.write(f"{len(results)} minors match your completed coursework:")

    for r in results:
        st.markdown(f"### {r['name']}")
        st.markdown(f"[View catalog page]({r['link']})")
        st.write(f"Progress: {r['completed']} / {r['total']} courses completed ({r['percent']:.1f}%)")
        # show courses already taken (formatted LETTER SPACE NUMBER)
        taken_fmt = [re.sub(r'([A-Za-z]+)(\d+)', r'\1 \2', c) for c in r["taken_codes"]]
        st.write("Courses already taken:", ", ".join(taken_fmt))
        # show pending courses by category
        st.write("Pending requirements:")
        for sec, pending in r["pending_sections"].items():
            # clean up section title spacing around hyphens
            sec_clean = re.sub(r"\s*-\s*", " - ", sec).strip()
            lower = sec_clean.lower()
            # handle choose sections specially
            if "choose" in lower:
                # parse required number
                m = re.search(r'choose\s+(\d+)', lower)
                req = int(m.group(1)) if m else 1
                # calculate how many selected (req - remaining)
                taken_here = req - len(pending)
                remaining = req - taken_here
                # skip if fully satisfied
                if remaining <= 0:
                    continue
                # display slots remaining options and pending list (formatted LETTER SPACE NUMBER)
                pending_fmt = [re.sub(r'([A-Za-z]+)(\d+)', r'\1 \2', c) for c in pending]
                st.write(f"**{sec_clean} – {remaining} remaining options:** {', '.join(pending_fmt)}")
            else:
                # required section
                if pending:
                    pending_fmt = [re.sub(r'([A-Za-z]+)(\d+)', r'\1 \2', c) for c in pending]
                    st.write(f"**{sec_clean}:** {', '.join(pending_fmt)}")
                else:
                    st.write(f"**{sec_clean}:** All completed")

if __name__ == '__main__':
    main()
