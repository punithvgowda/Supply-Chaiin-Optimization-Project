from flask import Flask, render_template, jsonify, session
from flask import request, redirect
from database import (
    get_session, Shipment, LocationLog, Alert, User, Hub,
    CarbonWallet, SafetyLog, CustomerReview
)
from datetime import datetime, timezone
import threading
import time
import math
import os

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = "hackathon-secret-key"


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        session['username'] = username or "Operator"
        return redirect('/')
    return render_template('login.html')

# ---------------- USER ----------------
@app.route('/api/user')
def get_user():
    return jsonify({"username": session.get("username", "Guest")})


# ---------------- MAIN ----------------

@app.route('/')
def index():
    if 'username' not in session:
        return redirect('/login')
    return render_template('index.html', username=session.get('username'))


# ---------------- SHIPMENTS ----------------
@app.route('/api/shipments')
def api_shipments():
    db = get_session()
    try:
        shipments = db.query(Shipment).all()
        result = []

        for s in shipments:
            latest = db.query(LocationLog)\
                .filter_by(truck_id=s.truck_id)\
                .order_by(LocationLog.timestamp.desc())\
                .first()

            if latest and latest.lat and latest.lng:
                weather_raw = latest.weather_condition or "Clear"
                # Return full "City | Condition" string for display under velocity
                weather = weather_raw.strip() if weather_raw else "Clear"
                lat, lng = latest.lat, latest.lng
                speed = latest.speed_kmh or 0
            else:
                weather = "Clear"
                lat, lng = 20.59, 78.96
                speed = 50

            result.append({
                "truck_id": s.truck_id,
                "origin": s.origin,
                "destination": s.destination,
                "status": s.status,
                "driver": {
                    "name": s.driver_name or "Unknown",
                    "phone": s.driver_phone or "N/A"
                },
                "risk": s.risk_score or 10,
                "prob": s.delay_prob or 10,
                "dev": s.eta_deviation or 1,
                "carbon": round(s.carbon_footprint or 50, 2),
                "reason": s.ai_reasoning or "Optimal route",
                "location": {"lat": lat, "lng": lng},
                "speed": speed,
                "weather": weather
            })

        return jsonify(result)
    finally:
        db.close()


# ---------------- CONTROL TOWER ----------------
@app.route('/api/control_tower')
def api_control_tower():
    db = get_session()
    try:
        hubs = db.query(Hub).all()
        wallet = db.query(CarbonWallet).first()

        alerts = db.query(Alert)\
            .filter_by(is_active=True)\
            .order_by(Alert.timestamp.desc())\
            .limit(5)\
            .all()

        # 🔥 TRK-022 ALWAYS appears in disruptions — force inject if missing
        trk022_in_alerts = any(a.truck_id == "TRK-022" for a in alerts)
        if not trk022_in_alerts:
            from database import Alert as AlertModel
            fake_022 = AlertModel(
                truck_id="TRK-022",
                alert_type="Heavy Rain",
                description="TRK-022 main route flooded — heavy rainfall blocking highway",
                cause="Heavy Rain & Flooding on Highway",
                recommendation="Take alternate inland bypass — avoids flood zone",
                severity="Critical",
                is_active=True
            )
            alerts = [fake_022] + list(alerts)

        safety_logs = db.query(SafetyLog).limit(3).all()
        reviews = db.query(CustomerReview).limit(3).all()

        if not safety_logs:
            safety_logs = [
                type("obj", (), {"truck_id": "TRK-001", "cargo_condition": "Intact", "seal_integrity": "Verified"})()
            ]
        if not reviews:
            reviews = [
                type("obj", (), {"customer_name": "Amazon", "rating": 5, "comment": "Fast delivery"})()
            ]

        return jsonify({
            "hubs": [{
                "name": h.name,
                "lat": h.lat,
                "lng": h.lng,
                "status": h.status,
                "manager": getattr(h, "manager_phone", "N/A")
            } for h in hubs],
            "carbon_credits": wallet.credits_available if wallet else 50000,
            "alerts": [{
                "truck_id": a.truck_id,
                "type": a.alert_type,
                "desc": a.description or "",
                "cause": a.cause or "Unknown",
                "rec": a.recommendation or "Monitor",
                "sev": a.severity or "High",
                "delay": getattr(a, 'delay_prob', 100)
            } for a in alerts],
            "safety_logs": [{
                "id": l.truck_id,
                "cargo": l.cargo_condition,
                "seal": l.seal_integrity
            } for l in safety_logs],
            "reviews": [{
                "name": r.customer_name,
                "rating": r.rating,
                "comment": r.comment
            } for r in reviews]
        })
    finally:
        db.close()


