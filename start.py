import threading
import time
import subprocess
import sys
import os

def run_simulator():
    print("[START] Data Simulator starting...")
    while True:
        try:
            from data_simulator import generate_location_data
            generate_location_data()
        except Exception as e:
            print(f"[SIMULATOR ERROR] {e}")
        time.sleep(15)

def run_disruption_engine():
    print("[START] Disruption Engine starting...")
    time.sleep(10)  # wait for simulator to seed data first
    while True:
        try:
            from disruption_engine import analyze_disruptions
            analyze_disruptions()
        except Exception as e:
            print(f"[DISRUPTION ERROR] {e}")
        time.sleep(15)

def run_app():
    print("[START] Flask app starting...")
    from app import app
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

if __name__ == "__main__":
    # Start simulator in background thread
    t1 = threading.Thread(target=run_simulator, daemon=True)
    t1.start()

    # Start disruption engine in background thread
    t2 = threading.Thread(target=run_disruption_engine, daemon=True)
    t2.start()

    print("[START] All background services started. Launching Flask...")
    time.sleep(5)  # give simulator time to seed DB

    # Run Flask in main thread
    run_app()
