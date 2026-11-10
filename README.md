# Portfolio

My personal portfolio site: plain HTML and CSS, no build step.

## Files

Everything the site serves is in [`public/`](public/):

| File | Page |
|---|---|
| `index.html` | Home |
| `portfolio.html` | All projects |
| `contact.html` | Contact links |
| `404.html` | Shown for any page that doesn't exist |
| `css/style.css` | Styles for every page |
| `js/main.js` | Typing animation on the home page heading |

To preview, open `public/index.html` in a browser.

## Editing

- **Add a project:** copy an `<article class="card">...</article>` block in `portfolio.html` and change the text and links. To feature it on the home page, paste a copy into `index.html` too.
- **Header and footer** are repeated in each HTML file, so change them in every file.

## Deploy

GitHub Pages publishes `public/` on every push to `main` (workflow `.github/workflows/pages.yml`).