# ---------------- ROUTE (FIXED - returns alt_route when risk is high) ----------------
@app.route('/api/route/<truck_id>')
def api_route(truck_id):
    db = get_session()
    try:
        shipment = db.query(Shipment).filter_by(truck_id=truck_id).first()
        if not shipment:
            return jsonify({"error": "Truck not found"}), 404

        latest = db.query(LocationLog)\
            .filter_by(truck_id=truck_id)\
            .order_by(LocationLog.timestamp.desc())\
            .first()

        origin_hub = db.query(Hub).filter_by(name=shipment.origin).first()
        dest_hub = db.query(Hub).filter_by(name=shipment.destination).first()

        current_lat = latest.lat if latest and latest.lat else 20.59
        current_lng = latest.lng if latest and latest.lng else 78.96

        origin_lat = origin_hub.lat if origin_hub else 28.6
        origin_lng = origin_hub.lng if origin_hub else 77.2
        dest_lat = dest_hub.lat if dest_hub else 19.07
        dest_lng = dest_hub.lng if dest_hub else 72.87

        active_alert = db.query(Alert)\
            .filter_by(truck_id=truck_id, is_active=True)\
            .first()

        alt_route = None
        recommendation = None

        is_trk022 = (truck_id == "TRK-022")
        delay = shipment.delay_prob or 0

        if is_trk022 or (delay > 50):
            # Midpoint between CURRENT and DESTINATION
            mid_lat = (current_lat + dest_lat) / 2
            mid_lng = (current_lng + dest_lng) / 2

            # Direction vector from current to destination
            dlat = dest_lat - current_lat
            dlng = dest_lng - current_lng

            # Perpendicular offset — pushes waypoint sideways (not random direction)
            # Normalized perpendicular: (-dlng, dlat)
            import math
            length = math.sqrt(dlat**2 + dlng**2) or 1
            perp_lat = -dlng / length
            perp_lng = dlat / length

            # Offset amount — 15% of route length, enough to show detour clearly
            offset_amount = length * 0.25

            if is_trk022:
                offset_lat = mid_lat + perp_lat * offset_amount
                offset_lng = mid_lng + perp_lng * offset_amount
                recommendation = (
                    "🌧️ HEAVY RAIN & FLOODING on main highway! "
                    "Alternate inland bypass route recommended. "
                    "Detour adds ~35 min but avoids flood zone completely."
                )
            else:
                offset_lat = mid_lat + perp_lat * offset_amount
                offset_lng = mid_lng + perp_lng * offset_amount
                cause = active_alert.cause if active_alert else f"High delay ({delay}%)"
                recommendation = f"⚠️ Delay at {delay}% — Alternate route recommended. {cause}. Estimated detour: +30 min."

            alt_route = {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [current_lng, current_lat],          # where truck is now
                        [offset_lng, offset_lat],             # bypass waypoint
                        [dest_lng, dest_lat]                  # actual destination
                    ]
                },
                "properties": {}
            }

        return jsonify({
            "truck_id": truck_id,
            "status": shipment.status,
            "origin": {"lat": origin_lat, "lng": origin_lng},
            "destination": {"lat": dest_lat, "lng": dest_lng},
            "current": {"lat": current_lat, "lng": current_lng},
            "alt_route": alt_route,
            "recommendation": recommendation
        })

    finally:
        db.close()


# ---------------- ANALYZE (NOW WORKS PER TRUCK) ----------------
@app.route('/api/analyze/<truck_id>')
def analyze_now(truck_id):
    db = get_session()
    try:
        shipment = db.query(Shipment).filter_by(truck_id=truck_id).first()
        if not shipment:
            return jsonify({"status": "not_found"}), 404

        # 🔥 TRK-022 ALWAYS critical — heavy rain hardcoded
        if truck_id == "TRK-022":
            shipment.status = "Delayed"
            shipment.risk_score = 85
            shipment.delay_prob = 90
            shipment.ai_reasoning = "Heavy rain causing severe flooding on main route"
            existing = db.query(Alert).filter_by(truck_id="TRK-022").first()
            if existing:
                existing.alert_type = "Heavy Rain"
                existing.description = "TRK-022 main route flooded — heavy rainfall"
                existing.cause = "Heavy Rain & Flooding on Highway"
                existing.recommendation = "Take alternate inland bypass — avoids flood zone"
                existing.severity = "Critical"
                existing.timestamp = datetime.now(timezone.utc)
                existing.is_active = True
            else:
                db.add(Alert(
                    truck_id="TRK-022",
                    alert_type="Heavy Rain",
                    description="TRK-022 main route flooded — heavy rainfall",
                    cause="Heavy Rain & Flooding on Highway",
                    recommendation="Take alternate inland bypass — avoids flood zone",
                    severity="Critical",
                    timestamp=datetime.now(timezone.utc),
                    is_active=True
                ))
            db.commit()
            return jsonify({"status": "rain_alert", "alt_route": True})

        risk = shipment.risk_score or 0
        delay = shipment.delay_prob or 0

        # Only create alert + show alt route when delay > 50%
        if delay > 50:
            existing = db.query(Alert).filter_by(truck_id=truck_id).first()

            cause = "High risk score detected"
            if delay > 50:
                cause = f"High delay probability ({int(delay)}%)"
            if risk > 50:
                cause = f"Severe risk score ({int(risk)}) — possible weather/congestion"

            if existing:
                existing.alert_type = "Risk Alert"
                existing.description = f"{truck_id} requires immediate attention"
                existing.cause = cause
                existing.recommendation = "Consider alternate route or delay shipment"
                existing.severity = "Critical" if risk > 60 else "High"
                existing.timestamp = datetime.now(timezone.utc)
                existing.is_active = True
            else:
                db.add(Alert(
                    truck_id=truck_id,
                    alert_type="Risk Alert",
                    description=f"{truck_id} requires immediate attention",
                    cause=cause,
                    recommendation="Consider alternate route or delay shipment",
                    severity="Critical" if risk > 60 else "High",
                    timestamp=datetime.now(timezone.utc),
                    is_active=True
                ))
            db.commit()
            return jsonify({"status": "alert_created", "delay": delay, "alt_route": True})
        else:
            # Delay <= 50% — deactivate alert, no alternate route needed
            existing = db.query(Alert).filter_by(truck_id=truck_id).first()
            if existing:
                existing.is_active = False
                db.commit()
            return jsonify({"status": "ok", "delay": delay, "alt_route": False})

    finally:
        db.close()


# ---------------- DISRUPTION ENGINE (DISABLED) ----------------
def start_disruption_engine():
    while False:
        time.sleep(10)


# ---------------- RUN ----------------
if __name__ == '__main__':
    # ✅ Always run engine (safe for hackathon)
    t = threading.Thread(target=start_disruption_engine, daemon=True)
    t.start()

    # ✅ Use Render port
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
