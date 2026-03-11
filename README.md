# CricClubs Ground Stats

An MCP plugin for Claude Code that fetches match duration statistics per ground from any [CricClubs](https://www.cricclubs.com) cricket series.

## What it does

Given a CricClubs series URL, this tool:

1. Scrapes the fixtures page for all matches (date, time, teams, ground)
2. Fetches each match's info page for actual start/end times and innings durations
3. Aggregates match duration by ground and returns a summary table

**Sample output (ARCL Summer 2025 Men):**

| Ground | Matches | Avg (min) | Min (min) | Max (min) |
|--------|---------|-----------|-----------|-----------|
| North SeaTac Park | 47 | 136 | 77 | 303 |
| Ron Regis Park | 42 | 139 | 67 | 233 |
| Hidden Valley Park Field 1 | 30 | 121 | 81 | 147 |
| Big Finn Hill Park | 27 | 120 | 10 | 146 |
| Petrovitsky Park Field #2 | 17 | 125 | 93 | 157 |
| **TOTAL** | **281** | **128** | | |

## Setup

### Prerequisites

- Python 3.10+
- Required packages:
  ```bash
  pip install "mcp[cli]" cloudscraper matplotlib fpdf2
  ```

### Option 1: Use as MCP server in Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "cricclubs-ground-stats": {
      "command": "python",
      "args": ["/path/to/cricclubs_ground_stats_mcp.py"]
    }
  }
}
```

Then in Claude Code, ask:

> Get ground stats for https://www.cricclubs.com/ARCL/listMatches.do?league=321&clubId=992

### Option 2: Install as Claude Marketplace plugin

Add to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "my-cricclubs-stats": {
      "source": {
        "source": "github",
        "repo": "YOUR_USERNAME/my-cricclubs-stats"
      }
    }
  },
  "enabledPlugins": {
    "cricclubs-ground-stats@my-cricclubs-stats": true
  }
}
```

Restart Claude Code and the `get_ground_stats` tool will be available.

## Standalone scripts

### fetch_match_stats.py

Fetches all match data and writes two CSVs:

```bash
python fetch_match_stats.py
```

- `arcl_match_stats.csv` — matches with timing data
- `arcl_match_stats_without_result.csv` — matches without timing data

**Fields:** match_id, date, team1, team2, ground, match_start_time, match_end_time, match_duration, innings1/2 duration, innings break, overs bowled, toss

### ground_stats.py

Reads `arcl_match_stats.csv` and generates:

```bash
python ground_stats.py
```

- `ground_stats.csv` — aggregated stats per ground
- `ground_stats_chart.png` — bar chart with avg/min/max duration per ground

### generate_outlier_report.py

Creates a PDF report of matches exceeding 140 minutes:

```bash
python generate_outlier_report.py
```

- `arcl_outlier_matches_report.pdf` — detailed report with summary stats, ground breakdown, and clickable CricClubs links

## Input URL format

The tool accepts any CricClubs series URL that contains `league` and `clubId` parameters:

```
https://www.cricclubs.com/{LEAGUE}/listMatches.do?league={ID}&clubId={ID}
https://www.cricclubs.com/{LEAGUE}/fixtures.do?league={ID}&clubId={ID}
```

## Notes

- Uses `cloudscraper` to handle Cloudflare protection on CricClubs
- Only matches where the scorer recorded innings start/end times will have duration data
- Match duration = 1st innings + innings break + 2nd innings
- The tool fetches each match's info page concurrently (10 threads) for speed

## Project Structure

```
my-cricclubs-stats/
├── .claude-plugin/
│   └── marketplace.json       # Plugin metadata
├── .mcp.json                  # MCP server config
├── cricclubs_ground_stats_mcp.py  # MCP server
├── fetch_match_stats.py       # Data fetcher
├── ground_stats.py            # Ground analysis + chart
├── generate_outlier_report.py # PDF report generator
└── README.md
```
