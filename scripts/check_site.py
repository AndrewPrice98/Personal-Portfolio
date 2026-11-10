"""Check the static site. Usage: python -I scripts/check_site.py public

Exits 0 when clean, otherwise 1 with one line per problem: "<file>: <problem>".
Standard library only. Add a check by writing check_x(site) -> list[str]
and appending it to CHECKS.
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SITE_PREFIX = "/Personal-Portfolio/"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr"}


class Site:
    def __init__(self, root):
        self.root = Path(root)
        self.pages = {
            p.relative_to(self.root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(self.root.rglob("*.html"))
        }


class TagWalker(HTMLParser):
    """Collects balance problems and every (tag, attrs) pair."""

    def __init__(self):
        super().__init__()
        self.stack, self.problems, self.tags = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag not in VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if tag in self.stack:
            while self.stack[-1] != tag:
                self.problems.append(f"unclosed <{self.stack.pop()}>")
            self.stack.pop()
        else:
            self.problems.append(f"stray </{tag}>")


def walk(html):
    w = TagWalker()
    w.feed(html)
    w.close()
    w.problems += [f"unclosed <{t}>" for t in w.stack]
    return w


def check_balanced(site):
    return [f"{name}: {p}" for name, html in site.pages.items()
            for p in walk(html).problems]


class IdWalker(HTMLParser):
    """Collects every id and anchor name on a page."""

    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.ids.update(v for k, v in a.items() if k == "id" and v)
        if tag == "a" and a.get("name"):
            self.ids.add(a["name"])


def page_ids(html):
    w = IdWalker()
    w.feed(html)
    w.close()
    return w.ids


def check_links(site):
    problems = []
    for name, html in site.pages.items():
        own_ids = page_ids(html)
        for tag, attrs in walk(html).tags:
            for attr in ("href", "src", "data"):
                if attr == "data" and tag != "object":
                    continue
                url = attrs.get(attr)
                if not url or url.startswith(("http:", "https:", "mailto:", "data:")):
                    continue
                path, _, fragment = url.split("?")[0].partition("#")
                if not path:
                    if fragment and fragment not in own_ids:
                        problems.append(f"{name}: broken fragment {url}")
                    continue
                if path.startswith(SITE_PREFIX):
                    target = site.root / path[len(SITE_PREFIX):]
                elif path.startswith("/"):
                    problems.append(f"{name}: {attr} {url} is missing the {SITE_PREFIX} prefix")
                    continue
                else:
                    target = (site.root / name).parent / path
                if target.is_dir():
                    target = target / "index.html"
                if not target.is_file():
                    problems.append(f"{name}: broken {attr} {url}")
                elif fragment and target.suffix == ".html":
                    rel = target.relative_to(site.root).as_posix()
                    if fragment not in page_ids(site.pages.get(rel, "")):
                        problems.append(f"{name}: {attr} {url} points at a missing #{fragment}")
    return problems


def check_no_empty_links(site):
    return [f"{name}: empty href" for name, html in site.pages.items()
            for tag, attrs in walk(html).tags if attrs.get("href") == ""]


NAV_TEXTS = ["Home", "Projects", "Resume", "Contact"]
TITLE_SUFFIX = "| Andrew T. Price II"


class TextWalker(HTMLParser):
    """Collects the link texts inside <nav>, the <title>, and the text and
    link classes inside the first element with class fast-lane."""

    def __init__(self):
        super().__init__()
        self.nav_depth = 0
        self.nav_links, self._link = [], None
        self.in_title, self.title = False, ""
        self.in_head = False
        self.fl_depth, self.fl_text, self.fl_classes = 0, "", []
        self.fl_seen = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "nav":
            self.nav_depth += 1
        if tag == "a" and self.nav_depth:
            self._link = ""
        if tag == "head":
            self.in_head = True
        if tag == "title" and self.in_head:
            self.in_title = True
        if self.fl_depth and tag not in VOID:
            self.fl_depth += 1
        elif "fast-lane" in classes and not self.fl_seen:
            self.fl_seen, self.fl_depth = True, 1
        if self.fl_depth:
            self.fl_classes += classes

    def handle_endtag(self, tag):
        if tag == "nav":
            self.nav_depth -= 1
        if tag == "a" and self._link is not None:
            self.nav_links.append(" ".join(self._link.split()))
            self._link = None
        if tag == "head":
            self.in_head = False
        if tag == "title":
            self.in_title = False
        if self.fl_depth and tag not in VOID:
            self.fl_depth -= 1

    def handle_data(self, data):
        if self._link is not None:
            self._link += data
        if self.in_title:
            self.title += data
        if self.fl_depth:
            self.fl_text += data


def text_walk(html):
    w = TextWalker()
    w.feed(html)
    w.close()
    return w


def check_nav(site):
    return [f"{name}: nav links are {w.nav_links}, expected {NAV_TEXTS}"
            for name, html in site.pages.items()
            if (w := text_walk(html)).nav_links != NAV_TEXTS]


def check_fast_lane(site):
    problems = []
    for name, html in site.pages.items():
        w = text_walk(html)
        if not w.fl_seen:
            problems.append(f"{name}: no .fast-lane element")
            continue
        for needle in ("Secret", "Security+", "open to work"):
            if needle not in w.fl_text:
                problems.append(f"{name}: fast lane is missing '{needle}'")
        for cls in ("fl-resume", "fl-linkedin"):
            if cls not in w.fl_classes:
                problems.append(f"{name}: fast lane is missing a .{cls} link")
    return problems


def check_titles(site):
    return [f"{name}: title '{t}' does not end with '{TITLE_SUFFIX}'"
            for name, html in site.pages.items()
            if not (t := text_walk(html).title.strip()).endswith(TITLE_SUFFIX)]


CASE_SLUGS = ["netguard", "minisiem", "cmmc-ready", "logingestllm", "ccna-study", "cysa-study",
              "job-tracker", "flight-tracker", "tempered", "sudo-snake"]
CASE_SECTIONS = ["Summary", "Problem", "What I built", "How it works",
                 "Evidence", "What I'd do next", "Links"]


class CaseWalker(HTMLParser):
    """Collects the h2 texts and the images of a case-file page."""

    def __init__(self):
        super().__init__()
        self.h2s, self._h2, self.imgs = [], None, []
        self.has_case = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article" and "case-file" in (a.get("class") or "").split():
            self.has_case = True
        if tag == "h2":
            self._h2 = ""
        if tag == "img":
            self.imgs.append(a)

    def handle_endtag(self, tag):
        if tag == "h2" and self._h2 is not None:
            self.h2s.append(" ".join(self._h2.split()))
            self._h2 = None

    def handle_data(self, data):
        if self._h2 is not None:
            self._h2 += data


def check_case_files(site):
    problems = []
    for slug in CASE_SLUGS:
        name = f"projects/{slug}.html"
        html = site.pages.get(name)
        if html is None:
            problems.append(f"{name}: missing")
            continue
        w = CaseWalker()
        w.feed(html)
        w.close()
        if not w.has_case:
            problems.append(f"{name}: no article.case-file")
        if w.h2s != CASE_SECTIONS:
            problems.append(f"{name}: h2 sections are {w.h2s}, expected {CASE_SECTIONS}")
        for img in w.imgs:
            for attr in ("alt", "width", "height"):
                if not img.get(attr):
                    problems.append(f"{name}: img {img.get('src')} lacks {attr}")
            if img.get("loading") != "lazy":
                problems.append(f"{name}: img {img.get('src')} lacks loading=lazy")
    return problems


SEVERITY = {"netguard": "CRIT", "minisiem": "CRIT", "cmmc-ready": "HIGH",
            "logingestllm": "HIGH", "ccna-study": "HIGH",
            "cysa-study": "HIGH", "job-tracker": "MED", "flight-tracker": "MED",
            "tempered": "MED", "sudo-snake": "MED"}


class SevWalker(HTMLParser):
    """Collects the text of every element carrying a data-severity attribute."""

    def __init__(self):
        super().__init__()
        self.tags, self._cur, self._depth = [], None, 0

    def handle_starttag(self, tag, attrs):
        if self._cur is not None and tag not in VOID:
            self._depth += 1
        elif "data-severity" in dict(attrs):
            self._cur, self._depth = {"attr": dict(attrs)["data-severity"], "text": ""}, 1

    def handle_endtag(self, tag):
        if self._cur is not None and tag not in VOID:
            self._depth -= 1
            if self._depth == 0:
                self.tags.append(self._cur)
                self._cur = None

    def handle_data(self, data):
        if self._cur is not None:
            self._cur["text"] += data


def check_severity(site):
    problems = []
    for slug, want in SEVERITY.items():
        name = f"projects/{slug}.html"
        if name not in site.pages:
            continue
        w = SevWalker()
        w.feed(site.pages[name])
        w.close()
        if len(w.tags) != 1:
            problems.append(f"{name}: expected exactly one severity tag, found {len(w.tags)}")
            continue
        text = w.tags[0]["text"].strip()
        if text != want or w.tags[0]["attr"] != want.lower():
            problems.append(f"{name}: severity tag is '{text}' (data-severity {w.tags[0]['attr']}), expected {want}")
        if "priority" in site.pages[name].lower():
            problems.append(f"{name}: contains the word 'priority'")
    return problems


class TermWalker(HTMLParser):
    """Finds .terminal, the text of its .term-output and the links in .term-chips."""

    def __init__(self):
        super().__init__()
        self.depth, self.out_depth, self.chip_depth = 0, 0, 0
        self.seen, self.output, self.chip_links = False, "", 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if self.depth and tag not in VOID:
            self.depth += 1
            if self.out_depth:
                self.out_depth += 1
            if self.chip_depth:
                self.chip_depth += 1
        elif "terminal" in classes and not self.seen:
            self.seen, self.depth = True, 1
        if self.depth:
            if "term-output" in classes and not self.out_depth:
                self.out_depth = 1
            if "term-chips" in classes and not self.chip_depth:
                self.chip_depth = 1
            if tag == "a" and self.chip_depth and a.get("href"):
                self.chip_links += 1

    def handle_endtag(self, tag):
        if self.depth and tag not in VOID:
            self.depth -= 1
            self.out_depth = max(0, self.out_depth - 1)
            self.chip_depth = max(0, self.chip_depth - 1)

    def handle_data(self, data):
        if self.out_depth:
            self.output += data


def check_terminal_fallback(site):
    html = site.pages.get("index.html", "")
    w = TermWalker()
    w.feed(html)
    w.close()
    if not w.seen:
        return ["index.html: no .terminal element"]
    problems = []
    for needle in ("Andrew T. Price II", "full-stack developer"):
        if needle not in w.output:
            problems.append(f"index.html: .term-output is missing '{needle}'")
    if w.chip_links < 5:
        problems.append(f"index.html: .term-chips has {w.chip_links} links, expected at least 5")
    return problems


def check_window_classes(site):
    css_path = site.root / "css" / "style.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""
    problems = []
    for name, html in site.pages.items():
        used = {c for _, a in walk(html).tags for c in (a.get("class") or "").split()
                if c.startswith(("window", "code-"))}
        problems += [f"{name}: class '{c}' has no rule in css/style.css"
                     for c in sorted(used) if f".{c}" not in css]
    return problems


class MissionWalker(HTMLParser):
    """Counts <li> items and collects the text inside #mission."""

    def __init__(self):
        super().__init__()
        self.depth, self.seen, self.items, self.text = 0, 0, 0, ""
        self.datetimes = []

    def handle_starttag(self, tag, attrs):
        if self.depth:
            if tag not in VOID:
                self.depth += 1
            self.items += tag == "li"
            if tag == "time":
                self.datetimes.append(dict(attrs).get("datetime") or "")
        elif dict(attrs).get("id") == "mission":
            self.seen += 1
            self.depth = 1

    def handle_endtag(self, tag):
        if self.depth and tag not in VOID:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.text += data


