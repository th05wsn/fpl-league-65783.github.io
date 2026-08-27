import requests
import json
import os

LEAGUE_ID = 65783
API_BASE = "https://fantasy.premierleague.com/api"

def get_fpl_data():
    # 1. Fetch General Info (Current Gameweek)
    bootstrap_res = requests.get(f"{API_BASE}/bootstrap-static/").json()
    current_gw = next(gw for gw in bootstrap_res['events'] if gw['is_current'])['id']
    
    # 2. Fetch League Standings
    league_res = requests.get(f"{API_BASE}/leagues-classic/{LEAGUE_ID}/standings/").json()
    standings = league_res['standings']['results']
    
    # 3. Process Tie Logic for Overall Standings
    # The FPL API already assigns the same 'rank' integer to tied players.
    processed_standings = []
    for entry in standings:
        processed_standings.append({
            "rank": entry['rank'],
            "manager": entry['player_name'],
            "team_name": entry['entry_name'],
            "gw_points": entry['event_total'],
            "total_points": entry['total'],
            "entry_id": entry['entry']
        })
        
    # 4. Process Tie Logic for Weekly High Scorers
    max_gw_points = max(s['gw_points'] for s in processed_standings)
    gw_top_scorers = [s for s in processed_standings if s['gw_points'] == max_gw_points]
    
    # 5. Fetch Trend Data for Chart (Top 5 Managers Only to save API calls)
    trend_data = {"labels": [f"GW {i}" for i in range(1, current_gw + 1)], "datasets": []}
    
    for manager in processed_standings[:5]:
        history_res = requests.get(f"{API_BASE}/entry/{manager['entry_id']}/history/").json()
        points_history = [gw['total_points'] for gw in history_res['current']]
        
        trend_data["datasets"].append({
            "label": manager['manager'],
            "data": points_history,
            "fill": False,
            "tension": 0.1
        })
    
    # 6. Compile Final JSON
    final_data = {
        "league_id": LEAGUE_ID,
        "gameweek": current_gw,
        "standings": processed_standings,
        "gw_top_scorers": gw_top_scorers,
        "trend_data": trend_data
    }
    
    # Save to file for GitHub Pages to serve
    os.makedirs("public", exist_ok=True)
    with open("public/fpl_data.json", "w") as f:
        json.dump(final_data, f)

if __name__ == "__main__":
    get_fpl_data()
