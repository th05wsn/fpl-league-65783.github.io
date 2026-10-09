import json
import os
from datetime import datetime, timezone
import requests

LEAGUE_ID = 65783
API_BASE = "https://fantasy.premierleague.com/api"


def get_fpl_data():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    # 1. Fetch General Info (Current Gameweek)
    bootstrap_res = requests.get(
        f"{API_BASE}/bootstrap-static/", headers=headers
    ).json()

    # Get current gameweek or default to finished events
    current_gw_obj = next(
        (gw for gw in bootstrap_res["events"] if gw["is_current"]), None
    )
    if not current_gw_obj:
        current_gw_obj = next(
            (gw for gw in reversed(bootstrap_res["events"]) if gw["finished"]),
            bootstrap_res["events"][0],
        )

    # 2. Fetch League Standings
    league_res = requests.get(
        f"{API_BASE}/leagues-classic/{LEAGUE_ID}/standings/", headers=headers
    ).json()
    league_info = league_res.get("league", {})
    raw_standings = league_res.get("standings", {}).get("results", [])

    # 3. Process Standings & Historical Gameweek Data
    processed_standings = []
    for entry in raw_standings:
        entry_id = entry["entry"]

        # Fetch history for each manager to build gw_history
        history_res = requests.get(
            f"{API_BASE}/entry/{entry_id}/history/", headers=headers
        ).json()
        current_history = history_res.get("current", [])

        # Extract cumulative totals per gameweek for chart/form tracking
        gw_history = [gw["total_points"] for gw in current_history]

        processed_standings.append(
            {
                "id": entry.get("id"),
                "rank": entry.get("rank"),
                "last_rank": entry.get("last_rank", 0),
                "entry": entry_id,
                "entry_name": entry.get("entry_name"),
                "player_name": entry.get("player_name"),
                "event_total": entry.get("event_total", 0),
                "total": entry.get("total", 0),
                "gw_history": gw_history,
            }
        )

    # 4. Fetch Top Premier League Players of Current Gameweek
    top_prem_players = []
    try:
        elements = bootstrap_res.get("elements", [])
        teams = {t["id"]: t["short_name"] for t in bootstrap_res.get("teams", [])}
        element_types = {
            et["id"]: et["singular_name_short"]
            for et in bootstrap_res.get("element_types", [])
        }

        # Sort by event points (current gameweek score)
        sorted_elements = sorted(
            elements, key=lambda x: x.get("event_points", 0), reverse=True
        )[:4]
        for p in sorted_elements:
            top_prem_players.append(
                {
                    "name": p.get("web_name"),
                    "position": element_types.get(p.get("element_type"), ""),
                    "team": teams.get(p.get("team"), ""),
                    "points": p.get("event_points", 0),
                }
            )
    except Exception as e:
        print(f"Error fetching top players: {e}")

    # 5. Build Dashboard Payload
    final_data = {
        "league": {"id": league_info.get("id"), "name": league_info.get("name")},
        "standings": {"results": processed_standings},
        "top_prem_players": top_prem_players,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    # Save data.json in the root directory (matching app.js fetch)
    with open("data.json", "w") as f:
        json.dump(final_data, f, indent=2)

    # Optional: Also save to public directory if deploying via GitHub Pages
    if os.path.exists("public"):
        with open("public/data.json", "w") as f:
            json.dump(final_data, f, indent=2)


if __name__ == "__main__":
    get_fpl_data()
