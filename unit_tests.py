# test_community_fed_db.py
from __future__ import annotations

import importlib
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest


def utc_fmt(dt: datetime) -> str:
    """SQLite datetime('now') is effectively UTC; use UTC to avoid timezone mismatch."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")


def truncate_tables(dbmod) -> None:
    conn = dbmod.get_conn()
    try:
        conn.execute("DELETE FROM events;")
        conn.execute("DELETE FROM users;")
        conn.commit()
    finally:
        conn.close()


def insert_event(dbmod, **overrides: Any) -> int:
    """
    Insert an event row and return its id.

    The schema includes:
      title (required), organizer, start_at (required), end_at, address, city, state, zip_code,
      what_to_expect, what_to_bring, registration_notes, created_by
    """
    defaults = dict(
        title="Test Event",
        organizer=None,
        start_at=utc_fmt(datetime.now(timezone.utc) + timedelta(days=1)),
        end_at=None,
        address=None,
        city=None,
        state=None,
        zip_code=None,
        what_to_expect=None,
        what_to_bring=None,
        registration_notes=None,
        created_by=None,
    )
    defaults.update(overrides)

    conn = dbmod.get_conn()
    try:
        cur = conn.execute(
            """
            INSERT INTO events
            (title, organizer, start_at, end_at, address, city, state, zip_code,
             what_to_expect, what_to_bring, registration_notes, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                defaults["title"],
                defaults["organizer"],
                defaults["start_at"],
                defaults["end_at"],
                defaults["address"],
                defaults["city"],
                defaults["state"],
                defaults["zip_code"],
                defaults["what_to_expect"],
                defaults["what_to_bring"],
                defaults["registration_notes"],
                defaults["created_by"],
            ),
        )
        conn.commit()
        return int(cur.lastrowid)
    finally:
        conn.close()


@pytest.fixture
def dbmod(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """
    Load community_fed_db with COMMUNITY_FED_DB_PATH pointing at a temp db file.
    Reload the module so DB_PATH is picked up from the env var at import time.
    """
    db_file = tmp_path / "test_community_fed.db"
    monkeypatch.setenv("COMMUNITY_FED_DB_PATH", str(db_file))

    import community_fed_db  # import after env set
    importlib.reload(community_fed_db)

    # Speed up tests: pbkdf2 at 200k iterations can be slow for unit tests.
    # This keeps behavior consistent inside tests while making them faster.
    community_fed_db.PBKDF2_ITERATIONS = 1_000

    # Ensure schema exists
    community_fed_db.init_db()

    return community_fed_db


@pytest.fixture
def dbmod_clean(dbmod):
    """Same as dbmod but with tables cleared after init_db seeding."""
    truncate_tables(dbmod)
    return dbmod


# ---------------------------
# Schema / init_db
# ---------------------------

def test_init_db_creates_tables_and_created_by_column(dbmod) -> None:
    conn = dbmod.get_conn()
    try:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table';"
            ).fetchall()
        }
        assert "users" in tables
        assert "events" in tables

        event_cols = conn.execute("PRAGMA table_info(events);").fetchall()
        col_names = [c["name"] for c in event_cols]
        assert "created_by" in col_names
    finally:
        conn.close()


def test_init_db_is_idempotent(dbmod) -> None:
    # Should not raise if called multiple times.
    dbmod.init_db()
    dbmod.init_db()


# ---------------------------
# Email validation / hashing
# ---------------------------

@pytest.mark.parametrize(
    "email, expected",
    [
        ("person@example.com", True),
        (" person@example.com ", True),
        ("person+tag@example.com", True),
        ("person@mail.example.co.uk", True),
        ("not-an-email", False),
        ("person@", False),
        ("@example.com", False),
        ("person@example", False),
        ("person @example.com", False),
    ],
)
def test_is_valid_email(dbmod, email: str, expected: bool) -> None:
    assert dbmod.is_valid_email(email) is expected


def test_hash_password_is_deterministic_for_same_salt(dbmod) -> None:
    salt_hex = "00" * 16  # 128-bit salt
    h1 = dbmod.hash_password("password123", salt_hex)
    h2 = dbmod.hash_password("password123", salt_hex)
    assert h1 == h2
    assert isinstance(h1, str)
    assert len(h1) > 0


def test_hash_password_changes_with_salt(dbmod) -> None:
    h1 = dbmod.hash_password("password123", "11" * 16)
    h2 = dbmod.hash_password("password123", "22" * 16)
    assert h1 != h2


# ---------------------------
# Users / Authentication
# ---------------------------

def test_create_user_inserts_and_normalizes_email(dbmod_clean) -> None:
    dbmod_clean.create_user(
        email="  PERSON@Example.com ",
        first_name="Pat",
        last_name="Lee",
        password="strong-pass",
    )

    row = dbmod_clean.get_user_by_email("person@example.com")
    assert row is not None
    assert row["email"] == "person@example.com"
    assert row["first_name"] == "Pat"
    assert row["last_name"] == "Lee"
    assert row["password_hash"]
    assert row["password_salt"]


def test_create_user_rejects_invalid_email(dbmod_clean) -> None:
    with pytest.raises(ValueError, match="valid email"):
        dbmod_clean.create_user(
            email="not-an-email",
            first_name="Pat",
            last_name="Lee",
            password="strong-pass",
        )


