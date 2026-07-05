import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover - optional dependency during setup
    sync_playwright = None

BASE_URL = "https://catalog.purdue.edu"
MINORS_PAGE = "https://catalog.purdue.edu/content.php?catoid=19&navoid=25481"
MAJORS_PAGE = "https://www.admissions.purdue.edu/majors/"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    )
}
COURSE_CODE_RE = re.compile(r"[A-Z]{2,4}\s*\d{3,5}")


def _normalize_text(text):
    return " ".join(text.split()).strip()


def _fetch_html(url):
    res = requests.get(url, headers=REQUEST_HEADERS, timeout=30)
    if res.ok and res.text.strip():
        return res.text

    if sync_playwright is not None:
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(
                    user_agent=REQUEST_HEADERS["User-Agent"],
                    viewport={"width": 1440, "height": 1200},
                )
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass
                html = page.content()
                browser.close()
                if html.strip():
                    return html
        except Exception:
            pass

    res.raise_for_status()
    return res.text


def _extract_course_codes(text):
    return sorted({code.replace(" ", "") for code in COURSE_CODE_RE.findall(text.upper())})


def _extract_excluded_codes(text):
    lower = text.lower()
    excluded = set()

    if "except" in lower:
        parts = re.split(r"(?i)except", text, maxsplit=1)
        tail = parts[1] if len(parts) > 1 else ""
        excluded.update(_extract_course_codes(tail))

    for phrase in ("cannot be counted", "cannot be used", "does not count"):
        if phrase in lower:
            excluded.update(_extract_course_codes(text))

    return sorted(excluded)


def _is_choice_title(title):
    lower = title.lower()
    return "choose" in lower or "select from" in lower or (
        "select" in lower and "from" in lower
    )


