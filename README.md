# Publisher Website Info Checker (BlogReach)

A small Python web tool: enter any website URL and see its homepage basics.

Built for the BlogReach.com ZR-26-00741 task sheet (Zeshan Sarwar).

## What it does

Given a website URL, the tool fetches the homepage and shows:

- Page title (as search engines see it)
- Meta description
- Whether the site serves over HTTPS (checked after redirects)
- Measured homepage load time, in seconds
- Number of links on the homepage

Invalid or unreachable URLs get a clear, plain-English error message
instead of a crash or a traceback.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # optional
python app.py
```

Then open http://localhost:5000 in a browser.

### Configuration (.env)

| Variable            | Default   | Meaning                              |
|---------------------|-----------|--------------------------------------|
| CHECKER_TIMEOUT     | 10        | Seconds to wait for a site to respond |
| CHECKER_MAX_BYTES   | 2097152   | Max homepage bytes to download        |
| PORT                | 5000      | Local dev port                        |

## How I tested it

19 automated tests in `tests/test_checker.py`, run with:

```bash
pytest tests/ -q
```

Coverage:

- URL normalization: missing scheme gets `https://`, explicit `http://`
  kept, whitespace stripped, empty input / bad scheme / spaces /
  bare words rejected with `InvalidURLError`
- `check_website` with mocked HTTP responses: title, meta description,
  and link count extraction (only `<a>` tags with `href` count),
  HTTPS detection after redirects, load-time measurement,
  HTTP error statuses, connection errors, and timeouts
- Flask routes: index page loads, invalid URLs show the error banner,
  valid URLs render the results card, unreachable sites show the
  friendly error

The live deployment was also tested by hand with real URLs
(blogreach.com and example.com).

## Limitations

- Only the homepage is fetched, and at most ~2 MB of it; very large
  pages are cut off after the cap.
- JavaScript-rendered content is not executed: the tool reads the raw
  HTML the server returns, so single-page apps may show little data.
- Load time is measured from the server running the tool, not from
  the visitor's browser, and it covers the HTML document only
  (not images, fonts, or scripts).
- Link count counts `<a href>` elements in the raw HTML, including
  navigation, footer, and duplicate links.
- Sites that block bots or require login will come back as unreachable.

## Deploy

The app is stateless and runs on Vercel (Flask). Pushing to `main`
redeploys automatically.