def check_mission(site):
    w = MissionWalker()
    w.feed(site.pages.get("index.html", ""))
    w.close()
    if w.seen != 1:
        return [f"index.html: expected one #mission section, found {w.seen}"]
    problems = []
    if w.items < 6:
        problems.append(f"index.html: #mission has {w.items} <li> items, expected at least 6")
    problems += [f"index.html: #mission is missing '{n}'"
                 for n in ("Hurlburt Field", "Kirtland AFB", "Creating Coding Careers", "Next")
                 if n not in w.text]
    problems += [f"index.html: #mission <time datetime=\"{d}\"> is not YYYY, YYYY-MM or YYYY-MM-DD"
                 for d in w.datetimes if not re.fullmatch(r"\d{4}(-\d{2}(-\d{2})?)?", d)]
    return problems


MAP_MAX_DEVICES = 16


class MapWalker(HTMLParser):
    """Collects hrefs of <a> inside #map's <svg> and .net-map-list."""

    def __init__(self):
        super().__init__()
        self.depth, self.seen, self.svgs, self.lists = 0, 0, 0, 0
        self.in_svg, self.in_list = 0, 0
        self.svg_hrefs, self.list_hrefs = [], []
        self.unlabelled, self.svg_labelled = 0, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self.depth:
            if tag not in VOID:
                self.depth += 1
            if tag == "svg":
                self.svgs += 1
                self.svg_labelled = bool((a.get("aria-labelledby") or "").strip() or (a.get("aria-label") or "").strip())
                self.in_svg = self.depth
            if tag == "ul" and "net-map-list" in (a.get("class") or "").split():
                self.lists += 1
                self.in_list = self.depth
            if tag == "a":
                if self.in_svg:
                    self.svg_hrefs.append(a.get("href") or "")
                    self.unlabelled += not (a.get("aria-label") or "").strip()
                if self.in_list:
                    self.list_hrefs.append(a.get("href") or "")
        elif a.get("id") == "map":
            self.seen += 1
            self.depth = 1

    def handle_endtag(self, tag):
        if self.depth and tag not in VOID:
            if self.in_svg == self.depth:
                self.in_svg = 0
            if self.in_list == self.depth:
                self.in_list = 0
            self.depth -= 1


