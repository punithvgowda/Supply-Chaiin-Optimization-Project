import time
import random
import requests
from datetime import datetime
from database import get_session, User, Shipment, LocationLog, Hub, CarbonWallet, SimulationConfig, Alert

API_KEY = "7a7d9b180f70e0a3e92007a04d6837a3"

# Cache with TIMESTAMP so it expires every 60 seconds
weather_cache = {}
WEATHER_CACHE_TTL = 60  # seconds

def get_real_weather(lat, lng):
    key = f"{round(lat, 2)}_{round(lng, 2)}"
    now = time.time()

    # Check cache — only use if less than 60 seconds old
    if key in weather_cache:
        cached_value, cached_time = weather_cache[key]
        if now - cached_time < WEATHER_CACHE_TTL:
            return cached_value

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={API_KEY}"
        response = requests.get(url, timeout=5).json()

        weather = response['weather'][0]['main']
        city = response.get('name', '').strip()

        # If city is empty, use nearest town from sys.name or country
        if not city:
            country = response.get('sys', {}).get('country', '')
            city = f"Region {country}" if country else f"Lat {round(lat,1)}"

        if weather in ["Rain", "Drizzle"]:
            weather = "Rainy"
        elif weather in ["Thunderstorm"]:
            weather = "Stormy"
        else:
            weather = "Clear"

        result = f"{city} | {weather}"

        # Store with timestamp
        weather_cache[key] = (result, now)
        print(f"[WEATHER] Fetched fresh: {result}")
        return result

    except Exception as e:
        print(f"[WEATHER ERROR] {e}")
        # Return stale cache if exists, else fallback
        if key in weather_cache:
            return weather_cache[key][0]
        return "Unknown | Clear"


TRUCKS = [f"TRK-{str(i).zfill(3)}" for i in range(1, 25)]

HUBS_CONFIG = [
    {"name": "New York Hub",     "lat": 40.71,  "lng": -74.00},
    {"name": "Los Angeles Hub",  "lat": 34.05,  "lng": -118.24},
    {"name": "Mumbai Hub",       "lat": 19.07,  "lng": 72.87},
    {"name": "Delhi Hub",        "lat": 28.61,  "lng": 77.20},
    {"name": "London Hub",       "lat": 51.50,  "lng": -0.12},
    {"name": "Manchester Hub",   "lat": 53.48,  "lng": -2.24},
    {"name": "Tokyo Hub",        "lat": 35.68,  "lng": 139.69},
    {"name": "Osaka Hub",        "lat": 34.69,  "lng": 135.50},
]

truck_progress = {}
JOURNEY_STEPS = 60

def lerp(a, b, t):
    return a + (b - a) * t


def initialize_db_data(session):
    if session.query(User).count() == 0:
        session.add(User(username="admin", email="admin@example.com", password="password"))

    if session.query(Hub).count() == 0:
        for h in HUBS_CONFIG:
            session.add(Hub(name=h["name"], lat=h["lat"], lng=h["lng"], status="Active"))

    if session.query(CarbonWallet).count() == 0:
        session.add(CarbonWallet(credits_available=50000))

    session.commit()


