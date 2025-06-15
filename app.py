import math
import re

import streamlit as st

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
        "It is still in development, so please report any issues or suggestions on the [GitHub repository](https://github.com/arnavsiva/Purdue-University-Minor-Optimizer)"
    )

    # Sidebar - user information input and course management
    st.sidebar.header("Your Information")
    # select current major (to avoid recommending the same minor)
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

    # proceed once optimization triggered
    with st.spinner("Loading minor requirements..."):
        status = st.empty()
        minors_data = []
        for name, link in get_minor_list():
            status.text(f"Loading requirements for {name}...")
            try:
                sections, notes = _get_requirements_from_minor_page(link)
            except Exception:
                sections, notes = {}, []
            minors_data.append(
                {"name": name, "link": link, "sections": sections, "notes": notes}
            )
        status.empty()

    # compute recommendations
    with st.spinner("Computing top recommendations..."):
        status = st.empty()
        results = []
        for minor in minors_data:
            name = minor["name"]
            # derive department prefix (first 4 letters) for level-based logic
            dept_prefix = name.split()[0][:4].upper()
            link = minor["link"]
            status.text(f"Checking {name} minor...")
            sections = minor["sections"]
            notes = minor.get("notes", [])
            # calculate per-section requirements
            # flatten codes (including nested OR groups) into a single list
            raw_codes = []
            for codes in sections.values():
                if isinstance(codes, list) and codes and isinstance(codes[0], list):
                    for group in codes:
                        raw_codes.extend(group)
                else:
                    raw_codes.extend(codes)
            # filter to valid course codes only (exclude descriptive text)
            import re as _re

            code_pattern = _re.compile(r"^[A-Z]{2,4}\d{3,5}$")
            total_req = 0
            completed_req = 0
            taken_codes = []
            # iterate each section to compute required selections
            for sec, codes_list in sections.items():
                # filter valid course codes
                sec_codes = [c for c in codes_list if code_pattern.match(c)]
                # handle level-based requirements: count courses taken at/above level threshold
                if "level" in sec.lower():
                    # parse level threshold and credits
                    m_thr = re.search(r"(\d+)\s*Level", sec, re.IGNORECASE)
                    level_threshold = int(m_thr.group(1)) if m_thr else 0
                    m_cred = re.search(r"\((\d+)\s+credits?", sec, re.IGNORECASE)
                    credits = int(m_cred.group(1)) if m_cred else 0
                    req_level = max(1, credits // 3)
                    total_req += req_level
                    # count taken courses for this minor’s department at or above threshold
                    taken_level = 0
                    for c in taken:
                        if c.startswith(dept_prefix):
                            num = int(re.match(r"[A-Za-z]+(\d+)", c).group(1))
                            if num >= level_threshold:
                                taken_level += 1
                                taken_codes.append(c)
                    completed_req += min(taken_level, req_level)
                    continue
                if not sec_codes:
                    continue  # skip sections without actual course codes
                lower = sec.lower()
                # determine number of selections required
                if "choose" in lower:
                    m = re.search(r"choose\s+(\d+)", lower)
                    if m:
                        req = int(m.group(1))
                    else:
                        # fallback to credit parsing
                        m2 = re.search(
                            r"\((\d+)(?:-\d+)?\s+credits?", sec, re.IGNORECASE
                        )
                        credits = int(m2.group(1)) if m2 else 3
                        req = max(1, credits // 3)
                else:
                    # parse credit parentheses for mandatory sections
                    m3 = re.search(r"\((\d+)(?:-\d+)?\s+credits?", sec, re.IGNORECASE)
                    if m3:
                        credits = int(m3.group(1))
                        req = max(1, credits // 3)
                    else:
                        # default: need all listed courses
                        req = len(sec_codes)
                # count how many taken in this section
                taken_in_sec = len(set(sec_codes) & taken)
                # accumulate
                total_req += req
                completed_req += min(taken_in_sec, req)
                # collect taken codes overall
                taken_codes.extend(set(sec_codes) & taken)
            if total_req == 0:
                continue
            # skip minors with no completed courses
            if completed_req == 0:
                continue
            completed = completed_req
            total = total_req
            percent = (completed / total) * 100
            # compute pending courses per section, disallow reusing chosen courses for multiple choose-one sections
            available_taken = set(taken_codes)
            pending_sections = {}
            for sec, codes in sections.items():
                # normalize section title
                lower = sec.lower()
                # level-based requirements (e.g., “20000 Level or Above”): compute remaining courses
                if "level" in lower:
                    # parse level threshold and credits
                    m_lvl = re.search(r"(\d+)\s*Level", sec, re.IGNORECASE)
                    level_threshold = int(m_lvl.group(1)) if m_lvl else 20000
                    m_cred = re.search(r"\((\d+)\s+credits?", sec, re.IGNORECASE)
                    credits = int(m_cred.group(1)) if m_cred else 0
                    req_cnt = max(1, credits // 3)
                    # count taken courses for this department at or above threshold
                    taken_level = sum(
                        1
                        for c in taken
                        if c.startswith(dept_prefix)
                        and int(re.match(r"[A-Za-z]+(\d+)", c).group(1))
                        >= level_threshold
                    )
                    remaining = max(0, req_cnt - taken_level)
                    pending_sections[sec] = remaining
                    continue
                # descriptive or instruction-only sections (no course codes)
                if not codes or all(not code_pattern.match(c) for c in codes):
                    pending_sections[sec] = None
                    continue
                # treat explicit 'choose' or credit-based requirements as choose-X
                if "choose" in lower or re.search(
                    r"\(\d+\s+credits", sec, re.IGNORECASE
                ):
                    # parse how many courses to select
                    m = re.search(r"choose\s+(\d+)", lower)
                    if m:
                        req = int(m.group(1))
                    else:
                        # try word numbers e.g. 'choose two'
                        m2 = re.search(r"choose\s+(one|two|three|four|five)", lower)
                        word_map = {
                            "one": 1,
                            "two": 2,
                            "three": 3,
                            "four": 4,
                            "five": 5,
                        }
                        req = word_map.get(m2.group(1), 1) if m2 else None
                    if req is None:
                        # fallback: use credits in parentheses / 3
                        m3 = re.search(r"\((\d+)\s+credits", sec, re.IGNORECASE)
                        credits = int(m3.group(1)) if m3 else 3
                        req = max(1, credits // 3)
                    # prepare set of valid codes for this section, excluding placeholder codes ending in '000'
                    codes_set = set(
                        [
                            c
                            for c in codes
                            if code_pattern.match(c) and not c.endswith("0000")
                        ]
                    )
                    chosen_list = list(available_taken & codes_set)
                    # consume only up to the required number, leave extras for D.1
                    for sel in chosen_list[:req]:
                        available_taken.discard(sel)
                    if len(chosen_list) >= req:
                        # section fully satisfied
                        pending_sections[sec] = []
                    else:
                        # still need to pick courses: list remaining options
                        pending_sections[sec] = [
                            c
                            for c in codes
                            if c not in taken and not c.endswith("0000")
                        ]
                else:
                    # standard section: pending are those not taken
                    pending_sections[sec] = [
                        c for c in codes if c not in taken and not c.endswith("0000")
                    ]
            # special-case Additional Course from Section B or C (D.1)
            for sec, codes in sections.items():
                if sec.strip().startswith("D. 1."):
                    # choose-1 additional course from Section B or top-level C
                    bc_codes = []
                    for k, opts in sections.items():
                        if k.startswith("B.") or (
                            k.startswith("C.") and not re.match(r"C\.\s*\d", k)
                        ):
                            bc_codes.extend([c for c in opts if code_pattern.match(c)])
                    # treat as a 'choose 1' from B/C using any remaining available_taken
                    chosen = set(bc_codes) & available_taken
                    if chosen:
                        pending_sections[sec] = []
                    else:
                        # list all options not yet taken
                        pending_sections[sec] = [c for c in bc_codes if c not in taken]
                    continue
            # special-case International Experience (D.2)
            for sec, codes in sections.items():
                if sec.strip().startswith("D. 2."):
                    # separate explicit course codes and descriptive options
                    explicit_codes = [c for c in codes if code_pattern.match(c)]
                    descriptive = [c for c in codes if not code_pattern.match(c)]
                    # start with unmet explicit codes
                    pending = [c for c in explicit_codes if c not in taken]
                    # include descriptive options if user hasn't covered experience
                    if not (
                        st.session_state.get("study_abroad")
                        or st.session_state.get("intl_internship")
                    ):
                        pending.extend(descriptive)
                    pending_sections[sec] = pending
                    continue
            results.append(
                {
                    "name": name,
                    "link": link,
                    "taken_codes": taken_codes,
                    "pending_sections": pending_sections,
                    "sections": sections,
                    "notes": notes,
                    "total": total,
                    "completed": completed,
                    "percent": percent,
                }
            )
        status.empty()

    # filter out any minor matching the user's current major
    if st.session_state.get("major") and st.session_state.major != "None":
        filter_name = f"{st.session_state.major} Minor"
        results = [r for r in results if r["name"] != filter_name]
    # sort by number of courses completed desc
    results = sorted(results, key=lambda x: x["percent"], reverse=True)

    if not results:
        st.info("No minors found with requirements.")
        return

    st.subheader("Recommended Minors")
    st.write(f"{len(results)} minors match your completed coursework:")

    for r in results:
        st.markdown("---")  # separator before minor header
        st.markdown(f"### {r['name']}")
        st.markdown(f"[View catalog page]({r['link']})  ")  # two spaces for newline
        # Display progress immediately after catalog link
        st.markdown(
            f"**Progress:** {r['completed']} / {r['total']} courses completed ({r['percent']:.1f}%)"
        )
        # Purdue residency requirement
        req_pcnt = None
        for note in notes:
            m = re.search(r"(\d+)%", note)
            if m:
                req_pcnt = int(m.group(1))
                break
        if req_pcnt:
            req_courses = math.ceil(r["total"] * req_pcnt / 100)
            allowed_ext = r["total"] - req_courses
            st.markdown(
                f"**Residency requirement:** At least {req_courses}/{r['total']} courses at Purdue ({req_pcnt}%), up to {allowed_ext} external."
            )
        # show courses already taken
        taken_fmt = [re.sub(r"([A-Za-z]+)(\d+)", r"\1 \2", c) for c in r["taken_codes"]]
        st.markdown("**Courses already taken:**\n- " + "\n- ".join(taken_fmt))
        # pending requirements
        st.markdown("**Pending requirements:**")
        sections_dict = r["sections"]
        pending_map = r["pending_sections"]
        # exclude navigation-like sections
        nav_prefixes = ("communication", "campus", "services", "other")
        # base sections (A-C)
        base_keys = [
            k
            for k in sections_dict
            if not any(k.strip().lower().startswith(n) for n in nav_prefixes)
            and not k.strip().lower().startswith("d.")
        ]
        # hide parent C if C.1/C.2 subsections exist
        c_keys = [k for k in sections_dict if k.strip().lower().startswith("c.")]
        # identify C subsections
        c1 = next((k for k in c_keys if re.match(r"c\.\s*1", k.strip().lower())), None)
        c2 = next((k for k in c_keys if re.match(r"c\.\s*2", k.strip().lower())), None)
        parent_c = next((k for k in c_keys if k not in (c1, c2)), None)
        if parent_c and (c1 or c2):
            base_keys = [k for k in base_keys if k != parent_c]
        # detect D sections: parent header and subsections D.1, D.2
        d_keys = [k for k in sections_dict if k.strip().lower().startswith("d.")]
        d1 = next((k for k in d_keys if re.match(r"d\.\s*1", k.strip().lower())), None)
        d2 = next((k for k in d_keys if re.match(r"d\.\s*2", k.strip().lower())), None)
        parent_d = next((k for k in d_keys if k not in (d1, d2)), None)
        # decide which D sections to display
        d_display = []
        if parent_d and (d1 or d2):
            # Option parent: show both until one completed, then collapse to parent only
            done1 = bool(d1 and pending_map.get(d1) == [])
            done2 = bool(d2 and pending_map.get(d2) == [])
            if not (done1 or done2):
                # neither option complete: show both subsections
                d_display = [sec for sec in (d1, d2) if sec]
            else:
                # collapse into parent: mark parent completed and hide subsections
                pending_map[parent_d] = []
                if d1:
                    pending_map.pop(d1, None)
                if d2:
                    pending_map.pop(d2, None)
                d_display = [parent_d]
        elif parent_d:
            # non-option parent: show only parent D
            d_display = [parent_d]

        # combine, sort, and render sections
        def sort_key(k):
            m = re.match(r"^([A-Z])\.\s*(\d+)?", k)
            if m:
                return (ord(m.group(1)), int(m.group(2)) if m.group(2) else 0)
            return (ord(k[0]) if k else 999, 0)

        ordered = sorted(base_keys + d_display, key=sort_key)

        # render sections
        for sec in ordered:
            label = re.sub(r"\s*[--]\s*", " - ", sec).strip()
            pend = pending_map.get(sec)
            if isinstance(pend, int):
                st.markdown(f"**{label}:** {pend} remaining courses")
            elif pend is None:
                st.markdown(f"**{label}:** manual")
            elif not pend:
                st.markdown(f"**{label}:** All completed")
            else:
                opts = [re.sub(r"([A-ZaZ]+)(\d+)", r"\1 \2", c) for c in pend]
                if re.search(r"choose", label.lower()) or re.search(
                    r"\(\d+ credits?\)", label, re.IGNORECASE
                ):
                    m = re.search(r"\((\d+)", sec)
                    req = int(m.group(1)) // 3 if m else len(opts)
                    taken = req - len(pend)
                    rem = req - taken
                    st.markdown(
                        f"**{label} - {rem} remaining options:** {', '.join(opts)}"
                    )
                else:
                    st.markdown(f"**{label}:** {', '.join(opts)}")
        # render separator and/or notes combined to avoid extra break
        notes = r.get("notes", [])
        if notes:
            # clean note text and ensure 'NOT overlap' has proper space
            cleaned = []
            for n in notes:
                txt = re.sub(r"^[\*\^]+\s*", "", n)
                # fix missing space in 'NOT overlap'
                txt = re.sub(r"NOT\s*overlap", "NOT overlap", txt, flags=re.IGNORECASE)
                cleaned.append(txt)
            # render only the Notes label and list without extra lines
            notes_html = '<div style="margin:0;padding:0">'
            notes_html += '<p style="margin:0;"><strong>Notes:</strong></p>'
            notes_html += '<ul style="margin:0;padding-left:1.25em;">'
            for cn in cleaned:
                notes_html += f'<li style="margin:0">{cn}</li>'
            notes_html += "</ul></div>"
            st.markdown(notes_html, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
