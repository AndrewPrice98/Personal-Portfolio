"""Check the static site. Usage: python -I scripts/check_site.py public

Exits 0 when clean, otherwise 1 with one line per problem: "<file>: <problem>".
Standard library only. Add a check by writing check_x(site) -> list[str]
and appending it to CHECKS.
"""
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


def check_links(site):
    problems = []
    for name, html in site.pages.items():
        for tag, attrs in walk(html).tags:
            for attr in ("href", "src"):
                url = attrs.get(attr)
                if not url or url.startswith(("#", "http:", "https:", "mailto:")):
                    continue
                path = url.split("#")[0].split("?")[0]
                if not path:
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
        self.fl_depth, self.fl_text, self.fl_classes = 0, "", []
        self.fl_seen = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "nav":
            self.nav_depth += 1
        if tag == "a" and self.nav_depth:
            self._link = ""
        if tag == "title":
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


CASE_SLUGS = ["netguard", "logingestllm", "ccna-study", "cysa-study",
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


SEVERITY = {"netguard": "CRIT", "logingestllm": "HIGH", "ccna-study": "HIGH",
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


CHECKS = [check_balanced, check_links, check_no_empty_links,
          check_nav, check_fast_lane, check_titles, check_case_files,
          check_severity]


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
