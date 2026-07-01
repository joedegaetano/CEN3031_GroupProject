# app.py
from __future__ import annotations

import streamlit as st
from community_fed_db import init_db, create_user, verify_login, get_upcoming_events

APP_NAME = "Community Fed"


def set_page(page: str) -> None:
    st.session_state.page = page


def do_logout() -> None:
    st.session_state.user = None
    set_page("Home")
    st.rerun()


def render_top_bar() -> None:
    left, _, right = st.columns([6, 3, 2], vertical_alignment="center")

    with left:
        st.markdown(f"## {APP_NAME}")

    with right:
        if st.session_state.user:
            if st.button("Logout", use_container_width=True):
                do_logout()
        else:
            if st.button("Login", use_container_width=True):
                set_page("Login")
                st.rerun()


def render_event_card(e) -> None:
    with st.container(border=True):
        st.subheader(e["title"])

        meta = []
        if e["organizer"]:
            meta.append(f"Organizer: {e['organizer']}")
        meta.append(f"When: {e['start_at']}" + (f" – {e['end_at']}" if e["end_at"] else ""))

        where_parts = [p for p in [e["address"], e["city"], e["state"], e["zip_code"]] if p]
        if where_parts:
            meta.append("Where: " + ", ".join(where_parts))

        if meta:
            st.caption(" • ".join(meta))

        if e["what_to_expect"]:
            st.write(f"**What to expect:** {e['what_to_expect']}")
        if e["what_to_bring"]:
            st.write(f"**What to bring:** {e['what_to_bring']}")
        if e["registration_notes"]:
            st.info(e["registration_notes"])


def page_home() -> None:
    # Hero
    st.markdown("## Find free grocery & food pantry events near you")
    st.write("Browse upcoming food bank and free grocery events in your town — no account needed.")

    # Search state
    st.session_state.setdefault("search_zip", "")
    st.session_state.setdefault("search_city", "")
    st.session_state.setdefault("did_search", False)

    # Location search box
    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1], vertical_alignment="bottom")
        with c1:
            zip_code = st.text_input("ZIP code", value=st.session_state.search_zip, placeholder="e.g., 32601")
        with c2:
            city = st.text_input("City (optional)", value=st.session_state.search_city, placeholder="e.g., Gainesville")
        with c3:
            if st.button("Find events", use_container_width=True):
                st.session_state.search_zip = zip_code.strip()
                st.session_state.search_city = city.strip()
                st.session_state.did_search = True
                st.rerun()

        st.caption("Tip: Enter a ZIP for the most accurate results. You can browse without logging in.")

    # Auth CTA area
    if st.session_state.user:
        u = st.session_state.user
        st.success(f"Logged in as {u['first_name']} {u['last_name']} ({u['email']})")
    else:
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Create an account", use_container_width=True):
                set_page("Create Account")
                st.rerun()
        st.caption("Create an account to save events and get reminders (optional).")

    # Events list
    st.markdown("### Upcoming events")

    zip_filter = st.session_state.search_zip if st.session_state.did_search and st.session_state.search_zip else None
    city_filter = st.session_state.search_city if st.session_state.did_search and st.session_state.search_city else None

    events = get_upcoming_events(limit=6, zip_code=zip_filter, city=city_filter)

    if not events:
        st.warning("No upcoming events found for that location yet. Try a nearby ZIP or city.")
    else:
        for e in events:
            render_event_card(e)

    # Trust / clarity
    st.markdown("### What to know")
    st.write(
        "Events differ by organizer. Some are first-come-first-served; others recommend registration. "
        "If requirements are listed, you’ll see them on the event card."
    )
    st.caption("We only use your location to show nearby events. We don’t require an account to browse.")


def page_create_account() -> None:
    st.header("Create your Community Fed account")

    st.session_state.setdefault("creating_account", False)

    def lock_submit():
        st.session_state.creating_account = True

    with st.form("create_account_form", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            first_name = st.text_input("First name")
        with c2:
            last_name = st.text_input("Last name")

        email = st.text_input("Email")
        pw1 = st.text_input("Password", type="password")
        pw2 = st.text_input("Confirm password", type="password")

        submitted = st.form_submit_button(
            "Create account",
            on_click=lock_submit,
            disabled=st.session_state.creating_account,
        )

    if submitted:
        try:
            if pw1 != pw2:
                st.error("Passwords do not match.")
                return

            with st.spinner("Creating account..."):
                create_user(email=email, first_name=first_name, last_name=last_name, password=pw1)

            st.success("Account created. Please log in.")

            c1, c2, c3 = st.columns([2, 1, 2])
            with c2:
                if st.button("Go to Login", use_container_width=True):
                    set_page("Login")
                    st.rerun()

        except ValueError as e:
            st.error(str(e))
        except Exception:
            st.error("Something went wrong while creating your account.")
        finally:
            st.session_state.creating_account = False


def page_login() -> None:
    st.header("Login")

    if st.session_state.user:
        st.info("You are already logged in.")
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Go to Home", use_container_width=True):
                set_page("Home")
                st.rerun()
        return

    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        user = verify_login(email=email, password=password)
        if not user:
            st.error("Invalid email or password.")
            return

        st.session_state.user = user
        st.success("Login successful.")
        set_page("Home")
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="centered")
    init_db()

    st.session_state.setdefault("page", "Home")
    st.session_state.setdefault("user", None)

    render_top_bar()
    st.divider()

    if st.session_state.page == "Home":
        page_home()
    elif st.session_state.page == "Create Account":
        # If already logged in, creation shouldn't be accessible
        if st.session_state.user:
            set_page("Home")
            st.rerun()
        page_create_account()
    elif st.session_state.page == "Login":
        page_login()
    else:
        set_page("Home")
        st.rerun()


if __name__ == "__main__":
    main()