def check_map(site):
    w = MapWalker()
    w.feed(site.pages.get("index.html", ""))
    w.close()
    if w.seen != 1:
        return [f"index.html: expected one #map section, found {w.seen}"]
    problems = []
    if w.svgs != 1:
        problems.append(f"index.html: #map has {w.svgs} <svg>, expected 1")
    if w.lists != 1:
        problems.append(f"index.html: #map has {w.lists} .net-map-list, expected 1")
    problems += [f"index.html: #map svg link '{h}' has no matching link in .net-map-list"
                 for h in w.svg_hrefs if h not in w.list_hrefs]
    problems += [f"index.html: #map list link '{h}' has no matching link in the svg"
                 for h in w.list_hrefs if h not in w.svg_hrefs]
    if not w.svg_labelled:
        problems.append("index.html: #map svg has no accessible name (aria-labelledby or aria-label)")
    if w.unlabelled:
        problems.append(f"index.html: #map has {w.unlabelled} svg link(s) without a non-empty aria-label")
    if len(w.svg_hrefs) != len(w.list_hrefs):
        problems.append(f"index.html: #map has {len(w.svg_hrefs)} svg links but {len(w.list_hrefs)} list links")
    if len(w.list_hrefs) > MAP_MAX_DEVICES:
        problems.append(f"index.html: #map has {len(w.list_hrefs)} devices, at most {MAP_MAX_DEVICES}")
    if not w.list_hrefs:
        problems.append("index.html: #map has no devices")
    return problems


