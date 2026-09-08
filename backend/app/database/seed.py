from app.database.connection import SessionLocal
from app.database.models import Symbol
from app.services.user_service import UserService
from app.core.security import hash_password

db = SessionLocal()

# ---------------------------------------------------
# Seed Symbols
# ---------------------------------------------------

if db.query(Symbol).count() == 0:

    symbols = [
        Symbol(ticker="AAPL", display_name="Apple Inc.", asset_type="equity"),
        Symbol(ticker="TSLA", display_name="Tesla, Inc.", asset_type="equity"),
        Symbol(ticker="NVDA", display_name="NVIDIA Corporation", asset_type="equity"),
        Symbol(ticker="MSFT", display_name="Microsoft Corporation", asset_type="equity"),
        Symbol(ticker="GOOGL", display_name="Alphabet Inc.", asset_type="equity"),
        Symbol(ticker="AMZN", display_name="Amazon.com, Inc.", asset_type="equity"),
        Symbol(ticker="META", display_name="Meta Platforms, Inc.", asset_type="equity"),
        Symbol(ticker="OANDA:EUR_USD", display_name="Euro / US Dollar", asset_type="forex"),
        # Replaced SPY (equity) -- confirmed via real tick counts on two
        # independent clusters (Kind and a fresh AKS deploy) that Finnhub's
        # free tier streams almost no SPY trade volume (2 ticks in over an
        # hour of open market vs. hundreds for every other equity in the
        # same batch) -- not a bug on our end, just a starved data source.
        # USD/CAD is a second, distinct forex pair instead.
        Symbol(ticker="OANDA:USD_CAD", display_name="US Dollar / Canadian Dollar", asset_type="forex"),
        Symbol(ticker="BINANCE:BTCUSDT", display_name="Bitcoin / Tether", asset_type="crypto"),
    ]

    db.add_all(symbols)
    db.commit()

    print("Symbols seeded.")

else:
    print("Symbols already exist.")


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
# Ticks and alerts are populated by the real Finnhub
# ingestion service and Phase 3 anomaly detection --
# no fake data seeded here anymore.
# ---------------------------------------------------

db.close()

print("Database seeded successfully!")
