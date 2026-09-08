"""
explainer.py against a real Postgres -- the LLM client is always
monkeypatched (no real Azure OpenAI calls in tests), but every DB read
and write is real.
"""

from sqlalchemy import select

import explainer


def _insert_alert(symbol_id, message="Test alert", severity="HIGH"):
    tables = explainer.reflect_tables(["alerts"])
    alerts_table = tables["alerts"]
    with explainer.engine.begin() as conn:
        result = conn.execute(
            alerts_table.insert()
            .values(symbol_id=symbol_id, message=message, severity=severity)
            .returning(alerts_table.c.id)
        )
        return result.scalar()


def _explanation_for(alert_id):
    tables = explainer.reflect_tables(["alerts"])
    alerts_table = tables["alerts"]
    with explainer.engine.connect() as conn:
        return conn.execute(
            select(alerts_table.c.explanation).where(alerts_table.c.id == alert_id)
        ).scalar()


class TestHappyPath:
    def test_no_unexplained_alerts_is_a_noop(self, monkeypatch, symbol_ids):
        # No alerts at all -- must not even try to build an LLM client.
        called = []
        monkeypatch.setattr(explainer, "build_client", lambda: called.append(1))
        explainer.run()
        assert called == []

    def test_unexplained_alert_gets_explained_and_written(self, monkeypatch, symbol_ids):
        alert_id = _insert_alert(symbol_ids["AAPL"], message="Volume spike")
        monkeypatch.setattr(explainer, "build_client", lambda: object())
        monkeypatch.setattr(
            explainer, "explain_alert", lambda client, **kw: "a real explanation"
        )

        explainer.run()

        assert _explanation_for(alert_id) == "a real explanation"

    def test_already_explained_alerts_are_left_alone(self, monkeypatch, symbol_ids):
        alert_id = _insert_alert(symbol_ids["AAPL"])
        tables = explainer.reflect_tables(["alerts"])
        alerts_table = tables["alerts"]
        with explainer.engine.begin() as conn:
            conn.execute(
                alerts_table.update()
                .where(alerts_table.c.id == alert_id)
                .values(explanation="already done")
            )

        calls = []
        monkeypatch.setattr(explainer, "build_client", lambda: object())
        monkeypatch.setattr(
            explainer,
            "explain_alert",
            lambda client, **kw: calls.append(1) or "should not be used",
        )

        explainer.run()

        assert calls == []
        assert _explanation_for(alert_id) == "already done"

    def test_batch_limit_caps_a_single_run(self, monkeypatch, symbol_ids):
        ids = [_insert_alert(symbol_ids["AAPL"], message=f"alert {i}") for i in range(explainer.BATCH_LIMIT + 5)]

        monkeypatch.setattr(explainer, "build_client", lambda: object())
        monkeypatch.setattr(explainer, "explain_alert", lambda client, **kw: "explained")

        explainer.run()

        explained = sum(1 for i in ids if _explanation_for(i) is not None)
        assert explained == explainer.BATCH_LIMIT

        # The leftover ones are exactly what a second run should pick up.
        explainer.run()
        explained_after_second_run = sum(1 for i in ids if _explanation_for(i) is not None)
        assert explained_after_second_run == len(ids)


class TestResilience:
    def test_a_write_failure_for_one_alert_does_not_sink_the_batch(
        self, monkeypatch, symbol_ids
    ):
        ids = [_insert_alert(symbol_ids["AAPL"], message=f"alert {i}") for i in range(3)]
        fail_id = ids[1]  # the middle one fails its write

        monkeypatch.setattr(explainer, "build_client", lambda: object())
        monkeypatch.setattr(explainer, "explain_alert", lambda client, **kw: "explained")

        real_begin = explainer.engine.begin

        class FakeConn:
            def __init__(self, real_conn):
                self._real = real_conn

            def execute(self, stmt):
                # Inspect the actual bound parameter, not a substring
                # check on compiled SQL text -- a literal-bound SQL
                # string can coincidentally contain another row's id as
                # a substring of some unrelated value (a timestamp, a
                # different column), so this checks the real WHERE-clause
                # parameter SQLAlchemy binds for an UPDATE ... WHERE
                # id == :id_1 (confirmed empirically, not guessed).
                params = stmt.compile().params
                if params.get("id_1") == fail_id:
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

        monkeypatch.setattr(explainer.engine, "begin", lambda: FakeBeginCtx())

        explainer.run()  # must not raise

        assert _explanation_for(fail_id) is None
        others = [i for i in ids if i != fail_id]
        assert all(_explanation_for(i) == "explained" for i in others)

        # Restore the real engine.begin and confirm a second run retries
        # exactly the one that failed.
        monkeypatch.setattr(explainer.engine, "begin", real_begin)
        explainer.run()
        assert _explanation_for(fail_id) == "explained"

    def test_a_failed_llm_call_for_one_alert_does_not_sink_the_batch(
        self, monkeypatch, symbol_ids
    ):
        ids = [_insert_alert(symbol_ids["AAPL"], message=f"alert {i}") for i in range(3)]
        fail_id = ids[0]

        monkeypatch.setattr(explainer, "build_client", lambda: object())

        def flaky_explain(client, **kw):
            # explainer.py's own SQL identifies rows by id, not by
            # message -- match on the message text this test controls
            # instead, since explain_alert only sees the alert's fields.
            if kw["message"] == "alert 0":
                raise RuntimeError("simulated LLM failure")
            return "explained"

        monkeypatch.setattr(explainer, "explain_alert", flaky_explain)

        explainer.run()

        assert _explanation_for(fail_id) is None
        others = [i for i in ids if i != fail_id]
        assert all(_explanation_for(i) == "explained" for i in others)
