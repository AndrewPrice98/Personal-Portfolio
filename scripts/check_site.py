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


CHECKS = [check_balanced, check_links, check_no_empty_links]


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