QUEUE_FEATURED = {"NetGuard": "projects/netguard.html", "MiniSIEM": "projects/minisiem.html",
                  "CMMC Ready": "projects/cmmc-ready.html",
                  "LogIngestLLM": "projects/logingestllm.html",
                  "CySA+ Study": "projects/cysa-study.html", "CCNA Study": "projects/ccna-study.html",
                  "Job Tracker": "projects/job-tracker.html",
                  "Military Flight Tracker": "projects/flight-tracker.html",
                  "Tempered": "projects/tempered.html", "Sudo-Snake": "projects/sudo-snake.html"}
QUEUE_COURSEWORK = {"Card Scanner": "https://github.com/AndrewPrice98/Card-Scanner",
                    "Movie Finder": "https://github.com/AndrewPrice98/node101-movie-finder",
                    "Tic Tac Toe": "https://github.com/AndrewPrice98/React100-TicTacToe",
                    "San Diego Top Spots": "https://github.com/AndrewPrice98/SanDiegoTopSpots",
                    "Mortgage Calculator": "https://github.com/AndrewPrice98/React100MortgageCalc"}
# The home page shows only the top featured rows, so a recruiter can scan it;
# portfolio.html lists every project.
QUEUE_HOME = ["NetGuard", "MiniSIEM", "CMMC Ready", "LogIngestLLM", "CySA+ Study",
              "CCNA Study", "Job Tracker", "Military Flight Tracker"]
QUEUE_HOME_MAX = 8
QUEUE_SEVERITIES = {"crit", "high", "med", "info"}


class QueueWalker(HTMLParser):
    """Collects each li.alert-row inside an .alert-queue: its attributes, first link and title."""

    def __init__(self):
        super().__init__()
        self.queues, self.rows = 0, []
        self.in_row, self.in_title, self.depth = False, False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        if "alert-queue" in cls:
            self.queues += 1
        if tag == "li" and "alert-row" in cls:
            self.in_row, self.depth = True, 1
            self.rows.append({"sev": a.get("data-severity"), "cat": a.get("data-category"),
                              "href": None, "title": ""})
            return
        if not self.in_row:
            return
        if tag not in VOID:
            self.depth += 1
        if tag == "a" and self.rows[-1]["href"] is None:
            self.rows[-1]["href"] = a.get("href") or ""
        if "row-title" in cls:
            self.in_title = True

    def handle_endtag(self, tag):
        if self.in_row and tag not in VOID:
            self.depth -= 1
            self.in_title = False
            if self.depth == 0:
                self.in_row = False

    def handle_data(self, data):
        if self.in_title:
            self.rows[-1]["title"] += data


