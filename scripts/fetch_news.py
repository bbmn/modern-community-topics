#!/usr/bin/env python3
from __future__ import annotations
import argparse
import email.utils
import html
import json
import re
import subprocess
import sys
import textwrap
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "sources.json"
DATA_DIR = ROOT / "data"

IMPORTANT_TERMS = {
    "announces": 1.4,
    "budget": 2.0,
    "cabinet": 1.7,
    "climate": 1.2,
    "council": 1.8,
    "court": 1.6,
    "deadline": 1.4,
    "decision": 2.2,
    "draft": 1.2,
    "election": 2.1,
    "evacuation": 2.0,
    "federal": 1.6,
    "finals": 1.4,
    "fire": 1.5,
    "free agency": 1.7,
    "funding": 1.8,
    "government": 1.7,
    "health": 1.6,
    "hearing": 1.5,
    "housing": 1.9,
    "inquiry": 1.6,
    "minister": 1.8,
    "parliament": 1.8,
    "policy": 1.7,
    "premier": 1.9,
    "province": 1.5,
    "public": 1.2,
    "rates": 1.5,
    "school": 1.3,
    "strike": 1.7,
    "tariff": 1.6,
    "transit": 1.6,
    "trial": 1.5,
    "trade": 1.9,
    "trades": 1.9,
    "vote": 1.8,
    "warning": 1.6,
    "wildfire": 2.2
}

GOVERNMENT_IMPACT_TERMS = {
    "appropriation": ("Public spending", 5),
    "budget": ("Public spending", 5),
    "tax": ("Taxes", 5),
    "housing": ("Housing", 5),
    "health": ("Health", 5),
    "criminal": ("Justice", 4),
    "safety": ("Public safety", 4),
    "citizenship": ("Citizenship", 4),
    "immigration": ("Immigration", 4),
    "environment": ("Environment", 4),
    "climate": ("Climate", 4),
    "energy": ("Energy", 4),
    "transport": ("Transportation", 3),
    "labour": ("Work", 3),
    "employment": ("Work", 3),
    "privacy": ("Privacy", 4),
    "security": ("Security", 4),
    "trade": ("Trade", 3),
    "indigenous": ("Indigenous affairs", 4),
    "first nation": ("Indigenous affairs", 4),
    "school": ("Education", 3),
    "education": ("Education", 3),
    "disability": ("Disability", 4),
    "benefit": ("Benefits", 4)
}

POLICY_WATCH_TERMS = {
    "Affordability": [
        "affordability", "grocery", "groceries", "rent", "rental", "mortgage",
        "cost of living", "property tax", "tax", "benefit", "rebate", "income"
    ],
    "Housing": [
        "housing", "homeless", "shelter", "zoning", "development", "tenant",
        "eviction", "short-term rental"
    ],
    "War & Security": [
        "ukraine", "russia", "war", "defence", "defense", "military", "nato",
        "security", "border", "iran", "gaza", "israel", "ceasefire"
    ],
    "Public Safety": [
        "police", "crime", "court", "bail", "drug", "overdose", "wildfire",
        "emergency", "warning", "evacuation"
    ],
    "Health": [
        "health", "hospital", "doctor", "nurse", "mental health", "addiction",
        "disability"
    ],
    "Climate & Infrastructure": [
        "climate", "transit", "transport", "infrastructure", "water",
        "wastewater", "energy", "emissions", "ferry"
    ],
    "Local Decisions": [
        "council", "committee", "bylaw", "public notice", "hearing",
        "annual report", "licence", "license", "budget"
    ]
}

STOP_WORDS = {
    "about", "after", "again", "against", "being", "could", "from", "have",
    "into", "more", "over", "that", "their", "there", "this", "with", "would",
    "says", "said", "will", "news", "latest", "update", "updates", "canada",
    "canadian", "british", "columbia", "victoria", "vancouver", "people",
    "official", "officials", "government", "minister", "province", "public",
    "june", "today", "amid", "after", "before", "during"
}


@dataclass
class FeedResult:
    items: list[dict[str, Any]]
    errors: list[str]


class BCGovNewsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.items: list[dict[str, str]] = []
        self._in_h2 = False
        self._in_anchor = False
        self._href = ""
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {name: value or "" for name, value in attrs}
        if tag == "h2":
            self._in_h2 = True
        if self._in_h2 and tag == "a":
            self._in_anchor = True
            self._href = attrs_dict.get("href", "")
            self._title_parts = []

    def handle_data(self, data: str) -> None:
        if self._in_anchor:
            self._title_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._in_anchor:
            title = strip_tags(" ".join(self._title_parts))
            href = self._href
            if title and href and "/releases/" in href:
                self.items.append({"title": title, "url": href})
            self._in_anchor = False
            self._href = ""
            self._title_parts = []
        if tag == "h2":
            self._in_h2 = False


class LinkTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.text_parts: list[str] = []
        self._href = ""
        self._link_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attrs_dict = {name: value or "" for name, value in attrs}
            self._href = attrs_dict.get("href", "")
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        value = data.strip()
        if value:
            self.text_parts.append(value)
        if self._href:
            self._link_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            text = strip_tags(" ".join(self._link_parts))
            if text:
                self.links.append({"text": text, "href": self._href})
            self._href = ""
            self._link_parts = []

    def text(self) -> str:
        return strip_tags(" ".join(self.text_parts))


def text_of(node: ET.Element | None, tag: str, namespaces: dict[str, str]) -> str:
    if node is None:
        return ""
    found = node.find(tag, namespaces)
    if found is None or found.text is None:
        return ""
    return html.unescape(found.text).strip()


def strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = re.sub(r"\s+", " ", value)
    return html.unescape(value).strip()


def trim_excerpt(value: str, limit: int = 700) -> str:
    value = strip_tags(value)
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].strip()
    return f"{clipped}..."


def parse_date(value: str) -> str:
    if not value:
        return ""
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat()
        except ValueError:
            return ""


def fetch_url(url: str, timeout: int = 8) -> bytes:
    result = subprocess.run(
        [
            "/usr/bin/curl",
            "--location",
            "--silent",
            "--show-error",
            "--fail",
            "--max-time",
            str(timeout),
            "--user-agent",
            "ModernCommunityTopics/0.1 (+local personal news digest)",
            url
        ],
        check=True,
        capture_output=True,
        timeout=timeout + 2
    )
    return result.stdout


def parse_feed(xml_bytes: bytes, section: dict[str, Any], feed: dict[str, Any]) -> list[dict[str, Any]]:
    if feed.get("type") == "bcgov_html":
        return parse_bcgov_html(xml_bytes, section, feed)
    if feed.get("type") == "esquimalt_home":
        return parse_esquimalt_home(html_bytes=xml_bytes, section=section, feed=feed)
    if feed.get("type") == "official_news_html":
        return parse_official_news_html(html_bytes=xml_bytes, section=section, feed=feed)

    root = ET.fromstring(xml_bytes)
    namespaces = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[dict[str, Any]] = []

    rss_items = root.findall(".//item")
    atom_items = root.findall(".//atom:entry", namespaces)

    for item in rss_items:
        title = text_of(item, "title", namespaces)
        link = text_of(item, "link", namespaces)
        description = strip_tags(text_of(item, "description", namespaces))
        published = parse_date(text_of(item, "pubDate", namespaces))
        guid = text_of(item, "guid", namespaces) or link or title
        if title and link:
            built = build_item(section, feed, guid, title, link, description, published)
            if should_include_item(feed, built):
                items.append(built)

    for item in atom_items:
        title = text_of(item, "atom:title", namespaces)
        link_node = item.find("atom:link", namespaces)
        link = link_node.attrib.get("href", "") if link_node is not None else ""
        description = strip_tags(text_of(item, "atom:summary", namespaces) or text_of(item, "atom:content", namespaces))
        published = parse_date(text_of(item, "atom:published", namespaces) or text_of(item, "atom:updated", namespaces))
        guid = text_of(item, "atom:id", namespaces) or link or title
        if title and link:
            built = build_item(section, feed, guid, title, link, description, published)
            if should_include_item(feed, built):
                items.append(built)

    return items


def should_include_item(feed: dict[str, Any], item: dict[str, Any]) -> bool:
    include_any = [term.lower() for term in feed.get("includeAny", [])]
    if not include_any:
        return True
    haystack = f"{item['title']} {item['description']}".lower()
    return any(term in haystack for term in include_any)


def parse_bcgov_html(html_bytes: bytes, section: dict[str, Any], feed: dict[str, Any]) -> list[dict[str, Any]]:
    parser = BCGovNewsParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    items = []
    for raw in parser.items[:20]:
        url = raw["url"]
        if url.startswith("/"):
            url = f"https://news.gov.bc.ca{url}"
        items.append(build_item(
            section,
            feed,
            url,
            raw["title"],
            url,
            "Government of British Columbia release.",
            ""
        ))
    return items


def parse_esquimalt_home(html_bytes: bytes, section: dict[str, Any], feed: dict[str, Any]) -> list[dict[str, Any]]:
    parser = LinkTextParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    items = []
    seen: set[str] = set()
    for link in parser.links:
        href = absolute_url(link["href"], "https://www.esquimalt.ca")
        title = link["text"]
        if not title or href in seen:
            continue
        title_lower = title.lower()
        is_notice = (
            "news-public-notices" in href
            or title_lower.startswith("notice of")
            or title_lower.startswith("public notice")
            or title_lower.startswith("call for")
        )
        if not is_notice:
            continue
        seen.add(href)
        items.append(build_item(
            section,
            feed,
            href,
            title,
            href,
            "Township of Esquimalt notice or civic update.",
            ""
        ))
        if len(items) >= 10:
            break
    return items


