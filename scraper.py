import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

BASE_URL = 'https://catalog.purdue.edu'
MINORS_PAGE = 'https://catalog.purdue.edu/content.php?catoid=13&navoid=16362'

def get_minor_list():
    """
    Return a list of (minor_name, url) tuples for each minor preview page.
    """
    res = requests.get(MINORS_PAGE)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    minor_links = []
    for a in soup.find_all('a', href=re.compile(r'preview_program\.php')):
        name = a.get_text(strip=True)
        if 'Minor' not in name:
            continue
        link = urljoin(BASE_URL, a['href'])
        minor_links.append((name, link))
    return minor_links

def get_minors_requirements():
    # Scrape all minor links via preview_program pages
    res = requests.get(MINORS_PAGE)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    minors = {}
    for a in soup.find_all('a', href=re.compile(r'preview_program\.php')):
        name = a.get_text(strip=True)
        if 'Minor' not in name:
            continue
        link = urljoin(BASE_URL, a['href'])
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
    soup = BeautifulSoup(res.text, 'html.parser')
    sections = {}
    # find each category under h3 headings
    for header in soup.find_all('h3'):
        title = header.get_text(strip=True)
        ul = header.find_next_sibling('ul')
        if not ul:
            continue
        codes = set()
        # include all list items under this section
        for li in ul.find_all('li'):
            text = li.get_text(separator=' ', strip=True)
            found = re.findall(r'[A-Z]{2,4}\s*\d{3,5}', text)
            for c in found:
                codes.add(c.replace(' ', ''))
        if codes:
            sections[title] = sorted(codes)
    return sections
