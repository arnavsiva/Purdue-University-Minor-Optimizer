import math
import re


def flatten_course_codes(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(flatten_course_codes(item))
        return flattened
    return []


def format_course(code):
    return re.sub(r"([A-Za-z]+)(\d+)", r"\1 \2", code)


def clean_notes(notes):
    cleaned = []
    for note in notes:
        text = re.sub(r"^[\*\^]+\s*", "", note)
        text = re.sub(r"NOT\s*overlap", "NOT overlap", text, flags=re.IGNORECASE)
        cleaned.append(text)
    return cleaned


def major_restriction_applies(major, restriction_text):
    if not major or major == "None" or not restriction_text:
        return False

    normalized_major = re.sub(r"[^a-z0-9]+", " ", major.lower()).strip()
    text = restriction_text.lower()
    sentences = re.split(r"[\n\.!?;]+", text)
    negative_phrases = [
        "not available",
        "not open",
        "not allowed",
        "not permitted",
        "may not",
        "cannot",
        "can't",
        "restricted",
        "only open",
        "only available",
    ]

    for sentence in sentences:
        if normalized_major not in sentence:
            continue
        if any(phrase in sentence for phrase in negative_phrases):
            return True
    return False


def evaluate_formula_section(section, taken):
    groups = section.get("groups", [])
    excluded_codes = set(section.get("excluded_codes", []))
    completed = 0
    taken_codes = []
    pending_groups = []

    for group in groups:
        best_missing = None
        best_alt = None
        satisfied = False
        for alt in group:
            codes = [code for code in flatten_course_codes(alt) if code not in excluded_codes]
            if not codes:
                continue
            missing = [code for code in codes if code not in taken]
            if not missing:
                completed += 1
                taken_codes.extend([code for code in codes if code in taken])
                satisfied = True
                break
            if best_missing is None or len(missing) < len(best_missing):
                best_missing = missing
                best_alt = codes
        if not satisfied:
            pending_groups.append({"options": best_alt or [], "missing": best_missing or []})

    total = section.get("required") or len(groups)
    percent = (completed / total * 100) if total else 0
    return {
        "kind": "formula",
        "title": section.get("title", "Section"),
        "total": total,
        "completed": min(completed, total),
        "percent": percent,
        "taken_codes": sorted(set(taken_codes)),
        "pending_groups": pending_groups,
        "notes": section.get("notes", []),
    }


def evaluate_pool_section(section, taken):
    excluded_codes = set(section.get("excluded_codes", []))
    options = sorted(set(code for code in section.get("options", []) if code not in excluded_codes))
    selected = sorted(set(options) & taken)
    total = section.get("required") or max(1, len(options) // 3)
    completed = min(total, len(selected))
    percent = (completed / total * 100) if total else 0
    return {
        "kind": "pool",
        "title": section.get("title", "Section"),
        "total": total,
        "completed": completed,
        "percent": percent,
        "taken_codes": selected,
        "remaining_options": [code for code in options if code not in taken],
        "children": section.get("children", []),
        "notes": section.get("notes", []),
    }


def evaluate_manual_section(section):
    return {
        "kind": "manual",
        "title": section.get("title", "Section"),
        "total": 0,
        "completed": 0,
        "percent": 0,
        "taken_codes": [],
        "description": section.get("description", ""),
    }


def evaluate_section(section, taken):
    kind = section.get("kind")
    if kind == "pool":
        return evaluate_pool_section(section, taken)
    if kind == "manual":
        return evaluate_manual_section(section)
    return evaluate_formula_section(section, taken)


def section_blocks_to_result(blocks, taken):
    return [evaluate_section(block, taken) for block in blocks]


def summarize_minor(minor, taken, major=None):
    if major_restriction_applies(major, minor.get("restriction_text", "")):
        return None

    block_results = section_blocks_to_result(minor.get("sections", []), taken)
    total_req = sum(result["total"] for result in block_results)
    completed_req = sum(result["completed"] for result in block_results)
    if total_req == 0 or completed_req == 0:
        return None

    return {
        "name": minor["name"],
        "link": minor["link"],
        "taken_codes": sorted({code for result in block_results for code in result["taken_codes"]}),
        "section_results": block_results,
        "notes": minor.get("notes", []),
        "total": total_req,
        "completed": completed_req,
        "percent": (completed_req / total_req) * 100 if total_req else 0,
    }


def sort_minor_results(results):
    return sorted(results, key=lambda item: (-item["percent"], item["total"] - item["completed"], item["name"]))


def residency_requirement(total_courses, notes):
    req_pcnt = None
    for note in notes:
        match = re.search(r"(\d+)%", note)
        if match:
            req_pcnt = int(match.group(1))
            break
    if req_pcnt is None:
        return None
    req_courses = math.ceil(total_courses * req_pcnt / 100)
    allowed_ext = total_courses - req_courses
    return req_pcnt, req_courses, allowed_ext