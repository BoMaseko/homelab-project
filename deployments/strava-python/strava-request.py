import os
import json
import requests
import time
from datetime import datetime
from prometheus_client import start_http_server, Gauge

run_distance = Gauge("strava_run_distance_meters", "Distance of the last 5 Strava runs", ["name", "date"])

CLIENT_ID = "201127"
CLIENT_SECRET = "81845bccc04242e84c70250b4a1de01587c8c092"
TOKEN_FILE = "strava_tokens.json"

# Load tokens from file
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    else:
        return {"refresh_token": "", "access_token": ""}

# Save tokens to file
def save_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

# Refresh access token using stored refresh token
def refresh_access_token():
    tokens = load_tokens()
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise ValueError("No refresh token found in token file!")

    url = "https://www.strava.com/oauth/token"
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    resp = requests.post(url, data=payload)
    data = resp.json()
    tokens["access_token"] = data["access_token"]
    tokens["refresh_token"] = data["refresh_token"]
    save_tokens(tokens)
    return tokens["access_token"]

# Fetch latest Strava activities
def get_latest_activities(limit=5):
    token = refresh_access_token()
    url = "https://www.strava.com/api/v3/athlete/activities"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)

    if resp.status_code == 200:
        activities = resp.json()
        print(f"Last {limit} activities:")

        for act in activities[:limit]:
            name = act["name"]
            distance_m = act["distance"]
            distance_km = round(act["distance"] / 1000, 2)
            start_time = datetime.fromisoformat(act["start_date_local"].replace("Z",""))
            print(f"- {name} | {distance_km} km | {start_time}")
            
            #Update Prometheus metric
            run_distance.labels(name=name, date=start_time.isoformat()).set(distance_m)

    else:
        print("Failed to fetch activities:", resp.status_code, resp.text)

if __name__ == "__main__":
    start_http_server(9400) #Prometheus will scrape this port
    print("Prometheus metrics server running on port 9100...")

    while True:
        get_latest_activities(limit=5)
        time.sleep(60) # 60 seconds 

