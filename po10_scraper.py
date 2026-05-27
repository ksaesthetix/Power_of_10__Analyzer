import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.powerof10.uk"
COACH_URL = BASE_URL + "/Home/Coach/{coach_id}"
ATHLETE_URL = BASE_URL + "/Home/Athlete/{athlete_id}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
    "Referer": "https://www.powerof10.uk/",
}
REQUEST_DELAY = 1.5


@dataclass
class Performance:
    athlete_id: str = ""
    athlete_name: str = ""
    event: str = ""
    performance: str = ""
    indoor: bool = False
    wind: str = ""
    position: str = ""
    venue: str = ""
    meeting: str = ""
    meeting_url: str = ""
    date: str = ""
    year: str = ""
    age_group: str = ""
    was_pb: bool = False


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def get_soup(url: str, session: requests.Session) -> Optional[BeautifulSoup]:
    try:
        response = session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        return BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
        return None


def get_athlete_ids_from_coach(coach_id: str, session: requests.Session) -> list[tuple[str, str]]:
    url = COACH_URL.format(coach_id=coach_id)
    soup = get_soup(url, session)
    if soup is None:
        return []

    athletes_div = soup.find("div", id="divAthletes")
    if athletes_div is None:
        return []

    results: list[tuple[str, str]] = []
    for link in athletes_div.find_all("a", href=re.compile(r"/Home/Athlete/")):
        href = link.get("href", "")
        athlete_id = href.split("/Home/Athlete/")[-1].strip("/")
        name = clean(link.get_text())
        if athlete_id and (athlete_id, name) not in results:
            results.append((athlete_id, name))
    return results


def parse_griddata_json(soup: BeautifulSoup, athlete_id: str, athlete_name: str) -> list[Performance]:
    perfs: list[Performance] = []
    for script in soup.find_all("script"):
        text = script.string or ""
        match = re.search(r'let gridData\s*=\s*(\{.*?\});', text, re.DOTALL)
        if not match:
            match = re.search(r'var gridData\s*=\s*(\{.*?\});', text, re.DOTALL)
        if not match:
            continue

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        dictpgs = data.get("perfs", {}).get("dictpgs", {})
        for pg_data in dictpgs.values():
            year = str(pg_data.get("yr", ""))
            for page in pg_data.get("pgs", []):
                for row in page.get("results", []):
                    perf_val = row.get("perf", "")
                    addinf = row.get("addinf", "")
                    mtid = row.get("mtid", "")
                    meet_url = f"{BASE_URL}/Home/Results/{mtid}" if mtid else ""
                    perfs.append(Performance(
                        athlete_id=athlete_id,
                        athlete_name=athlete_name,
                        event=row.get("evnt", ""),
                        performance=perf_val + (" i" if addinf == "i" else ""),
                        indoor=addinf == "i",
                        wind=row.get("wnd", ""),
                        position=row.get("pos", ""),
                        venue=row.get("venn", ""),
                        meeting=row.get("mtn", ""),
                        meeting_url=meet_url,
                        date=row.get("dte", ""),
                        year=year,
                        age_group=row.get("ag", ""),
                        was_pb=bool(row.get("waspb", False)),
                    ))
        break

    return perfs


def parse_career_js_arrays(soup: BeautifulSoup, athlete_id: str, athlete_name: str) -> list[Performance]:
    perfs: list[Performance] = []
    all_scripts = " ".join(script.string or "" for script in soup.find_all("script"))
    indices = re.findall(r'evntKeys\.set\((\d+),', all_scripts)
    if not indices:
        return perfs
    max_idx = max(int(i) for i in indices)

    def js_array(name: str) -> list[str]:
        match = re.search(r'var\s+' + re.escape(name) + r'\s*=\s*\[([^\]]*)\]', all_scripts)
        if not match:
            return []
        raw = match.group(1)
        return [item.strip().strip('"\'"') for item in raw.split(",")]

    def js_string(name: str) -> str:
        match = re.search(r'var\s+' + re.escape(name) + r'\s*=\s*\'([^\']*)\'', all_scripts)
        if match:
            return match.group(1)
        match = re.search(r'var\s+' + re.escape(name) + r'\s*=\s*"([^"]*)"', all_scripts)
        return match.group(1) if match else ""

    def decode_perf(raw_val: str, fmt: str) -> str:
        try:
            v = int(raw_val)
        except (ValueError, TypeError):
            return raw_val
        if fmt == "SecCs":
            secs = v // 100
            cs = v % 100
            if secs >= 60:
                mins = secs // 60
                secs = secs % 60
                return f"{mins}:{secs:02d}.{cs:02d}"
            return f"{secs}.{cs:02d}"
        if fmt == "MinSecCs":
            secs = v // 100
            cs = v % 100
            mins = secs // 60
            secs = secs % 60
            return f"{mins}:{secs:02d}.{cs:02d}"
        if fmt == "MetreCm":
            m_val = v // 100
            cm = v % 100
            return f"{m_val}.{cm:02d}"
        return raw_val

    for idx in range(max_idx + 1):
        event_name = js_string(f"dataEventName{idx}")
        fmt = js_string(f"dataFormatToUse{idx}")
        values = js_array(f"dataRpValues{idx}")
        locations = js_array(f"dataRpLocations{idx}")
        meetings = js_array(f"dataRpMeetings{idx}")
        positions = js_array(f"dataRpPositions{idx}")
        dates = js_array(f"dataRpMeetDates{idx}")
        age_grps = js_array(f"dataRpAgeGroups{idx}")
        indoors = js_array(f"dataRpIndoors{idx}")

        for i, raw_val in enumerate(values):
            if not raw_val:
                continue

            perf_str = decode_perf(raw_val, fmt)
            is_indoor = (indoors[i] == "1") if i < len(indoors) else False
            if is_indoor:
                perf_str += " i"

            date_str = dates[i] if i < len(dates) else ""
            year = ""
            dm = re.search(r"(\d{4})$", date_str)
            if dm:
                year = dm.group(1)
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y")
                    date_str = dt.strftime("%d %b %Y").lstrip("0")
                except Exception:
                    pass

            perfs.append(Performance(
                athlete_id=athlete_id,
                athlete_name=athlete_name,
                event=event_name,
                performance=perf_str,
                indoor=is_indoor,
                wind="",
                position=positions[i] if i < len(positions) else "",
                venue=locations[i].replace("`", "'") if i < len(locations) else "",
                meeting=meetings[i].replace("`", "'") if i < len(meetings) else "",
                meeting_url="",
                date=date_str,
                year=year,
                age_group=age_grps[i] if i < len(age_grps) else "",
                was_pb=False,
            ))

    return perfs


