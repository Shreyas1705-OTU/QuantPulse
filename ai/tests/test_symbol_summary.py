"""
symbol_summary.py against a real Postgres -- LLM calls always
monkeypatched, every DB read/write real.
"""

from datetime import datetime, timezone

from sqlalchemy import select

import symbol_summary


def _insert_tick(symbol_id, price=100.0, volume=10, traded_at=None):
    tables = symbol_summary.reflect_tables(["ticks"])
    ticks_table = tables["ticks"]
    with symbol_summary.engine.begin() as conn:
        result = conn.execute(
            ticks_table.insert()
            .values(
                symbol_id=symbol_id,
                price=price,
                volume=volume,
                traded_at=traded_at or datetime.now(timezone.utc),
            )
            .returning(ticks_table.c.id)
        )
        return result.scalar()


def _summary_row(symbol_id):
    tables = symbol_summary.reflect_tables(["symbol_summaries"])
    summaries_table = tables["symbol_summaries"]
    with symbol_summary.engine.connect() as conn:
        return conn.execute(
            select(summaries_table).where(summaries_table.c.symbol_id == symbol_id)
        ).first()


class TestHappyPath:
    def test_symbol_with_no_ticks_is_skipped(self, monkeypatch, symbol_ids):
        calls = []
        monkeypatch.setattr(symbol_summary, "build_client", lambda: calls.append(1))
        symbol_summary.run()
        assert calls == []
        assert _summary_row(symbol_ids["AAPL"]) is None

    def test_symbol_with_ticks_gets_summarized(self, monkeypatch, symbol_ids):
        for _ in range(5):
            _insert_tick(symbol_ids["AAPL"])

        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary, "summarize_symbol_day", lambda client, **kw: "a real summary"
        )

        symbol_summary.run()

        row = _summary_row(symbol_ids["AAPL"])
        assert row is not None
        assert row.summary_text == "a real summary"
        assert row.through_tick_id is not None

    def test_only_symbols_with_ticks_get_an_llm_call(self, monkeypatch, symbol_ids):
        _insert_tick(symbol_ids["AAPL"])
        # TSLA and MSFT get nothing.

        calls = []
        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary,
            "summarize_symbol_day",
            lambda client, **kw: calls.append(kw["ticker"]) or "summarized",
        )

        symbol_summary.run()

        assert calls == ["AAPL"]


class TestSkipLogic:
    def test_no_new_ticks_since_last_summary_skips_the_llm_call(
        self, monkeypatch, symbol_ids
    ):
        _insert_tick(symbol_ids["AAPL"])

        calls = []
        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary,
            "summarize_symbol_day",
            lambda client, **kw: calls.append(1) or "summarized",
        )

        symbol_summary.run()
        assert len(calls) == 1

        # Nothing changed -- a second run must not call the LLM again.
        symbol_summary.run()
        assert len(calls) == 1

    def test_a_new_tick_triggers_regeneration_and_advances_through_tick_id(
        self, monkeypatch, symbol_ids
    ):
        _insert_tick(symbol_ids["AAPL"])

        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary, "summarize_symbol_day", lambda client, **kw: "v1"
        )
        symbol_summary.run()
        first = _summary_row(symbol_ids["AAPL"])
        assert first.summary_text == "v1"

        _insert_tick(symbol_ids["AAPL"])
        monkeypatch.setattr(
            symbol_summary, "summarize_symbol_day", lambda client, **kw: "v2"
        )
        symbol_summary.run()

        second = _summary_row(symbol_ids["AAPL"])
        assert second.summary_text == "v2"
        assert second.through_tick_id > first.through_tick_id

    def test_skip_and_regenerate_are_independent_per_symbol(
        self, monkeypatch, symbol_ids
    ):
        _insert_tick(symbol_ids["AAPL"])
        _insert_tick(symbol_ids["TSLA"])

        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary, "summarize_symbol_day", lambda client, **kw: "v1"
        )
        symbol_summary.run()

        # Only TSLA gets a new tick.
        _insert_tick(symbol_ids["TSLA"])

        calls = []
        monkeypatch.setattr(
            symbol_summary,
            "summarize_symbol_day",
            lambda client, **kw: calls.append(kw["ticker"]) or "v2",
        )
        symbol_summary.run()

        assert calls == ["TSLA"]


class TestResilience:
    def test_a_write_failure_for_one_symbol_does_not_sink_the_run(
        self, monkeypatch, symbol_ids
    ):
        _insert_tick(symbol_ids["AAPL"])
        _insert_tick(symbol_ids["TSLA"])

        monkeypatch.setattr(symbol_summary, "build_client", lambda: object())
        monkeypatch.setattr(
            symbol_summary, "summarize_symbol_day", lambda client, **kw: "summarized"
        )

        real_begin = symbol_summary.engine.begin

        class FakeConn:
            def __init__(self, real_conn):
                self._real = real_conn

            def execute(self, stmt):
                # Inspect the actual bound parameter, not the literal-bound
                # SQL text -- a substring check on compiled SQL is fragile
                # here (both symbol_ids' inserts contain small integers
                # like "1" all over the compiled statement -- timestamps,
                # other column values -- so "is fail_symbol_id's digit a
                # substring of this SQL" false-positives on unrelated rows).
                params = stmt.compile().params
                if params.get("symbol_id") == symbol_ids["AAPL"]:
                    raise RuntimeError("simulated transient DB write failure")
                return self._real.execute(stmt)

            def __enter__(self):
                return self

            def __exit__(self, *a):
                self._real.__exit__(*a)

        class FakeBeginCtx:
            def __enter__(self):
                self._real_ctx = real_begin()
                real_conn = self._real_ctx.__enter__()
                self._fake = FakeConn(real_conn)
                return self._fake

            def __exit__(self, *a):
                return self._real_ctx.__exit__(*a)

        monkeypatch.setattr(symbol_summary.engine, "begin", lambda: FakeBeginCtx())

        symbol_summary.run()  # must not raise

        assert _summary_row(symbol_ids["AAPL"]) is None
        assert _summary_row(symbol_ids["TSLA"]) is not None

        monkeypatch.setattr(symbol_summary.engine, "begin", real_begin)
        symbol_summary.run()
        assert _summary_row(symbol_ids["AAPL"]) is not None
