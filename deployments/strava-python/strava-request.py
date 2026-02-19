import os
import json
import requests
import time
from datetime import datetime
from prometheus_client import start_http_server, Gauge

# Prometheus Metrics
run_distance = Gauge(
    "strava_run_distance_meters", "Distance of the last 5 Strava runs", ["name", "date"]
)
run_elapsed = Gauge(
    "strava_run_elapsed_time_seconds", "Elapsed time of runs", ["name", "date"]
)
run_moving = Gauge(
    "strava_run_moving_time_seconds", "Moving time of runs", ["name", "date"]
)
run_elevation = Gauge(
    "strava_run_elevation_gain_meters", "Elevation gain of runs", ["name", "date"]
)
run_avg_speed = Gauge(
    "strava_run_average_speed_meters_per_second", "Average speed of runs", ["name", "date"]
)
run_count = Gauge("strava_run_count", "Number of runs returned by exporter")

# Strava API credentials
CLIENT_ID = os.environ.get("STRAVA_CLIENT_ID", "201127")
CLIENT_SECRET = os.environ.get("STRAVA_CLIENT_SECRET", "81845bccc04242e84c70250b4a1de01587c8c092")

# Token paths
TOKEN_FILE = "/app/data/strava_tokens.json"
SECRET_FILE = "/tmp/strava_tokens.json"

# Fetch interval (seconds)
FETCH_INTERVAL = int(os.environ.get("FETCH_INTERVAL", 300))  # 5 minutes recommended

# Ensure token file exists
os.makedirs("/app/data", exist_ok=True)
if not os.path.exists(TOKEN_FILE) and os.path.exists(SECRET_FILE):
    with open(SECRET_FILE, "r") as src, open(TOKEN_FILE, "w") as dst:
        dst.write(src.read())
        print(f"Copied secret from {SECRET_FILE} to {TOKEN_FILE}", flush=True)

# Load and save tokens
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return {"refresh_token": "", "access_token": ""}

def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)
    print("Tokens saved successfully.", flush=True)

# Refresh Strava access token
def refresh_access_token():
    tokens = load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("No refresh token found!", flush=True)
        return None

    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    try:
        resp = requests.post(url, data=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        tokens["access_token"] = data["access_token"]
        tokens["refresh_token"] = data["refresh_token"]
        save_tokens(tokens)
        return tokens["access_token"]
    except Exception as e:
        print(f"Failed to refresh token: {e}", flush=True)
        return None

# Fetch latest activities
def get_latest_activities(limit=5):
    token = refresh_access_token()
    if not token:
        print("Skipping activity fetch due to missing token.", flush=True)
        return

    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        activities = resp.json()
        run_count.set(len(activities[:limit]))
        print(f"Fetched {len(activities[:limit])} activities:", flush=True)

        for act in activities[:limit]:
            name = act["name"]
            distance_m = act["distance"]
            elapsed_s = act["elapsed_time"]
            moving_s = act["moving_time"]
            elev_m = act.get("total_elevation_gain", 0)
            avg_speed = act.get("average_speed", 0)
            start_time = datetime.fromisoformat(act["start_date_local"].replace("Z", ""))

            # Set metrics
            run_distance.labels(name=name, date=start_time.isoformat()).set(distance_m)
            run_elapsed.labels(name=name, date=start_time.isoformat()).set(elapsed_s)
            run_moving.labels(name=name, date=start_time.isoformat()).set(moving_s)
            run_elevation.labels(name=name, date=start_time.isoformat()).set(elev_m)
            run_avg_speed.labels(name=name, date=start_time.isoformat()).set(avg_speed)

            print(f"- {name} | {round(distance_m/1000,2)} km | {elapsed_s}s elapsed | {moving_s}s moving | {elev_m}m elev | {round(avg_speed,2)} m/s avg", flush=True)

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 429:
            print("Rate limited by Strava. Sleeping 15 minutes...", flush=True)
            time.sleep(900)  # 15 minutes
            return
        print(f"Failed to fetch activities: {e}", flush=True)
    except Exception as e:
        print(f"Failed to fetch activities: {e}", flush=True)

# Main
if __name__ == "__main__":
    start_http_server(9400)
    print("Strava Prometheus exporter running on :9400", flush=True)

    while True:
        get_latest_activities(limit=5)
        time.sleep(FETCH_INTERVAL)

