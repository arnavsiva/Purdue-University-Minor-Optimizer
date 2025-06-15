import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://catalog.purdue.edu"
MINORS_PAGE = "https://catalog.purdue.edu/content.php?catoid=13&navoid=16362"
MAJORS_PAGE = "https://www.admissions.purdue.edu/majors/"


def get_minor_list():
    """
    Return a list of (minor_name, url) tuples for each minor preview page.
    """
    res = requests.get(MINORS_PAGE)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    minor_links = []
    for a in soup.find_all("a", href=re.compile(r"preview_program\.php")):
        name = a.get_text(strip=True)
        if "Minor" not in name:
            continue
        link = urljoin(BASE_URL, a["href"])
        minor_links.append((name, link))
    return minor_links


def get_minors_requirements():
    # Scrape all minor links via preview_program pages
    res = requests.get(MINORS_PAGE)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    minors = {}
    for a in soup.find_all("a", href=re.compile(r"preview_program\.php")):
        name = a.get_text(strip=True)
        if "Minor" not in name:
            continue
        link = urljoin(BASE_URL, a["href"])
        try:
            reqs = _get_requirements_from_minor_page(link)
        except Exception:
            reqs = []
        minors[name] = reqs
    return minors


def _get_requirements_from_minor_page(url):
    # scrape course requirements by category headings (h3)
    res = requests.get(url)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    sections = {}
    notes = []
    # find each category under h3 headings
    for header in soup.find_all("h3"):
        title = header.get_text(strip=True)
        ul = header.find_next_sibling("ul")
        if not ul:
            # capture descriptive paragraph if available (e.g., co-requisites, instructions)
            p = header.find_next_sibling("p")
            if p:
                info = p.get_text(strip=True)
                sections[title] = [info]
            else:
                # no list or paragraph: include empty placeholder to preserve the section header
                sections[title] = []
            continue
        # capture Notes separately
        if title.lower() == "notes":
            notes = [li.get_text(strip=True) for li in ul.find_all("li")]
            continue
        codes = set()
        # include all list items under this section
        for li in ul.find_all("li"):
            text = li.get_text(separator=" ", strip=True)
            found = re.findall(r"[A-Z]{2,4}\s*\d{3,5}", text)
            for c in found:
                codes.add(c.replace(" ", ""))
        if codes:
            sections[title] = sorted(codes)
    # general capture for Notes section in any header level
    if not notes:
        for hdr in soup.find_all(re.compile("^h[2-6]$")):
            if hdr.get_text(strip=True).lower() == "notes":
                ul = hdr.find_next_sibling("ul")
                if ul:
                    notes = [li.get_text(strip=True) for li in ul.find_all("li")]
                break
    # capture h4 subsections (e.g., C1, C2) under h3 sections, prefixing with parent letter
    for sub in soup.find_all("h4"):
        sub_title = sub.get_text(strip=True)
        # determine parent h3 letter prefix
        parent_hdr = sub.find_previous("h3")
        if parent_hdr:
            parent_text = parent_hdr.get_text(strip=True)
            m_parent = re.match(r"^([A-Z])\.", parent_text)
            if m_parent:
                parent_letter = m_parent.group(1)
                key = f"{parent_letter}. {sub_title}"
            else:
                key = sub_title
        else:
            key = sub_title
        # try list of courses
        ul = sub.find_next_sibling("ul")
        if ul:
            codes = []
            for li in ul.find_all("li"):
                text = li.get_text(separator=" ", strip=True)
                found = re.findall(r"[A-Z]{2,4}\s*\d{3,5}", text)
                if found:
                    codes.extend([c.replace(" ", "") for c in found])
                else:
                    # include adhoc list items as raw info
                    codes.append(text)
            if codes:
                sections[key] = codes
        else:
            # fallback: capture next paragraph text or at least include section key
            p = sub.find_next_sibling()
            if p and p.name == "p":
                info = p.get_text(strip=True)
                sections[key] = [info]
            else:
                # no list or paragraph, include empty placeholder to show descriptive subsection
                sections[key] = []
    return sections, notes


def get_majors_list():
    """
    Scrape the Purdue admissions majors page and return a sorted list of major names.
    """
    res = requests.get(MAJORS_PAGE)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")
    majors = []
    # the majors appear under the div with id 'all-majors-container'
    container = soup.find(id="all-majors-container")
    if container:
        for li in container.find_all("li"):
            a = li.find("a")
            if a:
                text = a.get_text(strip=True)
                if text:
                    majors.append(text)
    return sorted(set(majors))
