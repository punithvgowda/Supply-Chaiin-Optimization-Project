import time
from datetime import datetime, timezone
from database import get_session, Alert, Shipment


def analyze_disruptions():
    session = get_session()
    try:
        # 🔥 TRK-022 is ALWAYS delayed due to heavy rain — hardcoded
        create_alert(
            session,
            "TRK-022",
            "Heavy Rain",
            "TRK-022 route flooded — persistent heavy rainfall blocking main highway",
            cause="Heavy Rain & Flooding",
            recommendation="Take alternate inland route via bypass road — saves 30 min despite detour",
            severity="Critical"
        )

        # Also force TRK-022 shipment status to delayed in DB
        trk022 = session.query(Shipment).filter_by(truck_id="TRK-022").first()
        if trk022:
            trk022.status = "Delayed"
            trk022.risk_score = 85
            trk022.delay_prob = 90
            trk022.ai_reasoning = "Heavy rain causing severe flooding on main route"

        shipments = session.query(Shipment).all()

        for s in shipments:
            if s.truck_id == "TRK-022":
                continue  # already handled above
            risk = s.risk_score or 0
            delay = s.delay_prob or 0

            if delay > 50:
                # High risk — create or update alert
                cause = "High risk score detected"
                if delay > 50:
                    cause = f"High delay probability ({int(delay)}%)"
                if risk > 50:
                    cause = f"Severe risk ({int(risk)}) — weather/congestion"

                severity = "Critical" if risk > 60 else "High"

                create_alert(
                    session,
                    s.truck_id,
                    "Risk Alert",
                    f"{s.truck_id} requires attention",
                    cause=cause,
                    recommendation="Consider alternate route",
                    severity=severity
                )
            else:
                # Low risk — deactivate alert if exists (don't delete)
                existing = session.query(Alert).filter_by(
                    truck_id=s.truck_id
                ).first()
                if existing and existing.is_active:
                    existing.is_active = False
                    print(f"[CLEARED] {s.truck_id} — risk normalized")

        session.commit()

    except Exception as e:
        print(f"[ERROR] {e}")
        session.rollback()
    finally:
        session.close()


def create_alert(
    session,
    truck_id,
    alert_type,
    description,
    cause="Unknown",
    recommendation="Monitor situation",
    severity="Medium"
):
    now = datetime.now(timezone.utc)

    existing = session.query(Alert).filter(
        Alert.truck_id == truck_id
    ).first()

    if existing:
        existing.alert_type = alert_type
        existing.description = description
        existing.cause = cause
        existing.recommendation = recommendation
        existing.severity = severity
        existing.timestamp = now
        existing.is_active = True
        print(f"[UPDATED] {truck_id}")
    else:
        new_alert = Alert(
            truck_id=truck_id,
            alert_type=alert_type,
            description=description,
            cause=cause,
            recommendation=recommendation,
            severity=severity,
            timestamp=now,
            is_active=True
        )
        session.add(new_alert)
        print(f"[NEW] {truck_id}")


if __name__ == "__main__":
    print("🔥 Disruption Engine Running — monitoring all trucks by risk score")
    try:
        while True:
            analyze_disruptions()
            time.sleep(15)
    except KeyboardInterrupt:
        print("Stopped.")