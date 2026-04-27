from database import get_session, Shipment, LocationLog, Hub, Checkpoint, SafetyLog, User
session = get_session()
print(f"Users: {session.query(User).count()}")
print(f"Shipments: {session.query(Shipment).count()}")
print(f"LocationLogs: {session.query(LocationLog).count()}")
print(f"Hubs: {session.query(Hub).count()}")
print(f"Checkpoints: {session.query(Checkpoint).count()}")
session.close()
