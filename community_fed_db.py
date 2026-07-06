# community_fed_db.py
from __future__ import annotations

import os
import re
import hmac
import sqlite3
import hashlib
import secrets
from typing import Optional, List

DB_PATH = os.getenv("COMMUNITY_FED_DB_PATH", "community_fed.db")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PBKDF2_ITERATIONS = 200_000


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        # Users (auth)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT NOT NULL UNIQUE,
                first_name    TEXT NOT NULL,
                last_name     TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # Events (food bank / free grocery events)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                title              TEXT NOT NULL,
                organizer          TEXT,
                start_at           TEXT NOT NULL,              -- 'YYYY-MM-DD HH:MM'
                end_at             TEXT,
                address            TEXT,
                city               TEXT,
                state              TEXT,
                zip_code           TEXT,
                what_to_expect     TEXT,
                what_to_bring      TEXT,
                registration_notes TEXT,
                created_at         TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        #Add created_by column to events table
        columns = conn.execute("PRAGMA table_info(events);").fetchall()
        column_names = [col["name"] for col in columns]
        if "created_by" not in column_names:
            conn.execute(
                """
                ALTER TABLE events 
                ADD COLUMN created_by INTEGER REFERENCES users(id);
                """
            )
        conn.commit()
    finally:
        conn.close()

    seed_demo_events_if_empty()


# ---------------------------
# Users / Authentication
# ---------------------------

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def hash_password(password: str, salt_hex: str) -> str:
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return dk.hex()


def create_user(email: str, first_name: str, last_name: str, password: str) -> None:
    email = email.strip().lower()
    first_name = first_name.strip()
    last_name = last_name.strip()

    if not is_valid_email(email):
        raise ValueError("Please enter a valid email address.")
    if not first_name or not last_name:
        raise ValueError("First and last name are required.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    salt_hex = secrets.token_hex(16)  # 128-bit salt
    pw_hash = hash_password(password, salt_hex)

    conn = get_conn()
    try:
        conn.execute(
            """
            INSERT INTO users (email, first_name, last_name, password_hash, password_salt)
            VALUES (?, ?, ?, ?, ?);
            """,
            (email, first_name, last_name, pw_hash, salt_hex),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise ValueError("An account with that email already exists.")
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ? LIMIT 1;",
            (email.strip().lower(),),
        ).fetchone()
    finally:
        conn.close()


def verify_login(email: str, password: str) -> Optional[dict]:
    user = get_user_by_email(email)
    if not user:
        return None

    candidate_hash = hash_password(password, user["password_salt"])
    if not hmac.compare_digest(candidate_hash, user["password_hash"]):
        return None

    return {
        "id": user["id"],
        "email": user["email"],
        "first_name": user["first_name"],
        "last_name": user["last_name"],
    }


# ---------------------------
# Events
# ---------------------------

def seed_demo_events_if_empty() -> None:
    conn = get_conn()
    try:
        row = conn.execute("SELECT COUNT(1) AS c FROM events;").fetchone()
        if row["c"] and int(row["c"]) > 0:
            return

        demo = [
            (
                "Community Pantry Pop-Up",
                "Downtown Food Bank",
                "2026-07-05 10:00",
                "2026-07-05 12:00",
                "123 Main St",
                "Gainesville",
                "FL",
                "32601",
                "Fresh produce and pantry staples while supplies last.",
                "Reusable bags if you have them.",
                "No appointment. First come, first served.",
            ),
            (
                "Mobile Grocery Distribution",
                "Neighborhood Partners",
                "2026-07-08 15:00",
                "2026-07-08 17:00",
                "456 Oak Ave",
                "Gainesville",
                "FL",
                "32608",
                "Drive-thru style pickup.",
                "Trunk space recommended.",
                "Registration not required.",
            ),
            (
                "Senior Food Box Pickup",
                "Community Center",
                "2026-07-10 09:00",
                "2026-07-10 11:00",
                "789 Pine Rd",
                "Gainesville",
                "FL",
                "32607",
                "Pre-packed boxes; limited quantities.",
                "ID may be requested (varies by site).",
                "Arrive early.",
            ),
        ]

        conn.executemany(
            """
            INSERT INTO events
            (title, organizer, start_at, end_at, address, city, state, zip_code,
             what_to_expect, what_to_bring, registration_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            demo,
        )
        conn.commit()
    finally:
        conn.close()


def get_upcoming_events(
    *,
    limit: int = 6,
    zip_code: Optional[str] = None,
    city: Optional[str] = None,
) -> List[sqlite3.Row]:
    conn = get_conn()
    try:
        sql = """
            SELECT *
            FROM events
            WHERE datetime(start_at) >= datetime('now')
        """
        params: list = []

        if zip_code:
            sql += " AND zip_code = ?"
            params.append(zip_code.strip())

        if city:
            sql += " AND lower(city) LIKE lower(?)"
            params.append(f"%{city.strip()}%")

        sql += " ORDER BY datetime(start_at) ASC LIMIT ?"
        params.append(int(limit))

        return conn.execute(sql, tuple(params)).fetchall()
    finally:
        conn.close()


def get_event_by_id(event_id: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    try:
        return conn.execute(
            """
            SELECT *
            FROM events
            WHERE id = ?
            """,
            (event_id,),
        ).fetchone()
    finally:
        conn.close()


def update_event(
    event_id: int,
    title: str,
    organizer: str,
    start_at: str,
    end_at: str,
    address: str,
    city: str,
    state: str,
    zip_code: str,
    what_to_expect: str,
    what_to_bring: str,
    registration_notes: str,
) -> None:

    conn = get_conn()

    try:
        conn.execute(
            """
            UPDATE events
            SET
                title=?,
                organizer=?,
                start_at=?,
                end_at=?,
                address=?,
                city=?,
                state=?,
                zip_code=?,
                what_to_expect=?,
                what_to_bring=?,
                registration_notes=?
            WHERE id=?;
            """,
            (
                title,
                organizer,
                start_at,
                end_at,
                address,
                city,
                state,
                zip_code,
                what_to_expect,
                what_to_bring,
                registration_notes,
                event_id,
            ),
        )

        conn.commit()

    finally:
        conn.close()