def scrape_athlete_performances(
    athlete_id: str,
    athlete_name: str,
    session: requests.Session,
    scope: str = "career",
) -> list[Performance]:
    url = ATHLETE_URL.format(athlete_id=athlete_id)
    soup = get_soup(url, session)
    if soup is None:
        return []

    if not athlete_name:
        athlete_name = clean(athlete_id)

    if scope == "career":
        return parse_career_js_arrays(soup, athlete_id, athlete_name)
    return parse_griddata_json(soup, athlete_id, athlete_name)


def build_dataframe(
    coach_id: str = "",
    athlete_ids: Optional[list[str]] = None,
    scope: str = "career",
) -> pd.DataFrame:
    athlete_ids = athlete_ids or []
    athlete_roster: list[tuple[str, str]] = [(aid, "") for aid in athlete_ids if aid]

    with requests.Session() as session:
        session.get(BASE_URL + "/", headers=HEADERS, timeout=15)
        if coach_id:
            roster = get_athlete_ids_from_coach(coach_id, session)
            existing = {aid for aid, _ in athlete_roster}
            for aid, name in roster:
                if aid not in existing:
                    athlete_roster.append((aid, name))
                    existing.add(aid)
        all_performances: list[Performance] = []
        for idx, (athlete_id, athlete_name) in enumerate(athlete_roster, start=1):
            perfs = scrape_athlete_performances(athlete_id, athlete_name, session, scope)
            all_performances.extend(perfs)
            if idx < len(athlete_roster):
                time.sleep(REQUEST_DELAY)

    df = pd.DataFrame([
        {
            "athlete_id": p.athlete_id,
            "athlete_name": p.athlete_name,
            "event": p.event,
            "performance": p.performance,
            "indoor": p.indoor,
            "wind": p.wind,
            "position": p.position,
            "venue": p.venue,
            "meeting": p.meeting,
            "meeting_url": p.meeting_url,
            "date": p.date,
            "year": p.year,
            "age_group": p.age_group,
            "was_pb": p.was_pb,
        }
        for p in all_performances
    ])
    if not df.empty:
        df["year"] = pd.to_numeric(df["year"], errors="coerce")
        df["position"] = pd.to_numeric(df["position"], errors="coerce")
    return df


def infer_event_kind(event: str) -> str:
    name = str(event or "").lower()
    if any(keyword in name for keyword in ("jump", "vault", "shot", "discus", "hammer", "javelin", "throw")):
        return "distance"
    if name in {"long jump", "triple jump", "high jump", "pole vault", "shot put", "discus", "hammer", "javelin"}:
        return "distance"
    if re.match(r"^\d+(m)?$", name):
        return "time"
    if any(keyword in name for keyword in ("marathon", "walk", "steeple", "cross", "hurdles")):
        return "time"
    return "other"


def parse_perf_numeric(perf: str, kind: str):
    if not perf:
        return None
    raw = str(perf).lower().replace("i", "").strip()
    raw = re.sub(r"[^\d\.:]", "", raw)
    if not raw:
        return None
    if kind == "time":
        if ":" in raw:
            parts = raw.split(":")
            try:
                parts = [float(part) for part in parts]
            except ValueError:
                return None
            secs = 0.0
            for part in parts[::-1]:
                secs = secs / 60.0 + part
            return secs
        try:
            return float(raw)
        except ValueError:
            return None
    if kind == "distance":
        try:
            return float(raw)
        except ValueError:
            return None
    return None
