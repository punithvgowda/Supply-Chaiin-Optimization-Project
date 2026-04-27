from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

class Shipment(Base):
    __tablename__ = 'shipments'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, unique=True, nullable=False)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    status = Column(String, default="In Transit") # In Transit, Delayed, Rerouted
    driver_name = Column(String)
    driver_phone = Column(String)
    driver_health_score = Column(Integer, default=100)
    driver_fatigue = Column(String, default="Low")
    driver_hr = Column(Integer, default=72)
    # --- AI & RISK ENGINE ---
    risk_score = Column(Integer, default=0) # 0-100
    delay_prob = Column(Integer, default=0) # percentage
    eta_deviation = Column(Float, default=0.0) # hours
    fuel_efficiency = Column(Float, default=15.5) # km/l
    carbon_footprint = Column(Float, default=0.0) # kg CO2
    autonomous_active = Column(Boolean, default=False)
    ai_reasoning = Column(String)

class LocationLog(Base):
    __tablename__ = 'location_logs'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    speed_kmh = Column(Float, nullable=False)
    weather_condition = Column(String, default="Clear")

class Alert(Base):
    __tablename__ = 'alerts'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    alert_type = Column(String, nullable=False) # e.g., "Low Speed", "Bad Weather"
    description = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # --- ACTIONABLE INTELLIGENCE ---
    recommendation = Column(String) # e.g., "Reroute via NH44"
    cause = Column(String) # e.g., "Heavy Rain + Port Congestion"
    severity = Column(String, default="Medium")

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class Hub(Base):
    __tablename__ = 'hubs'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(String, default="Active")
    manager_phone = Column(String)
    is_satellite = Column(Boolean, default=False)

class FloatingDepot(Base):
    __tablename__ = 'floating_depots'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    status = Column(String)

class Checkpoint(Base):
    __tablename__ = 'checkpoints'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    official_count = Column(Integer, default=1)

class SafetyLog(Base):
    __tablename__ = 'safety_logs'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, nullable=False)
    checkpoint_name = Column(String, nullable=False)
    status = Column(String, default="Cleared") # Cleared, Inspected, Delayed
    cargo_condition = Column(String, default="Intact") # Intact, Damaged, Compromised
    seal_integrity = Column(String, default="Verified") # Verified, Tampered, Re-sealed
    safety_rating = Column(String, default="100%")
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

class CustomerReview(Base):
    __tablename__ = 'customer_reviews'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, nullable=False)
    customer_name = Column(String)
    rating = Column(Integer) # 1 to 5
    comment = Column(String)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

class VehicleHealth(Base):
    __tablename__ = 'vehicle_health'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, unique=True, nullable=False)
    next_service = Column(String)
    fuel_range = Column(Integer) # in km
    fitness_certificate = Column(String) # Expiry Date or Status
    engine_condition = Column(String, default="Good")

class CarbonWallet(Base):
    __tablename__ = 'carbon_wallet'
    id = Column(Integer, primary_key=True)
    credits_available = Column(Float, default=1000.0)

class SimulationConfig(Base):
    __tablename__ = 'simulation_config'
    id = Column(Integer, primary_key=True)
    active_scenario = Column(String, default="Normal") # Normal, Storm, Congestion, Blackout
    last_updated = Column(DateTime, default=datetime.now(timezone.utc))

class BlockchainSwap(Base):
    __tablename__ = 'blockchain_swaps'
    id = Column(Integer, primary_key=True)
    truck_id = Column(String, nullable=False)
    original_carrier = Column(String)
    matched_carrier = Column(String)
    contract_address = Column(String)
    status = Column(String) # Validated, Completed
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

DB_PATH = 'supply_chain.db'
engine = create_engine(
    f'sqlite:///{DB_PATH}', 
    echo=False, 
    pool_size=20, 
    max_overflow=10, 
    pool_timeout=30
)
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

def get_session():
    return Session()

def close_session(session):
    session.close()
