# Portfolio

Andrew T. Price II's portfolio: plain HTML, CSS and a little vanilla JavaScript, no framework and no build step. Every page reads fine with JavaScript off.

## Files

Everything the site serves is in [`public/`](public/):

| File | What it is |
|---|---|
| `index.html` | Home: terminal hero, mission log, network map, project queue |
| `portfolio.html` | Projects page: the full queue, including coursework |
| `resume.html` | Resume, with the PDF embedded and a download link |
| `contact.html` | Contact links |
| `404.html` | Shown for any page that doesn't exist (uses `/Personal-Portfolio/` paths, so it only renders correctly on GitHub Pages) |
| `projects/*.html` | One case file per featured project |
| `css/style.css` | Styles for every page |
| `js/terminal.js` | Typing animation and commands in the home page terminal (skipped under reduced motion) |
| `js/queue.js` | Category filter buttons for the project queue |
| `images/` | Project screenshots; `images/cases/` holds the case-file figures |
| `files/` | The resume PDF |

Outside `public/`:

| File | What it is |
|---|---|
| `scripts/check_site.py` | Site checker: balanced HTML, links, nav, fast lane, case-file sections, queue rows |
| `.github/workflows/pages.yml` | Publishes `public/` to GitHub Pages |

To preview, serve `public/` (for example `py -3 -m http.server 5191 --directory public`) and open `http://localhost:5191/`.

## Checking

```
py -3 -I scripts/check_site.py public
```

Prints one line per problem and exits 1, or exits 0 when the site is clean.

## Editing

- **Add a project:**
  1. Copy an existing case file in `public/projects/` (for example `netguard.html`) to `public/projects/<slug>.html` and rewrite it. Keep the same seven sections (Summary, Problem, What I built, How it works, Evidence, What I'd do next, Links), the single `data-severity` tag, and `alt`, `width`, `height` and `loading="lazy"` on every image.
  2. Copy an `<li class="alert-row">` block into the queue on `portfolio.html`, and into `index.html` too if it is featured. Set `data-severity` (`crit`, `high`, `med` or `info`), `data-category`, the link, the title, the summary and the tags. Give the title and summary spans unique `id`s (`rt-<slug>`, `rs-<slug>`) and point the link's `aria-labelledby` and `aria-describedby` at them.
  3. Add the project to the expected lists in `scripts/check_site.py` (`CASE_SLUGS`, `SEVERITY`, `QUEUE_FEATURED` or `QUEUE_COURSEWORK`) and run the checker.
- **Header, fast lane and footer** are repeated in each HTML file, so change them in every file.

## Deploy

GitHub Pages publishes `public/` on every push to `main` (workflow `.github/workflows/pages.yml`).
