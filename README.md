# TRANZITS | Resilient Smart Supply Chain Control Tower

**TRANZITS** is a next-generation AI-powered logistics platform designed to transform reactive supply chain management into a proactive, resilient operation. Built for high-stakes logistics environments, it leverages real-time telemetry and predictive analytics to mitigate disruptions before they impact the bottom line.

## 🌟 Hackathon Highlight: "Logistics Simulation Mode" (Hackathon Gold)
Most logistics platforms only tell you what's happening *now*. **TRANZITS** lets you see into the *future*. Our signature **Simulation Sandbox** allows operators to experiment with critical decisions before committing resources:
- **Change Courier Analysis:** Instant side-by-side comparison of cost, ETA, and carbon footprint when switching carriers.
- **Deferred Shipping Predictions:** What happens if we ship tomorrow? Our AI predicts risk reduction based on moving weather fronts.
- **Hybrid Splitting Logic:** Simulate splitting orders between Air and Ground freight to meet urgent deadlines without breaking the budget.

## 🚀 Core Features
- **Real-Time Telemetry & Anomaly Detection:** Constant monitoring of fleet velocity, driver health, and environmental conditions.
- **Predictive Disruption Engine:** Automated risk scoring for congestion, severe weather, and regional instability.
- **Dynamic AI Rerouting:** OSRM-integrated trajectory optimization that visualizes alternative paths in real-time.
- **Blockchain Capacity Swaps:** Transparent, automated carrier matching for capacity optimization during delays.
- **Carbon-Aware Logistics:** Real-time carbon footprint tracking with an integrated "Carbon Wallet" for offset management.
- **Context-Aware Sandbox:** A decision-support system that intelligently targets specific shipments for deep-dive simulation.

## 🛠 Tech Stack
- **Backend:** Flask (Python), SQLAlchemy, Pandas
- **Frontend:** Cyber-style UI with Vanilla JS, CSS Glassmorphism, and Leaflet.js
- **Intelligence:** Rule-based AI Engine + Predictive Modeling
- **API Integration:** OSRM (Open Source Routing Machine)
- **Database:** SQLite (Relational Log Storage)

## ⚙️ Installation & Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/Supply-Chaiin-Optimization-Project.git
   cd HACKATHON
   ```
2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run the Data Simulator (Terminal 1):**
   ```bash
   python data_simulator.py
   ```
4. **Run the Disruption Engine (Terminal 2):**
   ```bash
   python disruption_engine.py
   ```
5. **Start the Web Server (Terminal 3):**
   ```bash
   python app.py
   ```
6. **Open the Dashboard:**
   Visit `http://127.0.0.1:5000` in your browser.

## 📂 Project Structure
- `app.py`: Main Flask application and API endpoints.
- `disruption_engine.py`: Logic for detecting risks and creating alerts.
- `data_simulator.py`: Telemetry simulation script.
- `route_recommender.py`: OSRM API integration for alternative routes.
- `database.py`: SQLAlchemy models and database configuration.
- `static/`: Frontend assets (JS, CSS, Images).
- `templates/`: HTML templates for the dashboard.

## 📝 License
This project is licensed under the MIT License.
