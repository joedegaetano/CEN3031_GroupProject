from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call

import pytest
from streamlit.testing.v1 import AppTest


def find_app_file() -> Path:
    """Support placing this file either beside app.py or inside tests/."""
    test_file_directory = Path(__file__).resolve().parent
    candidates = [
        test_file_directory / "app.py",
        test_file_directory.parent / "app.py",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Could not find app.py. Put test_app.py beside app.py or in a tests/ folder."
    )


APP_FILE = find_app_file()


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """
    Replace community_fed_db with an in-memory fake module.

    This prevents the tests from reading or changing the real database.
    Each function is a Mock so tests can control return values and verify calls.
    """
    mocks = SimpleNamespace(
        init_db=Mock(name="init_db"),
        create_user=Mock(name="create_user"),
        verify_login=Mock(name="verify_login", return_value=None),
        get_upcoming_events=Mock(name="get_upcoming_events", return_value=[]),
        get_event_by_id=Mock(name="get_event_by_id", return_value=None),
    )

    fake_database_module = ModuleType("community_fed_db")
    fake_database_module.init_db = mocks.init_db
    fake_database_module.create_user = mocks.create_user
    fake_database_module.verify_login = mocks.verify_login
    fake_database_module.get_upcoming_events = mocks.get_upcoming_events
    fake_database_module.get_event_by_id = mocks.get_event_by_id

    monkeypatch.setitem(sys.modules, "community_fed_db", fake_database_module)
    return mocks


@pytest.fixture
def sample_event() -> dict[str, object]:
    return {
        "id": 7,
        "title": "Community Meal Pickup",
        "organizer": "Community Fed",
        "start_at": "2026-07-10 10:00 AM",
        "end_at": "2026-07-10 12:00 PM",
        "address": "123 Main Street",
        "city": "Gainesville",
        "state": "FL",
        "zip_code": "32601",
        "what_to_expect": "Drive-through grocery pickup.",
        "what_to_bring": "A photo ID.",
        "registration_notes": "Registration is recommended.",
    }


def new_app() -> AppTest:
    return AppTest.from_file(APP_FILE)


def widget_with_label(widgets, label: str, occurrence: int = 0):
    """Return a widget by its visible label."""
    matches = [widget for widget in widgets if widget.label == label]

    if not matches:
        available_labels = [widget.label for widget in widgets]
        raise AssertionError(
            f"Could not find widget labeled {label!r}. "
            f"Available labels: {available_labels}"
        )

    return matches[occurrence]


def set_text(at: AppTest, label: str, value: str) -> None:
    widget_with_label(at.text_input, label).set_value(value)


def assert_no_app_exceptions(at: AppTest) -> None:
    assert len(at.exception) == 0, [
        exception.value for exception in at.exception
    ]


def test_home_page_loads_and_initializes_database(db: SimpleNamespace) -> None:
    at = new_app().run()

    assert_no_app_exceptions(at)
    db.init_db.assert_called_once_with()
    db.get_upcoming_events.assert_called_once_with(
        limit=6,
        zip_code=None,
        city=None,
    )

    assert at.session_state["page"] == "Home"
    assert at.session_state["user"] is None
    assert any(
        "Find free grocery & food pantry events near you" in item.value
        for item in at.markdown
    )
    assert any(
        "No upcoming events found" in item.value
        for item in at.warning
    )


def test_home_search_passes_filters_to_database(db: SimpleNamespace) -> None:
    at = new_app().run()

    set_text(at, "ZIP code", " 32601 ")
    set_text(at, "City (optional)", " Gainesville ")
    widget_with_label(at.button, "Find events").click().run()

    assert_no_app_exceptions(at)
    assert at.session_state["search_zip"] == "32601"
    assert at.session_state["search_city"] == "Gainesville"
    assert at.session_state["did_search"] is True

    assert db.get_upcoming_events.call_args_list[-1] == call(
        limit=6,
        zip_code="32601",
        city="Gainesville",
    )


def test_login_rejects_invalid_credentials(db: SimpleNamespace) -> None:
    db.verify_login.return_value = None

    at = new_app()
    at.session_state["page"] = "Login"
    at.session_state["user"] = None
    at.run()

    set_text(at, "Email", "person@example.com")
    set_text(at, "Password", "wrong-password")

    # The page contains a top-bar Login button and a form Login button.
    widget_with_label(at.button, "Login", occurrence=-1).click().run()

    assert_no_app_exceptions(at)
    db.verify_login.assert_called_once_with(
        email="person@example.com",
        password="wrong-password",
    )
    assert at.session_state["user"] is None
    assert any(
        error.value == "Invalid email or password."
        for error in at.error
    )