def check_queue(site):
    problems = []
    for name in ("index.html", "portfolio.html"):
        w = QueueWalker()
        w.feed(site.pages.get(name, ""))
        w.close()
        if w.queues != 1:
            problems.append(f"{name}: expected one .alert-queue, found {w.queues}")
            continue
        titles = {}
        for r in w.rows:
            r["title"] = " ".join(r["title"].replace("↗", "").replace("(opens GitHub in a new tab)", "").split())
            titles[r["title"]] = r
            if r["sev"] not in QUEUE_SEVERITIES:
                problems.append(f"{name}: queue row '{r['title']}' has data-severity '{r['sev']}'")
            if not r["href"]:
                problems.append(f"{name}: queue row '{r['title']}' has no link")
        if len(titles) != len(w.rows):
            problems.append(f"{name}: queue has duplicate row titles")
        if name == "index.html":
            want = set(QUEUE_HOME)
            if [r["title"] for r in w.rows] != QUEUE_HOME:
                problems.append(f"{name}: queue rows are {[r['title'] for r in w.rows]}, expected {QUEUE_HOME} in that order")
        else:
            want = set(QUEUE_FEATURED) | set(QUEUE_COURSEWORK)
        if set(titles) != want:
            problems.append(f"{name}: queue rows differ: missing {sorted(want - set(titles))}, unexpected {sorted(set(titles) - want)}")
        for t, href in QUEUE_FEATURED.items():
            if t in titles and titles[t]["href"] != href:
                problems.append(f"{name}: queue row '{t}' links to '{titles[t]['href']}', expected {href}")
        for t, href in QUEUE_COURSEWORK.items():
            if name == "portfolio.html" and t in titles:
                if titles[t]["sev"] != "info":
                    problems.append(f"{name}: queue row '{t}' is not info")
                if titles[t]["href"] != href:
                    problems.append(f"{name}: queue row '{t}' links to '{titles[t]['href']}', expected {href}")
        html = site.pages[name]
        if 'class="alert-queue" role="list"' not in html:
            problems.append(f"{name}: .alert-queue must be <ul role=\"list\">")
        if 'id="queue-status"' not in html:
            problems.append(f"{name}: no #queue-status live region")
        for tag, a in walk(html).tags:
            if tag == "a" and "aria-labelledby" in a and a.get("aria-labelledby", "").startswith("rt-"):
                for attr, pre in (("aria-labelledby", "rt-"), ("aria-describedby", "rs-")):
                    ref = a.get(attr, "")
                    if not ref.startswith(pre) or f'id="{ref}"' not in html:
                        problems.append(f"{name}: queue link {a.get('href')} {attr}='{ref}' has no matching id")
        if name == "portfolio.html" and html.count("(opens GitHub in a new tab)") != len(QUEUE_COURSEWORK):
            problems.append(f"{name}: coursework rows need an '(opens GitHub in a new tab)' hint")
        if name == "index.html" and 'class="queue-filters"' not in site.pages[name]:
            problems.append("index.html: no .queue-filters")
        if name == "index.html" and not any(tag == "a" and "queue-more" in (a.get("class") or "").split()
                                            and a.get("href") == "portfolio.html" for tag, a in walk(html).tags):
            problems.append("index.html: no a.queue-more link to portfolio.html after the queue")
    if len(QUEUE_HOME) > QUEUE_HOME_MAX or not set(QUEUE_HOME) <= set(QUEUE_FEATURED):
        problems.append(f"check_site.py: QUEUE_HOME must be at most {QUEUE_HOME_MAX} titles from QUEUE_FEATURED")
    return problems


def check_terminal_projects(site):
    js_path = site.root / "js" / "terminal.js"
    js = js_path.read_text(encoding="utf-8") if js_path.exists() else ""
    m = re.search(r"var PROJECTS = \[(.*?)\n\s*\];", js, re.S)
    slugs = re.findall(r"\['([a-z0-9-]+)',", m.group(1)) if m else []
    if sorted(slugs) != sorted(CASE_SLUGS):
        return [f"js/terminal.js: PROJECTS slugs {slugs} differ from CASE_SLUGS {CASE_SLUGS}"]
    return []


CHECKS = [check_balanced, check_links, check_no_empty_links,
          check_nav, check_fast_lane, check_titles, check_case_files,
          check_severity, check_terminal_fallback, check_window_classes, check_mission, check_map, check_queue,
          check_terminal_projects]


def main(argv):
    if len(argv) != 2:
        print("usage: check_site.py <site-dir>")
        return 2
    site = Site(argv[1])
    problems = [p for check in CHECKS for p in check(site)]
    print("\n".join(problems))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