def parse_official_news_html(html_bytes: bytes, section: dict[str, Any], feed: dict[str, Any]) -> list[dict[str, Any]]:
    parser = LinkTextParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    items = []
    seen: set[str] = set()
    base_url = feed.get("baseUrl", feed["url"])
    include_href_any = [value.lower() for value in feed.get("includeHrefAny", [])]
    blocked_titles = {"news", "subscribe", "sign up", "alerts", "public notices"}

    for link in parser.links:
        title = strip_tags(link["text"])
        href = absolute_url(link["href"], base_url)
        href_lower = href.lower()
        if not title or href in seen:
            continue
        if title.lower() in blocked_titles or title.lower().startswith("page "):
            continue
        if include_href_any and not any(value in href_lower for value in include_href_any):
            continue
        seen.add(href)
        items.append(build_item(
            section,
            feed,
            href,
            title,
            href,
            f"{feed['name']} official news update.",
            ""
        ))
        if len(items) >= 8:
            break
    return items


def build_item(
    section: dict[str, Any],
    feed: dict[str, Any],
    guid: str,
    title: str,
    link: str,
    description: str,
    published: str
) -> dict[str, Any]:
    title = strip_tags(title)
    description = trim_excerpt(description)
    score = score_item(title, description, published, float(feed.get("weight", 1.0)))
    return {
        "id": stable_id(guid),
        "section": section["id"],
        "sectionName": section["name"],
        "focus": section.get("focus", ""),
        "source": feed["name"],
        "title": title,
        "bullet": make_bullet(title, feed["name"], published),
        "description": description,
        "url": link,
        "published": published,
        "score": score,
        "keywords": keywords_for(title + " " + description)
    }


def stable_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return cleaned[:80] or "story"