def test_login_stores_authenticated_user(db: SimpleNamespace) -> None:
    authenticated_user = {
        "id": 4,
        "first_name": "Jamie",
        "last_name": "Rivera",
        "email": "jamie@example.com",
    }
    db.verify_login.return_value = authenticated_user

    at = new_app()
    at.session_state["page"] = "Login"
    at.session_state["user"] = None
    at.run()

    set_text(at, "Email", "jamie@example.com")
    set_text(at, "Password", "correct-password")
    widget_with_label(at.button, "Login", occurrence=-1).click().run()

    assert_no_app_exceptions(at)
    db.verify_login.assert_called_once_with(
        email="jamie@example.com",
        password="correct-password",
    )
    assert at.session_state["user"] == authenticated_user
    assert at.session_state["page"] == "Home"


def test_logout_clears_the_current_user(db: SimpleNamespace) -> None:
    at = new_app()
    at.session_state["page"] = "Home"
    at.session_state["user"] = {
        "id": 4,
        "first_name": "Jamie",
        "last_name": "Rivera",
        "email": "jamie@example.com",
    }
    at.run()

    widget_with_label(at.button, "Logout").click().run()

    assert_no_app_exceptions(at)
    assert at.session_state["user"] is None
    assert at.session_state["page"] == "Home"
    assert any(button.label == "Login" for button in at.button)


def test_create_account_rejects_mismatched_passwords(
    db: SimpleNamespace,
) -> None:
    at = new_app()
    at.session_state["page"] = "Create Account"
    at.session_state["user"] = None
    at.run()

    set_text(at, "First name", "Taylor")
    set_text(at, "Last name", "Morgan")
    set_text(at, "Email", "taylor@example.com")
    set_text(at, "Password", "password-one")
    set_text(at, "Confirm password", "password-two")
    widget_with_label(at.button, "Create account").click().run()

    assert_no_app_exceptions(at)
    db.create_user.assert_not_called()
    assert any(
        error.value == "Passwords do not match."
        for error in at.error
    )
    assert at.session_state["creating_account"] is False


def test_create_account_calls_database(db: SimpleNamespace) -> None:
    at = new_app()
    at.session_state["page"] = "Create Account"
    at.session_state["user"] = None
    at.run()

    set_text(at, "First name", "Taylor")
    set_text(at, "Last name", "Morgan")
    set_text(at, "Email", "taylor@example.com")
    set_text(at, "Password", "strong-password")
    set_text(at, "Confirm password", "strong-password")
    widget_with_label(at.button, "Create account").click().run()

    assert_no_app_exceptions(at)
    db.create_user.assert_called_once_with(
        email="taylor@example.com",
        first_name="Taylor",
        last_name="Morgan",
        password="strong-password",
    )
    assert any(
        success.value == "Account created. Please log in."
        for success in at.success
    )
    assert at.session_state["creating_account"] is False


def test_create_account_displays_validation_error(
    db: SimpleNamespace,
) -> None:
    db.create_user.side_effect = ValueError("That email is already registered.")

    at = new_app()
    at.session_state["page"] = "Create Account"
    at.session_state["user"] = None
    at.run()

    set_text(at, "First name", "Taylor")
    set_text(at, "Last name", "Morgan")
    set_text(at, "Email", "existing@example.com")
    set_text(at, "Password", "strong-password")
    set_text(at, "Confirm password", "strong-password")
    widget_with_label(at.button, "Create account").click().run()

    assert_no_app_exceptions(at)
    assert any(
        error.value == "That email is already registered."
        for error in at.error
    )


def test_event_card_opens_event_details(
    db: SimpleNamespace,
    sample_event: dict[str, object],
) -> None:
    db.get_upcoming_events.return_value = [sample_event]
    db.get_event_by_id.return_value = sample_event

    at = new_app().run()

    assert any(
        subheader.value == sample_event["title"]
        for subheader in at.subheader
    )

    at.button(key="view_event_7").click().run()

    assert_no_app_exceptions(at)
    db.get_event_by_id.assert_called_with(7)
    assert at.session_state["page"] == "View Event"
    assert at.session_state["selected_event_id"] == 7
    assert at.header[0].value == sample_event["title"]
    assert any(
        "Log in or create an account to register" in warning.value
        for warning in at.warning
    )


def test_view_event_handles_missing_selection(db: SimpleNamespace) -> None:
    at = new_app()
    at.session_state["page"] = "View Event"
    at.session_state["user"] = None
    at.run()

    assert_no_app_exceptions(at)
    db.get_event_by_id.assert_not_called()
    assert any(
        error.value == "No event selected."
        for error in at.error
    )
