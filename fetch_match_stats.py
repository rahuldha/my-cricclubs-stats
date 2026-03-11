"""
Fetch match statistics from CricClubs.com

This script scrapes the ARCL fixtures page, fetches detailed info for each match,
and outputs the data to CSV files.
"""

import re
import csv
import cloudscraper
from concurrent.futures import ThreadPoolExecutor, as_completed

# =============================================================================
# CONFIGURATION
# =============================================================================
# These values identify the ARCL league on CricClubs
# You can find these in any CricClubs URL for your league

BASE_URL = "https://www.cricclubs.com/ARCL"
CLUB_ID = 992
LEAGUE_ID = 321

# Create a cloudscraper session that can handle Cloudflare protection
# This is more robust than plain curl when sites have bot protection
scraper = cloudscraper.create_scraper()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def fetch_url(url):
    """
    Fetch a URL using cloudscraper and return the HTML content.

    cloudscraper automatically handles Cloudflare challenges that would
    block regular curl or requests calls.
    """
    response = scraper.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def extract_field(html, keyword):
    """
    Extract a field value from HTML given a keyword like 'Location:'.

    This finds the keyword in the HTML, then extracts the value that follows it.
    It's a simple approach that works well for CricClubs pages.
    """
    idx = html.find(keyword)
    if idx < 0:
        return ""

    # Get a chunk of HTML after the keyword
    chunk = html[idx:idx + 500]

    # Remove HTML tags, replacing them with pipe separators
    clean = re.sub(r"<[^>]+>", "|", chunk)
    clean = clean.replace("&nbsp;", " ")

    # Split by pipes and get the value (first part is keyword, second is value)
    parts = [p.strip() for p in clean.split("|") if p.strip()]
    if len(parts) >= 2:
        return parts[1]
    return ""


def parse_innings_times(html, label):
    """
    Extract duration, start time, and end time for an innings section.

    CricClubs displays innings info like:
    "1st Innings: 61 min 10:49 AM 11:50 AM"

    This function parses that into separate values.
    """
    idx = html.find(label)
    if idx < 0:
        return "", "", ""

    chunk = html[idx:idx + 300]
    clean = re.sub(r"<[^>]+>", "|", chunk)
    clean = clean.replace("&nbsp;", " ")
    parts = [p.strip() for p in clean.split("|") if p.strip()]

    duration = ""
    start_time = ""
    end_time = ""

    # parts[0] is the label, parts[1] is duration, parts[2] has times
    if len(parts) >= 2:
        duration = parts[1]  # e.g. "61 min"

    if len(parts) >= 3:
        # Extract times like "10:49 AM" from the text
        times = re.findall(r"\d{1,2}:\d{2}\s*[AP]M", parts[2])
        if len(times) >= 2:
            start_time = times[0]
            end_time = times[1]
        elif len(times) == 1:
            start_time = times[0]

    return duration, start_time, end_time


# =============================================================================
# MAIN SCRAPING FUNCTIONS
# =============================================================================

def parse_fixtures():
    """
    Parse the fixtures page to get all matches in the league.

    Returns a list of dictionaries with match_id, date, teams, etc.
    """
    url = f"{BASE_URL}/fixtures.do?league={LEAGUE_ID}&clubId={CLUB_ID}"
    html = fetch_url(url)

    # Find the schedule table in the HTML
    match = re.search(
        r'<table[^>]*id="schedule-table"[^>]*>(.*?)</table>', html, re.DOTALL
    )
    if not match:
        print("ERROR: Could not find schedule-table")
        return []

    table = match.group(1)

    # Find all table rows
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.DOTALL)

    matches = []
    for tr in trs[1:]:  # Skip header row
        # Extract match IDs from links in the row
        match_ids = re.findall(r"matchId=(\d+)", tr)

        # Extract table cells
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.DOTALL)

        # Clean up cell contents (remove HTML tags)
        row = []
        for td in tds:
            clean = re.sub(r"<[^>]+>", " ", td).strip()
            clean = re.sub(r"\s+", " ", clean)
            clean = clean.replace("&nbsp;", "").strip()
            row.append(clean)

        # Only process rows with enough data
        if len(row) >= 10 and match_ids:
            matches.append({
                "match_id": match_ids[0],
                "match_number": row[0],
                "match_type": row[1],
                "date": row[2],
                "team1": row[4],
                "team2": row[5],
            })

    return matches


