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

    # 1. Fetch Bootstrap Static
    bootstrap_res = requests.get(
        f"{API_BASE}/bootstrap-static/", headers=headers
    ).json()

    current_gw_obj = next(
        (gw for gw in bootstrap_res["events"] if gw["is_current"]), None
    )
    if not current_gw_obj:
        current_gw_obj = next(
            (gw for gw in reversed(bootstrap_res["events"]) if gw["finished"]),
            bootstrap_res["events"][0],
        )

    current_gw = current_gw_obj["id"]

    # Build Team Map & Form Data
    teams = {
        t["id"]: {
            "name": t["name"],
            "short_name": t["short_name"],
            "strength": t["strength"],
            "code": t["code"],
        }
        for t in bootstrap_res.get("teams", [])
    }

    element_types = {
        et["id"]: et["singular_name_short"]
        for et in bootstrap_res.get("element_types", [])
    }

    # 2. Fetch Fixtures
    fixtures_res = requests.get(f"{API_BASE}/fixtures/", headers=headers).json()

    gw_fixtures = [f for f in fixtures_res if f.get("event") == current_gw]
    next_gw_fixtures = [
        f for f in fixtures_res if f.get("event") == (current_gw + 1)
    ]

    processed_fixtures = []
    for f in gw_fixtures if gw_fixtures else next_gw_fixtures:
        processed_fixtures.append(
            {
                "id": f.get("id"),
                "event": f.get("event"),
                "home_team": teams.get(f.get("team_h"), {}).get(
                    "name", "Unknown"
                ),
                "home_team_code": teams.get(f.get("team_h"), {}).get(
                    "short_name", "HOME"
                ),
                "away_team": teams.get(f.get("team_a"), {}).get(
                    "name", "Unknown"
                ),
                "away_team_code": teams.get(f.get("team_a"), {}).get(
                    "short_name", "AWAY"
                ),
                "home_score": f.get("team_h_score"),
                "away_score": f.get("team_a_score"),
                "finished": f.get("finished", False),
                "kickoff_time": f.get("kickoff_time"),
            }
        )

    # 3. Fetch League Standings & Detailed Manager Summaries
    league_res = requests.get(
        f"{API_BASE}/leagues-classic/{LEAGUE_ID}/standings/", headers=headers
    ).json()
    league_info = league_res.get("league", {})
    raw_standings = league_res.get("standings", {}).get("results", [])

    processed_standings = []
    manager_summaries = {}

    for entry in raw_standings:
        entry_id = entry["entry"]

        # History & Chip information
        history_res = requests.get(
            f"{API_BASE}/entry/{entry_id}/history/", headers=headers
        ).json()
        current_history = history_res.get("current", [])
        past_seasons = history_res.get("past", [])
        chips = history_res.get("chips", [])

        # Fetch Manager Picks for Current Gameweek
        picks_res = requests.get(
            f"{API_BASE}/entry/{entry_id}/event/{current_gw}/picks/",
            headers=headers,
        )
        picks = picks_res.json().get("picks", []) if picks_res.ok else []

        gw_history = [gw["total_points"] for gw in current_history]

        manager_obj = {
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
        processed_standings.append(manager_obj)

        manager_summaries[entry_id] = {
            "entry_id": entry_id,
            "entry_name": entry.get("entry_name"),
            "player_name": entry.get("player_name"),
            "overall_rank": entry.get("rank"),
            "total_points": entry.get("total"),
            "gw_points": entry.get("event_total"),
            "past_seasons": past_seasons,
            "chips_used": chips,
            "history": current_history,
        }

    # 4. Premier League Top Players
    top_prem_players = []
    try:
        elements = bootstrap_res.get("elements", [])
        sorted_elements = sorted(
            elements, key=lambda x: x.get("event_points", 0), reverse=True
        )[:4]
        for p in sorted_elements:
            top_prem_players.append(
                {
                    "name": p.get("web_name"),
                    "position": element_types.get(p.get("element_type"), ""),
                    "team": teams.get(p.get("team"), {}).get(
                        "short_name", "PL"
                    ),
                    "points": p.get("event_points", 0),
                }
            )
    except Exception as e:
        print(f"Error compiling top players: {e}")

    # 5. Export JSON
    final_data = {
        "league": {"id": league_info.get("id"), "name": league_info.get("name")},
        "gameweek": current_gw,
        "standings": {"results": processed_standings},
        "top_prem_players": top_prem_players,
        "fixtures": processed_fixtures,
        "manager_summaries": manager_summaries,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    with open("data.json", "w") as f:
        json.dump(final_data, f, indent=2)

    if os.path.exists("public"):
        with open("public/data.json", "w") as f:
            json.dump(final_data, f, indent=2)


if __name__ == "__main__":
    get_fpl_data()