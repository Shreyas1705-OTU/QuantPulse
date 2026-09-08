"""
Service-layer tests against a real Postgres. Covers the query logic
that's easy to get subtly wrong: DISTINCT ON tiebreaking, count vs.
capped-list consistency, and the "fall back to latest" summary logic.
"""

from datetime import datetime, timedelta, timezone

from app.services.alert_service import AlertService
from app.services.summary_service import SummaryService
from app.services.symbol_service import SymbolService
from app.services.tick_service import TickService
from app.services.user_service import UserService
from app.database.models import DailySummary, SymbolSummary


def _ts(minutes_ago):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)


class TestTickService:
    def test_create_and_count(self, db_session, symbol_ids):
        service = TickService(db_session)
        for i in range(5):
            service.create_tick(symbol_ids["AAPL"], price=100.0 + i, volume=10, traded_at=_ts(i))
        assert service.count_ticks() == 5

    def test_get_all_ticks_respects_limit_and_newest_first(self, db_session, symbol_ids):
        service = TickService(db_session)
        for i in range(10):
            # Oldest tick first (_ts(9) is 9 minutes ago), so index 0 in
            # the loop is the oldest and should sort LAST.
            service.create_tick(symbol_ids["AAPL"], price=float(i), volume=10, traded_at=_ts(9 - i))

        result = service.get_all_ticks(limit=3)
        assert len(result) == 3
        # Newest traded_at first.
        assert [t.price for t in result] == [9.0, 8.0, 7.0]

    def test_get_ticks_for_symbol_only_returns_that_symbol(self, db_session, symbol_ids):
        service = TickService(db_session)
        service.create_tick(symbol_ids["AAPL"], price=1.0, volume=1, traded_at=_ts(1))
        service.create_tick(symbol_ids["TSLA"], price=2.0, volume=1, traded_at=_ts(1))

        result = service.get_ticks_for_symbol(symbol_ids["AAPL"])
        assert len(result) == 1
        assert result[0].symbol_id == symbol_ids["AAPL"]

    def test_get_latest_tick_per_symbol_returns_one_row_per_symbol(
        self, db_session, symbol_ids
    ):
        service = TickService(db_session)
        # 3 ticks for AAPL, 1 for TSLA, 0 for MSFT.
        for i in range(3):
            service.create_tick(symbol_ids["AAPL"], price=float(i), volume=10, traded_at=_ts(3 - i))
        service.create_tick(symbol_ids["TSLA"], price=99.0, volume=10, traded_at=_ts(1))

        result = service.get_latest_tick_per_symbol()
        by_symbol = {t.symbol_id: t for t in result}

        assert set(by_symbol) == {symbol_ids["AAPL"], symbol_ids["TSLA"]}
        # AAPL's latest is the one fed last (i=2, most recent traded_at).
        assert by_symbol[symbol_ids["AAPL"]].price == 2.0

    def test_get_latest_tick_per_symbol_tiebreaks_on_id_desc(self, db_session, symbol_ids):
        # Two ticks sharing the exact same traded_at -- DISTINCT ON's
        # deterministic tiebreaker (id.desc()) must pick the
        # higher-id (later-inserted) one, not an arbitrary one.
        service = TickService(db_session)
        same_ts = _ts(1)
        first = service.create_tick(symbol_ids["AAPL"], price=1.0, volume=10, traded_at=same_ts)
        second = service.create_tick(symbol_ids["AAPL"], price=2.0, volume=10, traded_at=same_ts)
        assert second.id > first.id

        result = service.get_latest_tick_per_symbol()
        assert len(result) == 1
        assert result[0].id == second.id
        assert result[0].price == 2.0


class TestAlertService:
    def test_create_and_count(self, db_session, symbol_ids):
        service = AlertService(db_session)
        for _ in range(4):
            service.create_alert(symbol_ids["AAPL"], "Test", "HIGH")
        assert service.count_alerts() == 4

    def test_get_alerts_for_symbol_filters_correctly(self, db_session, symbol_ids):
        service = AlertService(db_session)
        service.create_alert(symbol_ids["AAPL"], "AAPL alert", "HIGH")
        service.create_alert(symbol_ids["TSLA"], "TSLA alert", "MEDIUM")

        result = service.get_alerts_for_symbol(symbol_ids["AAPL"])
        assert len(result) == 1
        assert result[0].message == "AAPL alert"


class TestSymbolService:
    def test_get_symbol_by_ticker(self, db_session, symbol_ids):
        service = SymbolService(db_session)
        symbol = service.get_symbol_by_ticker("AAPL")
        assert symbol is not None
        assert symbol.id == symbol_ids["AAPL"]

    def test_get_symbol_by_ticker_unknown_returns_none(self, db_session, symbol_ids):
        service = SymbolService(db_session)
        assert service.get_symbol_by_ticker("NOPE") is None

    def test_create_update_delete_round_trip(self, db_session, symbol_ids):
        service = SymbolService(db_session)
        created = service.create_symbol("GOOGL", "Alphabet Inc.", "equity")
        assert created.id is not None

        updated = service.update_symbol(
            created.id, "GOOGL", "Alphabet Inc. (updated)", "equity", False
        )
        assert updated.display_name == "Alphabet Inc. (updated)"
        assert updated.is_active is False

        assert service.delete_symbol(created.id) is True
        assert service.get_symbol(created.id) is None

    def test_delete_nonexistent_symbol_returns_false(self, db_session, symbol_ids):
        service = SymbolService(db_session)
        assert service.delete_symbol(999999) is False


class TestUserService:
    def test_create_and_lookup(self, db_session):
        service = UserService(db_session)
        service.create_user("alice", "alice@example.com", "hashed", role="admin")

        by_username = service.get_user_by_username("alice")
        by_email = service.get_user_by_email("alice@example.com")
        assert by_username.id == by_email.id
        assert by_username.role == "admin"

    def test_unknown_username_returns_none(self, db_session):
        service = UserService(db_session)
        assert service.get_user_by_username("nobody") is None


class TestSummaryService:
    def test_get_latest_summary_falls_back_across_dates(self, db_session):
        db_session.add(
            DailySummary(
                summary_date=datetime.now(timezone.utc).date() - timedelta(days=2),
                summary_text="two days ago",
            )
        )
        db_session.add(
            DailySummary(
                summary_date=datetime.now(timezone.utc).date() - timedelta(days=1),
                summary_text="yesterday",
            )
        )
        db_session.commit()

        service = SummaryService(db_session)
        latest = service.get_latest_summary()
        # No summary for today -- falls back to the most recent one that
        # exists (yesterday), not the oldest or an arbitrary one.
        assert latest.summary_text == "yesterday"

    def test_get_latest_summary_none_when_empty(self, db_session):
        service = SummaryService(db_session)
        assert service.get_latest_summary() is None

    def test_get_symbol_summaries_joins_ticker_and_orders_alphabetically(
        self, db_session, symbol_ids
    ):
        db_session.add(
            SymbolSummary(symbol_id=symbol_ids["TSLA"], summary_text="tsla summary")
        )
        db_session.add(
            SymbolSummary(symbol_id=symbol_ids["AAPL"], summary_text="aapl summary")
        )
        db_session.commit()

        service = SummaryService(db_session)
        rows = service.get_symbol_summaries()

        # AAPL < TSLA alphabetically -- and MSFT (no summary row) must
        # not appear at all.
        assert [r.ticker for r in rows] == ["AAPL", "TSLA"]
        assert rows[0].summary_text == "aapl summary"
