# Modern Community Topics

A local-first daily briefing app that turns RSS/news feeds into short regional bullet points.

## What It Does

- Pulls configured feeds for local, provincial, national, world, and New Zealand news.
- Adds an Esquimalt lane for Township notices and civic updates.
- Builds a Government tab with federal bill tracking, BC Legislature links, and Esquimalt meeting/agendas.
- Scores likely important stories using recency, civic-impact keywords, and source weighting.
- Writes a browser-friendly briefing to `data/latest.json`.
- Writes government tracking data to `data/government.json`.
- Generates `data/digest.md` and `data/digest.html` for email or quick reading.
- Lets you click a bullet in the web app to see context and related source links.

## Quick Start

```bash
python3 scripts/fetch_news.py
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/web/
```

## Daily Use

Run this whenever you want a fresh briefing:

```bash
python3 scripts/fetch_news.py --days 3 --limit-per-section 8
```

The source list lives in `config/sources.json`.

## Government Roundup

The app has a `Government` tab with:

- Federal bill tracking from LEGISinfo
- BC Legislature progress-of-bills official tracker
- Esquimalt Council and committee meeting dates from Legistar
- A `Policy Watch` band for affordability, housing, war/security, health, public safety, climate/infrastructure, and local civic decisions
- `Most Relevant`, `Became Law`, and `Stopped or Stalled` buckets when parsed status data is available

If an official site blocks or times out during refresh, the app keeps an official tracker link in place instead of showing a blank section.

Government importance is scored transparently. Items are prioritized when they are near passage, recently active, or touch high-impact areas such as budgets, taxes, housing, health, public safety, rights, environment, labour, or Indigenous affairs. The app shows the reason on each summary card.

## Esquimalt Sources

The Esquimalt lane blends official civic notices with filtered regional reporting:

- Township of Esquimalt official notices
- CHEK News
- Victoria News
- Lookout, the CFB Esquimalt newspaper

Regional feeds are filtered for Esquimalt and nearby civic/naval terms so the section does not become a generic Victoria feed.

## Sports

The app has a `Sports` tab with:

- Official score and fixture links for the World Cup, Champions League, and Premier League
- Football headlines from BBC Football, The Guardian Football, and ESPN Soccer

The score cards link to official match centres rather than scraped scores, which keeps the app stable when league sites change their markup.

## Automatic Twice-Daily Refresh

On macOS, install the background schedule with:

```bash
chmod +x scripts/install_scheduler.sh scripts/uninstall_scheduler.sh scripts/run_briefing.sh
scripts/install_scheduler.sh
```

That installs a user `launchd` job that refreshes the briefing at:

- 8:00 AM
- 5:00 PM

It also runs once immediately after installation.

The scheduled job updates:

- `data/latest.json`
- `data/digest.md`
- `data/digest.html`

You do not need Codex, Terminal, or the browser app open for the refresh to happen. Your Mac does need to be on and you need to be logged in.

To remove the schedule:

```bash
scripts/uninstall_scheduler.sh
```

Logs are written to:

```text
data/scheduler.out.log
data/scheduler.err.log
```

## Viewing It

The scheduled refresh job only refreshes the data. To read the interactive app, start the local web server:

```bash
python3 -m http.server 8080
```

Then open:

```text
http://localhost:8080/web/
```

If you leave the page open, it checks for fresh data every 15 minutes.

For a no-server view, open `data/digest.html` directly in a browser.

## iPhone And Household Sharing

On the same Wi-Fi network, open this from an iPhone or another household device:

```text
http://192.168.68.53:8080/web/
```

On iPhone, use Safari's Share button and choose `Add to Home Screen`.

To make the web server start automatically when you log in:

```bash
chmod +x scripts/install_server.sh scripts/uninstall_server.sh scripts/run_server.sh
scripts/install_server.sh
```

The Mac must be awake and connected to Wi-Fi for household devices to reach it.

To remove the auto-start server:

```bash
scripts/uninstall_server.sh
```

For access away from home, use a private network tool such as Tailscale, or publish the generated static files to a private hosted page. Avoid exposing the raw local server directly to the public internet.

## Travel Access With GitHub Pages

For access when your Mac is off, publish the static app to GitHub Pages. This repo includes a GitHub Actions workflow at:

```text
.github/workflows/pages.yml
```

The workflow:

- runs `scripts/fetch_news.py`
- builds a clean static site with `scripts/build_pages_site.py`
- deploys `web/`, `data/`, and `assets/` to GitHub Pages
- runs manually from GitHub Actions or on a twice-daily UTC schedule

In GitHub, enable Pages with:

```text
Settings -> Pages -> Build and deployment -> Source: GitHub Actions
```

After the first successful run, open the GitHub Pages URL on iPhone Safari and choose `Add to Home Screen`.

GitHub Pages is free for public repositories on GitHub Free. Private repository Pages may require a paid GitHub plan. If the site should not be public, use Cloudflare Access, a private host, or another password-protected deployment path.

## Dock App

This project includes a small macOS app launcher:

```text
Modern Community Topics.app
```

Double-click it to start the local web server if needed and open:

```text
https://bbmn.github.io/modern-community-topics/web/
```

To keep it in the Dock, drag `Modern Community Topics.app` onto the Dock. The app is only a launcher, so it opens the published briefing and then exits. For local development, use the localhost server commands above.

Server logs are written to:

```text
data/server.out.log
data/server.err.log
```

## Email Path

For now, the script generates an email-ready file at `data/digest.html`. The next step would be wiring that into either:

- Apple Mail / macOS automation
- Gmail SMTP
- Mailgun, Resend, or another transactional email service
- A scheduled local job that runs each morning

## Notes

Some publishers change or block RSS feeds. If one feed fails, the script records the error and keeps going.
