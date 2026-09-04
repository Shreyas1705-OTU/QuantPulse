import random

from app.database.connection import SessionLocal
from app.database.models import Device, User, Reading, Alert
from app.services.user_service import UserService
from app.core.security import hash_password

db = SessionLocal()

# ---------------------------------------------------
# Seed Devices
# ---------------------------------------------------

if db.query(Device).count() == 0:

    devices = [
        Device(
            name="Temperature Sensor",
            status="Online",
            location="Warehouse A",
        ),
        Device(
            name="Pressure Sensor",
            status="Offline",
            location="Warehouse B",
        ),
        Device(
            name="Gateway Device",
            status="Online",
            location="Main Office",
        ),
    ]

    db.add_all(devices)
    db.commit()

    print("Devices seeded.")

else:
    print("Devices already exist.")


# ---------------------------------------------------
# Seed Default Admin User
# ---------------------------------------------------

service = UserService(db)

user = service.get_user_by_username("shreyas")

if user is None:

    service.create_user(
        username="shreyas",
        email="shreyas@quantpulse.com",
        hashed_password=hash_password("Password123"),
        role="admin",
    )

    print("Default admin user created.")

else:
    print("Admin user already exists.")


# ---------------------------------------------------
# Seed Readings
# ---------------------------------------------------

if db.query(Reading).count() == 0:

    readings = []

    for device_id in [1, 2, 3]:

        for _ in range(10):

            readings.append(
                Reading(
                    device_id=device_id,
                    temperature=round(random.uniform(20.0, 35.0), 1),
                    humidity=round(random.uniform(35.0, 70.0), 1),
                    battery=random.randint(60, 100),
                )
            )

    db.add_all(readings)
    db.commit()

    print("Sample readings created.")

else:

    print("Readings already exist.")


# ---------------------------------------------------
# Seed Alerts
# ---------------------------------------------------

if db.query(Alert).count() == 0:

    alerts = [

        Alert(
            device_id=1,
            message="Temperature exceeded threshold",
            severity="High",
        ),

        Alert(
            device_id=2,
            message="Pressure sensor offline",
            severity="Critical",
        ),

        Alert(
            device_id=3,
            message="Gateway battery below 70%",
            severity="Medium",
        ),
    ]

    db.add_all(alerts)
    db.commit()

    print("Sample alerts created.")

else:

    print("Alerts already exist.")


db.close()

print("Database seeded successfully!")