def parse_match_info(match_id):
    """
    Parse the info page for a single match to get detailed timing data.

    This fetches the match info page and extracts:
    - Ground/location
    - Innings start/end times
    - Match duration
    - Overs bowled
    - Toss result
    """
    url = f"{BASE_URL}/info.do?matchId={match_id}&clubId={CLUB_ID}"

    try:
        html = fetch_url(url)
    except Exception as e:
        print(f"  Error fetching info for {match_id}: {e}")
        return None

    # Extract basic fields
    location = extract_field(html, "Location:")
    toss = extract_field(html, "Toss:")

    # Clean up toss text
    toss_idx = html.find("Toss:")
    if toss_idx >= 0:
        toss_chunk = html[toss_idx:toss_idx + 500]
        toss_clean = re.sub(r"<[^>]+>", " ", toss_chunk)
        toss_clean = toss_clean.replace("&nbsp;", " ")
        toss_clean = re.sub(r"\s+", " ", toss_clean).strip()
        toss = toss_clean.replace("Toss:", "").strip()
        # Trim at next field boundary
        for stopper in ["Player of", "Location:", "1st Innings", "Last Updated"]:
            si = toss.find(stopper)
            if si > 0:
                toss = toss[:si].strip()

    # Extract innings timing information
    inn1_dur, inn1_start, inn1_end = parse_innings_times(html, "1st Innings:")
    inn2_dur, inn2_start, inn2_end = parse_innings_times(html, "2nd Innings:")
    break_dur, break_start, break_end = parse_innings_times(html, "Innings break:")

    # Match timing: start of 1st innings to end of 2nd innings
    match_start_time = inn1_start
    match_end_time = inn2_end

    # Calculate total duration by summing innings and break
    total_duration = ""
    durations = []
    for d in [inn1_dur, break_dur, inn2_dur]:
        m = re.search(r"(\d+)\s*min", d)
        if m:
            durations.append(int(m.group(1)))
    if durations:
        total_minutes = sum(durations)
        total_duration = f"{total_minutes} min"

    # Extract overs from scorecard (format: "15.2 / 16 ov")
    overs = re.findall(r"([\d.]+)\s*/\s*([\d.]+)\s*ov", html)
    team1_overs = ""
    team2_overs = ""
    if len(overs) >= 2:
        team1_overs = f"{overs[0][0]}/{overs[0][1]}"
        team2_overs = f"{overs[1][0]}/{overs[1][1]}"
    elif len(overs) == 1:
        team1_overs = f"{overs[0][0]}/{overs[0][1]}"

    return {
        "ground": location,
        "match_start_time": match_start_time,
        "match_end_time": match_end_time,
        "match_duration": total_duration,
        "innings1_duration": inn1_dur,
        "innings1_start": inn1_start,
        "innings1_end": inn1_end,
        "innings_break": break_dur,
        "innings2_duration": inn2_dur,
        "innings2_start": inn2_start,
        "innings2_end": inn2_end,
        "team1_overs": team1_overs,
        "team2_overs": team2_overs,
        "toss": toss,
    }


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    print("Fetching fixtures from ARCL CricClubs...")
    matches = parse_fixtures()
    print(f"Found {len(matches)} matches")

    if not matches:
        return

    # Define CSV columns
    fieldnames = [
        "match_id",
        "match_number",
        "match_type",
        "date",
        "team1",
        "team2",
        "ground",
        "match_start_time",
        "match_end_time",
        "match_duration",
        "innings1_duration",
        "innings1_start",
        "innings1_end",
        "innings_break",
        "innings2_duration",
        "innings2_start",
        "innings2_end",
        "team1_overs",
        "team2_overs",
        "toss",
    ]

    # Empty info template for matches we can't fetch
    empty_info = {k: "" for k in fieldnames if k not in ["match_id", "match_number", "match_type", "date", "team1", "team2"]}

    print("Fetching match info pages...")
    info_results = {}

    # Helper function for concurrent fetching
    def fetch_one(match):
        mid = match["match_id"]
        info = parse_match_info(mid)
        return mid, info

    # Fetch all match info pages concurrently (10 at a time)
    # This is MUCH faster than fetching one at a time
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_one, m): m for m in matches}
        done = 0
        for future in as_completed(futures):
            done += 1
            mid, info = future.result()
            info_results[mid] = info or empty_info
            if done % 50 == 0:
                print(f"  Progress: {done}/{len(matches)}")

    print(f"Fetched all {len(matches)} match info pages. Writing CSVs...")

    # Split into matches with and without timing data
    with_result = []
    without_result = []

    for match in matches:
        info = info_results.get(match["match_id"], empty_info)
        row = {**match, **info}
        if row.get("match_start_time"):
            with_result.append(row)
        else:
            without_result.append(row)

    # Write CSV files
    with open("arcl_match_stats.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(with_result)

    with open("arcl_match_stats_without_result.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(without_result)

    print(f"\narcl_match_stats.csv: {len(with_result)} matches with timing data")
    print(f"arcl_match_stats_without_result.csv: {len(without_result)} matches without timing data")
    print("Done!")


if __name__ == "__main__":
    main()