def test_create_user_requires_first_and_last_name(dbmod_clean) -> None:
    with pytest.raises(ValueError, match="First and last name are required"):
        dbmod_clean.create_user(
            email="person@example.com",
            first_name="",
            last_name="Lee",
            password="strong-pass",
        )


def test_create_user_rejects_short_password(dbmod_clean) -> None:
    with pytest.raises(ValueError, match="at least 8"):
        dbmod_clean.create_user(
            email="person@example.com",
            first_name="Pat",
            last_name="Lee",
            password="short",
        )


def test_create_user_duplicate_email_raises(dbmod_clean) -> None:
    dbmod_clean.create_user(
        email="person@example.com",
        first_name="Pat",
        last_name="Lee",
        password="strong-pass",
    )
    with pytest.raises(ValueError, match="already exists"):
        dbmod_clean.create_user(
            email="PERSON@example.com",  # should normalize to same
            first_name="Pat",
            last_name="Lee",
            password="strong-pass",
        )


def test_verify_login_success_and_failure(dbmod_clean) -> None:
    dbmod_clean.create_user(
        email="jamie@example.com",
        first_name="Jamie",
        last_name="Rivera",
        password="correct-password",
    )

    ok = dbmod_clean.verify_login("jamie@example.com", "correct-password")
    assert ok is not None
    assert ok["email"] == "jamie@example.com"
    assert ok["first_name"] == "Jamie"
    assert ok["last_name"] == "Rivera"
    assert isinstance(ok["id"], int)

    bad_pw = dbmod_clean.verify_login("jamie@example.com", "wrong-password")
    assert bad_pw is None

    missing = dbmod_clean.verify_login("missing@example.com", "whatever")
    assert missing is None


# ---------------------------
# Events queries
# ---------------------------

def test_get_upcoming_events_filters_past_and_orders_future(dbmod_clean) -> None:
    now = datetime.now(timezone.utc)
    past = utc_fmt(now - timedelta(days=1))
    future1 = utc_fmt(now + timedelta(hours=2))
    future2 = utc_fmt(now + timedelta(days=2))

    insert_event(dbmod_clean, title="Past Event", start_at=past, city="Gainesville")
    id1 = insert_event(dbmod_clean, title="Soon Event", start_at=future1, city="Gainesville")
    id2 = insert_event(dbmod_clean, title="Later Event", start_at=future2, city="Gainesville")

    rows = dbmod_clean.get_upcoming_events(limit=10)
    titles = [r["title"] for r in rows]

    assert "Past Event" not in titles
    assert titles == ["Soon Event", "Later Event"]
    assert [r["id"] for r in rows] == [id1, id2]


def test_get_upcoming_events_respects_limit(dbmod_clean) -> None:
    now = datetime.now(timezone.utc)
    for i in range(5):
        insert_event(
            dbmod_clean,
            title=f"Event {i}",
            start_at=utc_fmt(now + timedelta(hours=i + 1)),
        )

    rows = dbmod_clean.get_upcoming_events(limit=2)
    assert len(rows) == 2


def test_get_upcoming_events_filters_zip_and_city_case_insensitive(dbmod_clean) -> None:
    now = datetime.now(timezone.utc)
    start = utc_fmt(now + timedelta(days=1))

    insert_event(dbmod_clean, title="A", start_at=start, zip_code="32601", city="Gainesville")
    insert_event(dbmod_clean, title="B", start_at=start, zip_code="32601", city="GAINESVILLE WEST")
    insert_event(dbmod_clean, title="C", start_at=start, zip_code="99999", city="Gainesville")

    rows = dbmod_clean.get_upcoming_events(limit=10, zip_code="32601", city="gaines")
    assert [r["title"] for r in rows] == ["A", "B"]


def test_get_event_by_id_returns_row_or_none(dbmod_clean) -> None:
    event_id = insert_event(dbmod_clean, title="Lookup Event")
    row = dbmod_clean.get_event_by_id(event_id)
    assert row is not None
    assert row["id"] == event_id
    assert row["title"] == "Lookup Event"

    missing = dbmod_clean.get_event_by_id(999999)
    assert missing is None


def test_update_event_updates_all_fields(dbmod_clean) -> None:
    event_id = insert_event(
        dbmod_clean,
        title="Old Title",
        organizer="Old Org",
        start_at=utc_fmt(datetime.now(timezone.utc) + timedelta(days=1)),
        end_at=None,
        address="Old Address",
        city="Old City",
        state="FL",
        zip_code="32601",
        what_to_expect="Old expect",
        what_to_bring="Old bring",
        registration_notes="Old notes",
    )

    dbmod_clean.update_event(
        event_id=event_id,
        title="New Title",
        organizer="New Org",
        start_at=utc_fmt(datetime.now(timezone.utc) + timedelta(days=2)),
        end_at=utc_fmt(datetime.now(timezone.utc) + timedelta(days=2, hours=2)),
        address="123 Main St",
        city="Gainesville",
        state="FL",
        zip_code="32608",
        what_to_expect="New expect",
        what_to_bring="New bring",
        registration_notes="New notes",
    )

    updated = dbmod_clean.get_event_by_id(event_id)
    assert updated is not None
    assert updated["title"] == "New Title"
    assert updated["organizer"] == "New Org"
    assert updated["address"] == "123 Main St"
    assert updated["city"] == "Gainesville"
    assert updated["zip_code"] == "32608"
    assert updated["what_to_expect"] == "New expect"
    assert updated["registration_notes"] == "New notes"