def keywords_for(value: str) -> list[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", value.lower())
    return sorted({word for word in words if word not in STOP_WORDS and len(word) >= 5})[:24]


def score_item(title: str, description: str, published: str, source_weight: float) -> float:
    body = f"{title} {description}".lower()
    score = 1.0 * source_weight
    for term, weight in IMPORTANT_TERMS.items():
        if re.search(rf"\b{re.escape(term)}\b", body):
            score += weight
    if published:
        try:
            age_hours = (datetime.now(timezone.utc) - datetime.fromisoformat(published)).total_seconds() / 3600
            score += max(0, 3.0 - age_hours / 18)
        except ValueError:
            pass
    return round(score, 3)


def make_bullet(title: str, source: str, published: str) -> str:
    date_hint = ""
    if published:
        try:
            date_hint = datetime.fromisoformat(published).strftime("%b %-d")
        except ValueError:
            date_hint = ""
    suffix = f" ({source}{', ' + date_hint if date_hint else ''})"
    return f"{title}{suffix}"


def load_items(config: dict[str, Any]) -> FeedResult:
    all_items: list[dict[str, Any]] = []
    errors: list[str] = []
    for section in config["sections"]:
        for feed in section["feeds"]:
            try:
                xml_bytes = fetch_url(feed["url"])
                all_items.extend(parse_feed(xml_bytes, section, feed))
            except (ET.ParseError, urllib.error.URLError, TimeoutError, OSError, subprocess.SubprocessError) as exc:
                errors.append(f"{feed['name']}: {describe_fetch_error(exc)}")
    return FeedResult(items=all_items, errors=errors)


def load_government(config: dict[str, Any]) -> dict[str, Any]:
    sections = []
    errors = []
    for section in config.get("government", []):
        source = section["source"]
        try:
            if source.get("type") == "manual_items":
                items = parse_manual_government_items(section, source)
            else:
                html_bytes = fetch_url(source["url"])
                items = parse_government_source(html_bytes, section, source)
        except (ET.ParseError, urllib.error.URLError, TimeoutError, OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{source['name']}: {describe_fetch_error(exc)}")
            items = official_tracker_item(section, source, "Official tracker unavailable during this refresh.")
        sections.append({
            "id": section["id"],
            "name": section["name"],
            "focus": section.get("focus", ""),
            "source": source["name"],
            "sourceUrl": source.get("url", ""),
            "items": items
        })
    return {"sections": sections, "highlights": summarize_government(sections), "errors": errors}


def load_sports(config: dict[str, Any], days: int, limit: int) -> dict[str, Any]:
    sports_config = config.get("sports", {})
    default_section = {
        "id": "sports-news",
        "name": "Sports News",
        "focus": "Most relevant sports headlines"
    }
    items: list[dict[str, Any]] = []
    errors = []
    for feed in sports_config.get("feeds", []):
        feed_section = {
            "id": feed.get("sectionId", default_section["id"]),
            "name": feed.get("sectionName", default_section["name"]),
            "focus": feed.get("sectionFocus", default_section["focus"])
        }
        try:
            xml_bytes = fetch_url(feed["url"])
            items.extend(parse_feed(xml_bytes, feed_section, feed))
        except (ET.ParseError, urllib.error.URLError, TimeoutError, OSError, subprocess.SubprocessError) as exc:
            errors.append(f"{feed['name']}: {describe_fetch_error(exc)}")
    items = filter_recent(dedupe(items), days)
    items.sort(key=lambda row: row["score"], reverse=True)
    scoreboards = []
    for row in sports_config.get("scoreboards", []):
        matches: list[dict[str, str]] = []
        if row.get("scoreApi"):
            try:
                matches = parse_espn_scoreboard(fetch_url(row["scoreApi"]))
            except (json.JSONDecodeError, urllib.error.URLError, TimeoutError, OSError, subprocess.SubprocessError) as exc:
                errors.append(f"{row['name']} scores: {describe_fetch_error(exc)}")
        scoreboards.append({
            "id": stable_id(f"sports-{row['id']}"),
            "title": row["name"],
            "status": row["status"],
            "description": row["description"],
            "url": row["url"],
            "source": row["source"],
            "scoreSource": "ESPN",
            "matches": matches[:8]
        })
    news_sections = sports_config.get("newsSections") or [default_section]
    sections = []
    for news_section in news_sections:
        section_items = [item for item in items if item["section"] == news_section["id"]]
        section_items.sort(key=lambda row: row["score"], reverse=True)
        sections.append({
            "id": news_section["id"],
            "name": news_section["name"],
            "focus": news_section.get("focus", ""),
            "items": section_items[:limit]
        })
    return {
        "scoreboards": scoreboards,
        "sections": sections,
        "errors": errors
    }


def parse_espn_scoreboard(json_bytes: bytes) -> list[dict[str, str]]:
    data = json.loads(json_bytes.decode("utf-8"))
    matches = []
    for event in data.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        competitors = competition.get("competitors") or []
        if len(competitors) < 2:
            continue

        home = next((team for team in competitors if team.get("homeAway") == "home"), competitors[0])
        away = next((team for team in competitors if team.get("homeAway") == "away"), competitors[1])
        status_type = (competition.get("status") or event.get("status") or {}).get("type", {})
        state = status_type.get("state", "")
        short_status = status_type.get("shortDetail") or status_type.get("detail") or status_type.get("description") or ""
        match_date = parse_date(event.get("date", ""))
        home_name = team_name(home)
        away_name = team_name(away)

        if state in {"in", "post"}:
            text = f"{home_name} {home.get('score', '0')}-{away.get('score', '0')} {away_name}"
            if short_status:
                text = f"{text} ({short_status})"
            match_day = format_match_day(match_date)
            summary = event_note(competition)
            note = f"{match_day}: {summary}" if match_day and summary else match_day or summary
        else:
            kickoff = format_match_time(match_date)
            text = f"{home_name} vs {away_name}"
            note = " / ".join(
                piece for piece in [kickoff, event_note(competition), series_note(competition)] if piece
            ) or short_status

        matches.append({
            "id": stable_id(f"{event.get('id', '')}-{home_name}-{away_name}"),
            "text": text,
            "note": note,
            "date": match_date,
            "url": event_url(event) or ""
        })
    matches.sort(key=lambda row: row.get("date") or "")
    return matches


def team_name(competitor: dict[str, Any]) -> str:
    team = competitor.get("team", {})
    return team.get("shortDisplayName") or team.get("displayName") or team.get("name") or "TBD"


def event_note(competition: dict[str, Any]) -> str:
    notes = competition.get("notes") or []
    if notes:
        return notes[0].get("headline") or notes[0].get("text") or ""
    headlines = competition.get("headlines") or []
    if headlines:
        return headlines[0].get("shortLinkText") or headlines[0].get("description") or ""
    return ""


def series_note(competition: dict[str, Any]) -> str:
    series = competition.get("series") or {}
    return series.get("summary", "")


def event_url(event: dict[str, Any]) -> str:
    for link in event.get("links", []):
        rel = link.get("rel") or []
        if "summary" in rel and link.get("href"):
            return link["href"]
    links = event.get("links") or []
    return links[0].get("href", "") if links else ""


def format_match_time(value: str) -> str:
    if not value:
        return ""
    try:
        when = datetime.fromisoformat(value).astimezone()
    except ValueError:
        return ""
    return when.strftime("%a %-I:%M %p")


def format_match_day(value: str) -> str:
    if not value:
        return ""
    try:
        when = datetime.fromisoformat(value).astimezone()
    except ValueError:
        return ""
    return when.strftime("%b %-d")


def describe_fetch_error(exc: BaseException) -> str:
    if isinstance(exc, subprocess.TimeoutExpired):
        return "timed out"
    if isinstance(exc, subprocess.CalledProcessError):
        return f"source returned curl exit {exc.returncode}"
    return str(exc)


def parse_government_source(html_bytes: bytes, section: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    source_type = source.get("type")
    if source_type == "legisinfo_bills":
        return parse_legisinfo_bills(html_bytes, source)
    if source_type == "legistar_calendar":
        return parse_legistar_calendar(html_bytes, source)
    return official_tracker_item(section, source, f"Open {source['name']} for the latest official bill progress and sitting details.")


def parse_manual_government_items(section: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for raw in source.get("items", []):
        items.append({
            "id": stable_id(f"{section['id']}-{raw['title']}"),
            "title": raw["title"],
            "status": raw.get("status", ""),
            "description": raw.get("description", ""),
            "url": raw["url"],
            "source": source["name"],
            "date": raw.get("date", ""),
            "priority": raw.get("priority", 1),
            "category": raw.get("category", "Government context"),
            "importanceReasons": raw.get("importanceReasons", ["Included as high-impact recent government context."]),
            "outcome": raw.get("outcome", "active")
        })
    return items


def official_tracker_item(section: dict[str, Any], source: dict[str, Any], description: str) -> list[dict[str, Any]]:
    return [{
        "id": stable_id(source["url"]),
        "title": section["name"],
        "status": "Official tracker",
        "description": description,
        "url": source["url"],
        "source": source["name"],
        "date": "",
        "priority": 1,
        "category": "Tracker",
        "importanceReasons": ["Official source link kept available when parsed status is unavailable."],
        "outcome": "tracker"
    }]


def parse_legisinfo_bills(html_bytes: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    parser = LinkTextParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    items = []
    seen: set[str] = set()
    inactive = ["royal assent received", "bill defeated", "outside the order", "pro forma"]
    for link in parser.links:
        text = strip_tags(link["text"])
        if "Current status" not in text or "Last major stage completed" not in text:
            continue
        if any(status in text.lower() for status in inactive):
            continue
        match = re.search(
            r"\b([CS]-\d+)\b.*?\b\1\b\s+(.*?)\s+Current status\s+(.*?)\s+Last major stage completed\s+(.*)",
            text
        )
        if not match:
            continue
        bill_number, title, status, stage = [strip_tags(value) for value in match.groups()]
        href = absolute_url(link["href"], "https://www.parl.ca")
        if bill_number in seen:
            continue
        seen.add(bill_number)
        items.append({
            "id": stable_id(f"{source['name']}-{bill_number}"),
            "title": f"{bill_number}: {title}",
            "status": status,
            "description": summarize_bill(title, status, stage),
            "url": href,
            "source": source["name"],
            "date": "",
            "priority": government_priority(status, title),
            "category": government_category(title),
            "importanceReasons": government_reasons(title, status),
            "outcome": government_outcome(status)
        })
        if len(items) >= 20:
            break
    items.sort(key=lambda item: item["priority"], reverse=True)
    return items[:12]


def parse_legistar_calendar(html_bytes: bytes, source: dict[str, Any]) -> list[dict[str, Any]]:
    parser = LinkTextParser()
    parser.feed(html_bytes.decode("utf-8", errors="replace"))
    text = parser.text()
    meetings = []
    pattern = re.compile(
        r"([A-Za-z, &]+?)\s+(\d{1,2}/\d{1,2}/\d{4})\s+(\d{1,2}:\d{2}\s+[AP]M)\s+(.+?)(?=\s+(?:Council|Committee|Advisory|Board|Environment|APC)\b|\s+RadDatePicker|$)"
    )
    for match in pattern.finditer(text):
        name, date, time, details = [strip_tags(value) for value in match.groups()]
        name = clean_meeting_name(name)
        details = clean_meeting_details(details)
        if name in {"Name Meeting Date", "Meeting Calendar"}:
            continue
        meetings.append({
            "id": stable_id(f"{source['name']}-{name}-{date}-{time}"),
            "title": f"{name} - {date}",
            "status": time,
            "description": details[:220],
            "url": source["url"],
            "source": source["name"],
            "date": date,
            "priority": 2 if "Council" in name else 1,
            "category": "Municipal meeting",
            "importanceReasons": ["Upcoming local decision-making forum."],
            "outcome": "active"
        })
        if len(meetings) >= 8:
            break
    if meetings:
        return meetings
    return official_tracker_item({"name": "Esquimalt meeting calendar"}, source, "Open the official Legistar calendar for current meetings, agendas, minutes, and video links.")


def clean_meeting_name(value: str) -> str:
    known = [
        "Special Committee of the Whole",
        "Committee of the Whole",
        "Special Meeting of Council",
        "Environment, Parks and Recreation Advisory Committee",
        "Advisory Planning Commission",
        "APC Design Review Committee",
        "Board of Variance",
        "Council"
    ]
    matches = [(value.rfind(name), name) for name in known if name in value]
    if not matches:
        return value
    return max(matches, key=lambda item: item[0])[1]


def clean_meeting_details(value: str) -> str:
    value = re.sub(r"\.RadScheduler.*", "", value)
    value = re.sub(r"\bMeeting details\b|\bAgenda\b|\bMinutes\b|\bVideo\b", " ", value)
    value = re.sub(r"\bNot available\b", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or "Agenda and meeting details available from the official calendar."


def government_priority(status: str, title: str = "") -> int:
    status = status.lower()
    title_lower = title.lower()
    score = 1
    if "third reading" in status or "awaiting royal assent" in status:
        score = 5
    if "report stage" in status or "committee" in status:
        score = max(score, 4)
    if "second reading" in status:
        score = max(score, 3)
    if "royal assent" in status:
        score = max(score, 6)
    for term, (_, weight) in GOVERNMENT_IMPACT_TERMS.items():
        if term in title_lower:
            score += weight
            break
    return score


def government_category(title: str) -> str:
    title_lower = title.lower()
    for term, (category, _) in GOVERNMENT_IMPACT_TERMS.items():
        if term in title_lower:
            return category
    return "General legislation"


def government_reasons(title: str, status: str) -> list[str]:
    reasons = []
    status_lower = status.lower()
    title_lower = title.lower()
    if "royal assent" in status_lower:
        reasons.append("Passed and became law.")
    elif "third reading" in status_lower or "awaiting royal assent" in status_lower:
        reasons.append("Near the final stage of passage.")
    elif "committee" in status_lower or "report stage" in status_lower:
        reasons.append("Under detailed review or amendment.")
    elif "second reading" in status_lower:
        reasons.append("Principle of the bill is being debated.")
    for term, (category, _) in GOVERNMENT_IMPACT_TERMS.items():
        if term in title_lower:
            reasons.append(f"Touches {category.lower()}.")
            break
    return reasons or ["Tracked because it appears in the official legislative source."]


def government_outcome(status: str) -> str:
    status_lower = status.lower()
    if "royal assent" in status_lower:
        return "passed"
    if any(term in status_lower for term in ["defeated", "withdrawn", "outside the order", "died"]):
        return "not_passed"
    return "active"


def summarize_bill(title: str, status: str, stage: str) -> str:
    title = re.sub(r"^An Act to\s+", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^An Act respecting\s+", "Respecting ", title, flags=re.IGNORECASE)
    return f"{title}. Current status: {status}. Last major stage completed: {stage}."


def summarize_government(sections: list[dict[str, Any]], policy_items: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    all_items = []
    for section in sections:
        for item in section.get("items", []):
            row = dict(item)
            row["sectionName"] = section["name"]
            all_items.append(row)

    def compact(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": item["id"],
            "title": item["title"],
            "status": item.get("status", ""),
            "description": item.get("description", ""),
            "url": item["url"],
            "source": item["source"],
            "sectionName": item.get("sectionName", ""),
            "category": item.get("category", ""),
            "importanceReasons": item.get("importanceReasons", []),
            "priority": item.get("priority", 0),
            "outcome": item.get("outcome", "active")
        }

    important = [
        item for item in all_items
        if item.get("outcome") != "tracker"
    ]
    important.sort(key=lambda item: item.get("priority", 0), reverse=True)
    if not important:
        important = all_items

    return {
        "policyWatch": policy_items or [],
        "important": [compact(item) for item in important[:5]],
        "passed": [compact(item) for item in all_items if item.get("outcome") == "passed"][:5],
        "notPassed": [compact(item) for item in all_items if item.get("outcome") == "not_passed"][:5]
    }


def build_policy_watch(items: list[dict[str, Any]], limit: int = 8) -> list[dict[str, Any]]:
    watched = []
    preferred_sections = {"esquimalt", "greater-victoria", "local", "provincial", "national", "world"}
    seen_titles: set[str] = set()
    for item in items:
        if item["section"] not in preferred_sections:
            continue
        title_key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        if title_key in seen_titles:
            continue
        body = f"{item['title']} {item.get('description', '')}".lower()
        matches = []
        score = item.get("score", 0)
        for category, terms in POLICY_WATCH_TERMS.items():
            if any(policy_term_matches(body, term) for term in terms):
                matches.append(category)
                score += 3
        if not matches:
            continue
        seen_titles.add(title_key)
        if item["section"] in {"esquimalt", "greater-victoria", "local", "provincial", "national"}:
            score += 2
        if item["section"] == "world" and "War & Security" in matches:
            score += 2
        watched.append({
            "id": f"policy-{item['id']}",
            "title": item["title"],
            "status": item.get("source", ""),
            "description": item.get("description", "") or "Open the source for details.",
            "url": item["url"],
            "source": item["source"],
            "sectionName": item["sectionName"],
            "category": ", ".join(matches[:2]),
            "importanceReasons": [policy_reason(matches, item)],
            "priority": round(score, 3),
            "outcome": "policy_watch"
        })
    watched.sort(key=lambda row: row["priority"], reverse=True)
    return watched[:limit]


def policy_term_matches(body: str, term: str) -> bool:
    if " " in term:
        return term in body
    return re.search(rf"\b{re.escape(term)}\b", body) is not None


def policy_reason(matches: list[str], item: dict[str, Any]) -> str:
    topic = ", ".join(matches[:2]).lower()
    return f"Relevant to {topic}; surfaced from {item['sectionName']} coverage."


def absolute_url(href: str, base: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return f"{base.rstrip('/')}{href}"
    return f"{base.rstrip('/')}/{href.lstrip('/')}"


def filter_recent(items: list[dict[str, Any]], days: int) -> list[dict[str, Any]]:
    if days <= 0:
        return items
    now = datetime.now(timezone.utc)
    recent = []
    for item in items:
        if not item["published"]:
            recent.append(item)
            continue
        try:
            age_days = (now - datetime.fromisoformat(item["published"])).total_seconds() / 86400
            if age_days <= days:
                recent.append(item)
        except ValueError:
            recent.append(item)
    return recent


def dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output = []
    for item in sorted(items, key=lambda row: row["score"], reverse=True):
        key = re.sub(r"[^a-z0-9]+", " ", item["title"].lower()).strip()
        key = " ".join(word for word in key.split() if word not in STOP_WORDS)
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def attach_related(items: list[dict[str, Any]]) -> None:
    for item in items:
        related = []
        item_words = set(item["keywords"])
        for candidate in items:
            if candidate["id"] == item["id"]:
                continue
            overlap = item_words.intersection(candidate["keywords"])
            if len(overlap) < 2:
                continue
            same_section = item["section"] == candidate["section"]
            same_source = item["source"] == candidate["source"]
            if not same_section and len(overlap) < 4:
                continue
            score = len(overlap) * 2 + (3 if same_section else 0) - (2 if same_source else 0)
            related.append((score, len(overlap), candidate))
        related.sort(key=lambda pair: (pair[0], pair[1], pair[2]["score"]), reverse=True)
        item["relatedSources"] = [
            {
                "source": candidate["source"],
                "title": candidate["title"],
                "url": candidate["url"],
                "reason": related_reason(item, candidate)
            }
            for _, _, candidate in related[:3]
        ]


def related_reason(item: dict[str, Any], candidate: dict[str, Any]) -> str:
    overlap = sorted(set(item["keywords"]).intersection(candidate["keywords"]))
    if item["section"] == candidate["section"]:
        return f"Same section; shared terms: {', '.join(overlap[:4])}."
    return f"Shared terms: {', '.join(overlap[:4])}."


def sectioned(items: list[dict[str, Any]], config: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    sections = []
    for section in config["sections"]:
        selected = [item for item in items if item["section"] == section["id"]]
        selected.sort(key=lambda row: row["score"], reverse=True)
        sections.append({
            "id": section["id"],
            "name": section["name"],
            "focus": section.get("focus", ""),
            "items": selected[:limit]
        })
    return sections


def write_outputs(payload: dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / "latest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if "government" in payload:
        (DATA_DIR / "government.json").write_text(json.dumps(payload["government"], indent=2), encoding="utf-8")
    if "sports" in payload:
        (DATA_DIR / "sports.json").write_text(json.dumps(payload["sports"], indent=2), encoding="utf-8")
    (DATA_DIR / "digest.md").write_text(render_markdown(payload), encoding="utf-8")
    (DATA_DIR / "digest.html").write_text(render_html(payload), encoding="utf-8")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [f"# Modern Community Topics - {payload['generatedAtLocal']}", ""]
    for section in payload["sections"]:
        lines.extend([f"## {section['name']}", ""])
        if not section["items"]:
            lines.extend(["No current stories found.", ""])
            continue
        for item in section["items"]:
            lines.append(f"- [{item['title']}]({item['url']}) - {item['source']}")
        lines.append("")
    if payload["errors"]:
        lines.extend(["## Feed Notes", ""])
        lines.extend(f"- {error}" for error in payload["errors"])
    government = payload.get("government", {})
    if government.get("sections"):
        lines.extend(["", "## Government Roundup", ""])
        highlights = government.get("highlights", {})
        for title, key in [
            ("Policy Watch", "policyWatch"),
            ("Most Relevant", "important"),
            ("Became Law", "passed"),
            ("Stopped or Stalled", "notPassed")
        ]:
            items = highlights.get(key, [])
            if not items:
                continue
            lines.extend([f"### {title}", ""])
            for item in items[:8]:
                reason = " ".join(item.get("importanceReasons", []))
                lines.append(f"- [{item['title']}]({item['url']}) - {item.get('category') or item.get('status')}. {reason}")
            lines.append("")
        for section in government["sections"]:
            lines.extend([f"### {section['name']}", ""])
            for item in section["items"][:8]:
                lines.append(f"- [{item['title']}]({item['url']}) - {item['status']}")
            lines.append("")
    sports = payload.get("sports", {})
    if sports.get("scoreboards") or sports.get("sections"):
        lines.extend(["", "## Sports", ""])
        if sports.get("scoreboards"):
            lines.extend(["### Scores & Fixtures", ""])
            for item in sports["scoreboards"]:
                lines.append(f"- [{item['title']}]({item['url']}) - {item['status']} ({item['source']})")
                for match in item.get("matches", [])[:8]:
                    note = f" - {match['note']}" if match.get("note") else ""
                    lines.append(f"  - {match['text']}{note}")
            lines.append("")
        for section in sports.get("sections", []):
            lines.extend([f"### {section['name']}", ""])
            for item in section.get("items", [])[:8]:
                lines.append(f"- [{item['title']}]({item['url']}) - {item['source']}")
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_html(payload: dict[str, Any]) -> str:
    sections = []
    for section in payload["sections"]:
        bullets = "\n".join(
            f'<li><a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a> '
            f'<span>{html.escape(item["source"])}</span></li>'
            for item in section["items"]
        ) or "<li>No current stories found.</li>"
        sections.append(f"<h2>{html.escape(section['name'])}</h2><ul>{bullets}</ul>")
    government_sections = []
    for title, key in [
        ("Policy Watch", "policyWatch"),
        ("Most Relevant", "important"),
        ("Became Law", "passed"),
        ("Stopped or Stalled", "notPassed")
    ]:
        items = payload.get("government", {}).get("highlights", {}).get(key, [])
        if not items:
            continue
        bullets = "\n".join(
            f'<li><a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a> '
            f'<span>{html.escape(item.get("category") or item.get("status") or "")}</span></li>'
            for item in items[:8]
        )
        government_sections.append(f"<h2>{html.escape(title)}</h2><ul>{bullets}</ul>")
    for section in payload.get("government", {}).get("sections", []):
        bullets = "\n".join(
            f'<li><a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a> '
            f'<span>{html.escape(item["status"])}</span></li>'
            for item in section["items"][:8]
        ) or "<li>No current government items found.</li>"
        government_sections.append(f"<h2>{html.escape(section['name'])}</h2><ul>{bullets}</ul>")
    sports_sections = []
    scoreboards = payload.get("sports", {}).get("scoreboards", [])
    if scoreboards:
        score_items = []
        for item in scoreboards:
            match_lines = []
            for match in item.get("matches", [])[:8]:
                note = f' <span>{html.escape(match["note"])}</span>' if match.get("note") else ""
                match_lines.append(f'<li>{html.escape(match["text"])}{note}</li>')
            match_bullets = "\n".join(match_lines) or "<li>Open the official tracker for current scores and fixtures.</li>"
            score_items.append(
                f'<li><a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a> '
                f'<span>{html.escape(item["status"])} - {html.escape(item["source"])}</span>'
                f'<ul>{match_bullets}</ul></li>'
            )
        bullets = "\n".join(score_items)
        sports_sections.append(f"<h2>Scores & Fixtures</h2><ul>{bullets}</ul>")
    for section in payload.get("sports", {}).get("sections", []):
        bullets = "\n".join(
            f'<li><a href="{html.escape(item["url"])}">{html.escape(item["title"])}</a> '
            f'<span>{html.escape(item["source"])}</span></li>'
            for item in section.get("items", [])[:8]
        ) or "<li>No current sports headlines found.</li>"
        sports_sections.append(f"<h2>{html.escape(section['name'])}</h2><ul>{bullets}</ul>")
    return textwrap.dedent(f"""\
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Modern Community Topics</title>
      <style>
        body {{ color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.5; margin: 32px; }}
        h1 {{ font-size: 24px; }}
        h2 {{ border-top: 1px solid #d9e2ec; font-size: 18px; margin-top: 28px; padding-top: 18px; }}
        a {{ color: #1d4ed8; }}
        .app-link {{ background: #eef2f6; border: 1px solid #d7dee8; border-radius: 6px; color: #0f4c5c; display: inline-block; font-weight: 700; margin-bottom: 18px; padding: 8px 12px; text-decoration: none; }}
        span {{ color: #66788a; font-size: 13px; }}
      </style>
    </head>
    <body>
      <a class="app-link" href="../web/">Back to app</a>
      <h1>Modern Community Topics - {html.escape(payload['generatedAtLocal'])}</h1>
      {''.join(sections)}
      <h1>Government Roundup</h1>
      {''.join(government_sections)}
      <h1>Sports</h1>
      {''.join(sports_sections)}
    </body>
    </html>
    """)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local daily news briefing from RSS feeds.")
    parser.add_argument("--days", type=int, default=3, help="Include stories from the last N days. Use 0 for all.")
    parser.add_argument("--limit-per-section", type=int, default=8, help="Maximum bullets per section.")
    args = parser.parse_args()

    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    result = load_items(config)
    items = filter_recent(dedupe(result.items), args.days)
    attach_related(items)
    government = load_government(config)
    government["highlights"]["policyWatch"] = build_policy_watch(items)
    sports = load_sports(config, args.days, args.limit_per_section)
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "generatedAtLocal": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "sections": sectioned(items, config, args.limit_per_section),
        "government": government,
        "sports": sports,
        "errors": result.errors + government["errors"] + sports["errors"]
    }
    write_outputs(payload)
    print(f"Wrote {DATA_DIR / 'latest.json'} with {sum(len(s['items']) for s in payload['sections'])} stories.")
    if result.errors:
        print("Some feeds failed:")
        for error in result.errors:
            print(f"- {error}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