def _parse_required_count(title, default=None):
    lower = title.lower()
    word_map = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
    }

    for pattern in (
        r"choose\s+(\d+|one|two|three|four|five)",
        r"select\s+(\d+|one|two|three|four|five)",
    ):
        match = re.search(pattern, lower)
        if match:
            token = match.group(1)
            if token.isdigit():
                return int(token)
            return word_map.get(token, default)

    credit_match = re.search(r"\((\d+)\s*(?:-\s*\d+)?\s*credits?\)", title, re.I)
    if credit_match:
        return max(1, int(credit_match.group(1)) // 3)

    return default


def _collect_content_nodes(start_heading, stop_tags=None):
    stop_tags = stop_tags or {"h2", "h3", "h4"}
    nodes = []
    node = start_heading.next_sibling
    while node is not None:
        name = getattr(node, "name", None)
        if name in stop_tags:
            break
        if name is not None:
            nodes.append(node)
        node = node.next_sibling
    return nodes


def _parse_list_groups(list_node):
    li_texts = [
        _normalize_text(li.get_text(" ", strip=True))
        for li in list_node.find_all("li", recursive=False)
    ]
    clusters = []
    current_cluster = []

    for text in li_texts:
        if not text:
            if current_cluster:
                clusters.append(current_cluster)
                current_cluster = []
            continue
        current_cluster.append(text)

    if current_cluster:
        clusters.append(current_cluster)

    groups = []
    for cluster in clusters:
        connector_mode = any(
            item.upper() == "OR"
            or re.search(r"\b(or|and)\b\s*$", item, re.I)
            for item in cluster
        )

        if connector_mode:
            alternatives = []
            current_alt = []
            for item in cluster:
                current_alt.extend(_extract_course_codes(item))
                if item.upper() == "OR" or re.search(r"\bor\b\s*$", item, re.I):
                    if current_alt:
                        alternatives.append(sorted(set(current_alt)))
                        current_alt = []
                    continue
                if re.search(r"\band\b\s*$", item, re.I):
                    continue
            if current_alt:
                alternatives.append(sorted(set(current_alt)))
            if alternatives:
                groups.append(alternatives)
            continue

        for item in cluster:
            codes = _extract_course_codes(item)
            if not codes:
                continue
            if len(codes) > 1 and re.search(r"\band\b", item, re.I):
                groups.append([sorted(set(codes))])
            else:
                for code in codes:
                    groups.append([[code]])

    return groups


def _parse_content_nodes(nodes):
    groups = []
    codes = []
    descriptions = []
    excluded_codes = []

    for node in nodes:
        if getattr(node, "name", None) in {"ul", "ol"}:
            groups.extend(_parse_list_groups(node))
            for item in node.find_all("li"):
                item_text = item.get_text(" ", strip=True)
                codes.extend(_extract_course_codes(item_text))
                excluded_codes.extend(_extract_excluded_codes(item_text))
            continue

        text = _normalize_text(node.get_text(" ", strip=True))
        if not text:
            continue

        node_codes = _extract_course_codes(text)
        if node_codes:
            groups.append([[node_codes]])
            codes.extend(node_codes)
            excluded_codes.extend(_extract_excluded_codes(text))
        else:
            descriptions.append(text)
            excluded_codes.extend(_extract_excluded_codes(text))

    return {
        "groups": groups,
        "codes": sorted(set(codes)),
        "descriptions": descriptions,
        "excluded_codes": sorted(set(excluded_codes)),
    }


def _build_section_block(title, nodes, child_blocks=None):
    parsed = _parse_content_nodes(nodes)
    title = _normalize_text(title)

    if child_blocks and _is_choice_title(title):
        option_codes = set(parsed["codes"])
        for child in child_blocks:
            option_codes.update(child.get("codes", []))
            option_codes.update(child.get("options", []))

        required = _parse_required_count(title, default=max(1, len(option_codes) // 3))
        return {
            "title": title,
            "kind": "pool",
            "required": required,
            "options": sorted(option_codes),
            "children": child_blocks,
            "notes": parsed["descriptions"],
            "excluded_codes": parsed["excluded_codes"],
        }

    if parsed["groups"]:
        return {
            "title": title,
            "kind": "formula",
            "required": _parse_required_count(title, default=len(parsed["groups"])),
            "groups": parsed["groups"],
            "codes": parsed["codes"],
            "notes": parsed["descriptions"],
            "excluded_codes": parsed["excluded_codes"],
        }

    if parsed["descriptions"]:
        return {
            "title": title,
            "kind": "manual",
            "description": " ".join(parsed["descriptions"]),
            "excluded_codes": parsed["excluded_codes"],
        }

    return None


def _collect_text_lines(nodes):
    lines = []
    for node in nodes:
        if getattr(node, "name", None) in {"ul", "ol"}:
            for li in node.find_all("li"):
                text = _normalize_text(li.get_text(" ", strip=True))
                if text:
                    lines.append(text)
        else:
            text = _normalize_text(node.get_text(" ", strip=True))
            if text:
                lines.append(text)
    return lines


def get_minor_list():
    """
    Return a list of (minor_name, url) tuples for each minor preview page.
    """
    soup = BeautifulSoup(_fetch_html(MINORS_PAGE), "html.parser")
    minor_links = []
    seen = set()
    for a in soup.find_all("a", href=re.compile(r"preview_program\.php")):
        name = _normalize_text(a.get_text(" ", strip=True))
        if "Minor" not in name:
            continue
        link = urljoin(BASE_URL, a["href"])
        if link in seen:
            continue
        seen.add(link)
        minor_links.append((name, link))
    return minor_links


def get_minors_requirements():
    # Scrape all minor links via preview_program pages
    soup = BeautifulSoup(_fetch_html(MINORS_PAGE), "html.parser")
    minors = {}
    for a in soup.find_all("a", href=re.compile(r"preview_program\.php")):
        name = _normalize_text(a.get_text(" ", strip=True))
        if "Minor" not in name:
            continue
        link = urljoin(BASE_URL, a["href"])
        try:
            reqs = _get_requirements_from_minor_page(link)
        except Exception:
            reqs = ([], [], "")
        minors[name] = reqs
    return minors


def _get_requirements_from_minor_page(url):
    # Scrape course requirements from the rendered catalog page.
    soup = BeautifulSoup(_fetch_html(url), "html.parser")
    main = soup.find("main") or soup.body or soup
    headings = [h for h in main.find_all(["h2", "h3", "h4"]) if _normalize_text(h.get_text(" ", strip=True))]
    sections = []
    notes = []
    restriction_texts = []

    start_index = 0
    for idx, heading in enumerate(headings):
        heading_text = _normalize_text(heading.get_text(" ", strip=True))
        if heading.name.lower() == "h2" and heading_text.lower().startswith("requirements for the minor"):
            start_index = idx + 1
            break

    i = start_index
    while i < len(headings):
        heading = headings[i]
        title = _normalize_text(heading.get_text(" ", strip=True))
        tag = heading.name.lower()

        if tag == "h2":
            lower = title.lower()
            if lower == "notes":
                note_nodes = _collect_content_nodes(heading)
                notes.extend(_collect_text_lines(note_nodes))
                restriction_texts.extend(_collect_text_lines(note_nodes))
            elif any(keyword in lower for keyword in ("policy", "pre-requisite", "disclaimer")):
                restriction_nodes = _collect_content_nodes(heading)
                restriction_texts.extend(_collect_text_lines(restriction_nodes))
            i += 1
            continue

        if tag != "h3":
            i += 1
            continue

        if title.lower().startswith("location(s):"):
            i += 1
            continue

        child_headings = []
        j = i + 1
        while j < len(headings) and headings[j].name.lower() == "h4":
            child_headings.append(headings[j])
            j += 1

        direct_nodes = _collect_content_nodes(heading)

        if _is_choice_title(title) and child_headings:
            child_blocks = []
            for child in child_headings:
                child_title = _normalize_text(child.get_text(" ", strip=True))
                child_nodes = _collect_content_nodes(child)
                child_block = _build_section_block(child_title, child_nodes)
                if child_block:
                    child_blocks.append(child_block)
            block = _build_section_block(title, direct_nodes, child_blocks=child_blocks)
            if block:
                sections.append(block)
        else:
            if direct_nodes:
                block = _build_section_block(title, direct_nodes)
                if block:
                    sections.append(block)
            for child in child_headings:
                child_title = _normalize_text(child.get_text(" ", strip=True))
                child_nodes = _collect_content_nodes(child)
                child_block = _build_section_block(child_title, child_nodes)
                if child_block:
                    sections.append(child_block)

        i = j

    return sections, notes, " ".join(restriction_texts)


def get_majors_list():
    """
    Scrape the Purdue admissions majors page and return a sorted list of major names.
    """
    soup = BeautifulSoup(_fetch_html(MAJORS_PAGE), "html.parser")
    majors = []
    seen = set()
    # the majors appear under the div with id 'all-majors-container'
    for h2 in soup.find_all("h2"):
        text = _normalize_text(h2.get_text(" ", strip=True))
        if not text or text.upper() in {"FOLLOW US", "EXPLORE", "APPLY", "INFORMATION FOR"}:
            continue
        link = h2.find_next("a", href=True)
        if not link:
            continue
        parsed = urlparse(link["href"])
        if not parsed.path.startswith("/majors/"):
            continue
        if text in seen:
            continue
        seen.add(text)
        majors.append(text)
    return sorted(set(majors))