def generate_location_data():
    session = get_session()

    try:
        initialize_db_data(session)

        sim_config = session.query(SimulationConfig).first()
        if not sim_config:
            sim_config = SimulationConfig(active_scenario="Normal")
            session.add(sim_config)
            session.commit()

        hubs = session.query(Hub).all()
        hub_map = {h.name: h for h in hubs}

        for i, tid in enumerate(TRUCKS):

            # 🔥 TRK-022: ALWAYS rainy + delayed — skip normal logic
            if tid == "TRK-022":
                shipment = session.query(Shipment).filter_by(truck_id=tid).first()
                if not shipment:
                    origin = hubs[i % len(hubs)]
                    dest = hubs[(i + 1) % len(hubs)]
                    shipment = Shipment(
                        truck_id=tid,
                        origin=origin.name,
                        destination=dest.name,
                        status="Delayed"
                    )
                    session.add(shipment)
                    session.flush()

                # Force rain values — always
                shipment.status = "Delayed"
                shipment.risk_score = 85
                shipment.delay_prob = 90
                shipment.ai_reasoning = "Heavy rain & flooding on main highway. Alternate route required."

                # Get current position for log
                if tid not in truck_progress:
                    truck_progress[tid] = {"step": (i * 3) % JOURNEY_STEPS, "direction": 1}
                prog = truck_progress[tid]
                t_val = prog["step"] / JOURNEY_STEPS
                o = hub_map[shipment.origin]
                d = hub_map[shipment.destination]
                lat = lerp(o.lat, d.lat, t_val)
                lng = lerp(o.lng, d.lng, t_val)

                session.add(LocationLog(
                    truck_id=tid,
                    lat=lat,
                    lng=lng,
                    speed_kmh=random.uniform(20, 40),  # slow due to rain
                    weather_condition=f"Flooded Zone | Rainy",
                    timestamp=datetime.utcnow()
                ))

                # Keep TRK-022 alert ALIVE — never deactivate it
                existing_alert = session.query(Alert).filter_by(truck_id="TRK-022").first()
                if existing_alert:
                    existing_alert.is_active = True
                    existing_alert.cause = "Heavy Rain & Flooding on Highway"
                    existing_alert.recommendation = "Take alternate inland bypass — avoids flood zone"
                    existing_alert.severity = "Critical"
                else:
                    session.add(Alert(
                        truck_id="TRK-022",
                        alert_type="Heavy Rain",
                        description="TRK-022 main route flooded — heavy rainfall blocking highway",
                        cause="Heavy Rain & Flooding on Highway",
                        recommendation="Take alternate inland bypass — avoids flood zone",
                        severity="Critical",
                        timestamp=datetime.utcnow(),
                        is_active=True
                    ))

                # Move progress
                prog["step"] += prog["direction"]
                if prog["step"] >= JOURNEY_STEPS:
                    prog["direction"] = -1
                elif prog["step"] <= 0:
                    prog["direction"] = 1

                continue  # skip rest of loop for TRK-022

            # ---- ALL OTHER TRUCKS: normal real-weather logic ----
            shipment = session.query(Shipment).filter_by(truck_id=tid).first()

            if not shipment:
                origin = hubs[i % len(hubs)]
                dest = hubs[(i + 1) % len(hubs)]
                shipment = Shipment(
                    truck_id=tid,
                    origin=origin.name,
                    destination=dest.name,
                    status="In Transit"
                )
                session.add(shipment)
                session.flush()

            # Movement
            if tid not in truck_progress:
                truck_progress[tid] = {"step": (i * 3) % JOURNEY_STEPS, "direction": 1}

            prog = truck_progress[tid]
            t_val = prog["step"] / JOURNEY_STEPS

            o = hub_map[shipment.origin]
            d = hub_map[shipment.destination]

            lat = lerp(o.lat, d.lat, t_val)
            lng = lerp(o.lng, d.lng, t_val)

            # 🌍 REAL WEATHER — refreshes every 60s
            weather_full = get_real_weather(lat, lng)
            weather = weather_full.split("|")[1].strip()

            # Traffic — weighted so it actually changes meaningfully
            traffic_roll = random.random()
            if traffic_roll < 0.3:
                traffic = "Low"
            elif traffic_roll < 0.65:
                traffic = "Moderate"
            else:
                traffic = "High"

            # Speed — varies realistically based on traffic + weather
            base_speed = random.uniform(60, 95)
            if traffic == "High":
                base_speed *= random.uniform(0.45, 0.65)   # heavy traffic slows a lot
            elif traffic == "Moderate":
                base_speed *= random.uniform(0.70, 0.85)
            if weather == "Rainy":
                base_speed *= random.uniform(0.75, 0.88)
            elif weather == "Stormy":
                base_speed *= random.uniform(0.50, 0.70)
            speed = round(max(15, min(base_speed, 110)), 1)

            # Risk logic — more dynamic range
            risk = 0
            if speed < 25:
                risk += 45
            elif speed < 45:
                risk += 25
            elif speed < 60:
                risk += 10

            if weather == "Rainy":
                risk += random.randint(15, 30)
            elif weather == "Stormy":
                risk += random.randint(35, 50)

            if traffic == "High":
                risk += random.randint(20, 35)
            elif traffic == "Moderate":
                risk += random.randint(8, 18)

            # Time-of-day simulation — peak hours add risk
            hour = datetime.utcnow().hour
            if 7 <= hour <= 9 or 17 <= hour <= 19:
                risk += random.randint(10, 20)  # rush hour

            risk += random.randint(-8, 12)  # noise
            risk = max(0, min(risk, 100))

            # Delay prob — not just risk*factor, adds independent variation
            delay = int(risk * random.uniform(0.6, 1.0))
            delay = max(0, min(delay + random.randint(-5, 10), 99))

            # Force update — bypass SQLAlchemy cache
            if risk > 70:
                new_status = "Delayed"
            elif risk > 40:
                new_status = "At Risk"
            else:
                new_status = "In Transit"

            session.query(Shipment).filter_by(truck_id=tid).update({
                "risk_score": risk,
                "delay_prob": delay,
                "status": new_status,
                "ai_reasoning": f"{weather} weather with {traffic} traffic. Risk {risk}%"
            }, synchronize_session="fetch")

            print(f"[{tid}] speed={speed} risk={risk} delay={delay}% status={new_status}")

            # 🔥 DO NOT wipe alerts here — let disruption_engine manage them
            # (old code had: session.query(Alert).filter_by(truck_id=tid).update({"is_active": False}))
            # That was killing all alerts including TRK-022!

            # UPDATE existing log if exists, else insert — prevents stale reads
            existing_log = session.query(LocationLog)                .filter_by(truck_id=tid)                .order_by(LocationLog.timestamp.desc())                .first()
            if existing_log:
                existing_log.lat = lat
                existing_log.lng = lng
                existing_log.speed_kmh = speed
                existing_log.weather_condition = weather_full
                existing_log.timestamp = datetime.utcnow()
            else:
                session.add(LocationLog(
                    truck_id=tid,
                    lat=lat,
                    lng=lng,
                    speed_kmh=speed,
                    weather_condition=weather_full,
                    timestamp=datetime.utcnow()
                ))

            # Move progress
            prog["step"] += prog["direction"]
            if prog["step"] >= JOURNEY_STEPS:
                prog["direction"] = -1
            elif prog["step"] <= 0:
                prog["direction"] = 1

        session.commit()
        print(f"[SIMULATOR] Cycle done at {datetime.utcnow().strftime('%H:%M:%S')}")

    except Exception as e:
        print(f"[SIMULATOR ERROR] {e}")
        session.rollback()

    finally:
        session.close()


if __name__ == "__main__":
    print("🚛 Data Simulator Running — weather refreshes every 60s, TRK-022 always rainy")
    while True:
        generate_location_data()
        time.sleep(15)  # run every 15s, but weather cache expires at 60s