from __future__ import annotations

import datetime as _dt

import streamlit as st
from community_fed_db import (
    init_db,
    create_user,
    verify_login,
    get_upcoming_events,
    get_event_by_id,
    get_events_by_organizer,
    get_registered_events,
    register_for_event,
    is_registered,
    cancel_registration,
    delete_event,
    update_event,
    get_user_by_id,
    update_user,
    count_events,
    count_upcoming_registered,
    add_favorite,
    remove_favorite,
    is_favorite,
    get_favorite_events,
    create_event,
    get_pending_events,
    set_event_approval_status,
)

APP_NAME = "Community Fed"
ADMIN_EMAILS = {"admin@communityfed.com"}

def set_page(page: str) -> None:
    st.session_state.page = page


def do_logout() -> None:
    st.session_state.user = None
    set_page("Home")
    st.rerun()

def is_admin() -> bool:
    user = st.session_state.get("user")
    return bool(user and user["email"].lower() in ADMIN_EMAILS)    


def render_top_bar() -> None:
    left, home, dashboard, manage, profile, right = st.columns(
        [4, 2, 2, 2, 2, 2],
        vertical_alignment="center",
    )

    with left:
        st.markdown(f"## {APP_NAME}")

    with home:
        if st.button("Home", use_container_width=True):
            set_page("Home")
            st.rerun()
    with dashboard:
        if st.session_state.user:
            if st.button("Dashboard", use_container_width=True):
                set_page("Dashboard")
                st.rerun()

    with manage:
        if st.session_state.user:
            if st.button("Manage Events", use_container_width=True):
                set_page("Manage Events")
                st.rerun()

    with profile:
        if st.session_state.user:
            if st.button("Profile", use_container_width=True):
                set_page("Profile")
                st.rerun()

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
        # Show edit/favorite button for logged in users
        if st.session_state.user:
            if e["created_by"] == st.session_state.user["id"]:
                if st.button("Edit Event", key=f"edit_{e['id']}"):
                    st.session_state.selected_event = e["id"]
                    set_page("Modify Event")
                    st.rerun()

            if is_favorite(st.session_state.user["id"], e["id"]):
                if st.button("★ Remove Favorite", key=f"unfavorite_{e['id']}"):
                    remove_favorite(st.session_state.user["id"], e["id"])
                    st.rerun()

            else:
                if st.button("☆ Add Favorite", key=f"favorite_{e['id']}"):
                   add_favorite(st.session_state.user["id"], e["id"])
                   st.rerun()

        if st.button("View event details", key=f"view_event_{e['id']}", use_container_width=True):
           st.session_state.selected_event_id = e["id"]
           st.session_state.event_return_page = "Home"
           set_page("View Event")
           st.rerun()


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

        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Create Event", use_container_width=True):
                set_page("Create Event")
                st.rerun()
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

def page_view_event() -> None:
    event_id = st.session_state.get("selected_event_id")
    return_page = st.session_state.get("event_return_page", "Home")

    if not event_id:
        st.error("No event selected.")
        if st.button("Back to events", key="back_no_event_selected"):
            set_page(return_page)
            st.rerun()
        return

    event = get_event_by_id(event_id)

    if not event:
        st.error("This event could not be found.")
        if st.button("Back to events", key="back_from_event_not_found"):
            set_page(return_page)
            st.rerun()
        return

    if st.button("← Back to events", key="back_to_events_from_view"):
        set_page(return_page)
        st.rerun()

    st.header(event["title"])

    if event["organizer"]:
        st.caption(f"Organized by {event['organizer']}")

    st.divider()

    with st.container(border=True):
        st.subheader("Event Details")

        st.write(
            f"**Date and time:** {event['start_at']}"
            + (f" – {event['end_at']}" if event["end_at"] else "")
        )

        where_parts = [p for p in [event["address"], event["city"], event["state"], event["zip_code"]] if p]
        if where_parts:
            st.write(f"**Location:** {', '.join(where_parts)}")

        if event["what_to_expect"]:
            st.write(f"**What to expect:** {event['what_to_expect']}")

        if event["what_to_bring"]:
            st.write(f"**What to bring:** {event['what_to_bring']}")

        if event["registration_notes"]:
            st.info(event["registration_notes"])

    st.divider()

    with st.container(border=True):
        st.subheader("Registration")

        if st.session_state.user:
            user_id = st.session_state.user["id"]
            if is_registered(user_id, event["id"]):
                st.success("You're registered for this event.")
                if st.button("Cancel registration", key="cancel_from_event_view", use_container_width=True):
                    cancel_registration(user_id, event["id"])
                    st.rerun()
            else:
                st.write("You are logged in and can register for this event.")
                if st.button("Register for this event", key="register_from_event_view", use_container_width=True):
                    register_for_event(user_id, event["id"])
                    st.success("You're registered for this event.")
                    st.rerun()
        else:
            st.warning("Log in or create an account to register for this event.")

            c1, c2 = st.columns(2)
            with c1:
                if st.button("Login", key="login_from_event_view", use_container_width=True):
                    set_page("Login")
                    st.rerun()
            with c2:
                if st.button("Create account", key="create_account_from_event_view", use_container_width=True):
                    set_page("Create Account")
                    st.rerun()    


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

def page_create_event() -> None:
    if st.button("← Back to Home"):
        set_page("Home")
        st.rerun()

    st.header("Create event")

    if not st.session_state.user:
        st.warning("Please log in to create an event.")
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Go to Login", use_container_width=True):
                set_page("Login")
                st.rerun()
        return

    with st.form("create_event_form", clear_on_submit=True):
        title = st.text_input("Event title")
        organizer = st.text_input("Organizer")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Start date")
        with c2:
            start_time = st.time_input("Start time")

        c3, c4 = st.columns(2)
        with c3:
            end_date = st.date_input("End date")
        with c4:
            end_time = st.time_input("End time")

        address = st.text_input("Address")
        c5, c6, c7 = st.columns([2, 1, 1])
        with c5:
            city = st.text_input("City")
        with c6:
            state = st.text_input("State")
        with c7:
            zip_code = st.text_input("ZIP code")

        what_to_expect = st.text_area("What to expect")
        what_to_bring = st.text_area("What to bring")
        registration_notes = st.text_area("Registration notes")

        submitted = st.form_submit_button("Create event")

    if submitted:
        try:
            

            start_at = f"{start_date.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')}"
            end_at = f"{end_date.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"

            create_event(
                title=title,
                organizer=organizer,
                start_at=start_at,
                end_at=end_at,
                address=address,
                city=city,
                state=state,
                zip_code=zip_code,
                what_to_expect=what_to_expect,
                what_to_bring=what_to_bring,
                registration_notes=registration_notes,
                created_by=st.session_state.user["id"],
            )

            st.success("Event submitted for approval.")
            if st.button("Return Home", use_container_width=True):
                set_page("Home")
                st.rerun()

        except ValueError as e:
            st.error(str(e))
        except Exception:
            st.error("Something went wrong while creating the event.")


def page_modify_event() -> None:
    if st.button("← Back to Manage Events", key="modify_back"):
        set_page("Manage Events")
        st.rerun()

    if not st.session_state.user:
        st.warning("Please log in to modify events.")
        return

    event_id = st.session_state.get("selected_event")
    if not event_id:
        st.error("No event selected to modify.")
        return

    event = get_event_by_id(event_id)
    if not event:
        st.error("This event could not be found.")
        return

    if event["created_by"] != st.session_state.user["id"]:
        st.error("You can only modify events that you created.")
        return

    st.header("Modify event")

    start_dt = _dt.datetime.strptime(
            event["start_at"],
            "%Y-%m-%d %H:%M",
    )
    end_dt = (
        _dt.datetime.strptime(
            event["end_at"],
            "%Y-%m-%d %H:%M",
        )
        if event["end_at"]
        else start_dt
    )

    with st.form("modify_event_form", clear_on_submit=False):
        title = st.text_input("Event title", value=event["title"])
        organizer = st.text_input("Organizer", value=event["organizer"] or "")

        c1, c2 = st.columns(2)
        with c1:
            start_date = st.date_input("Start date", value=start_dt.date())
        with c2:
            start_time = st.time_input("Start time", value=start_dt.time())

        c3, c4 = st.columns(2)
        with c3:
            end_date = st.date_input("End date", value=end_dt.date())
        with c4:
            end_time = st.time_input("End time", value=end_dt.time())

        address = st.text_input("Address", value=event["address"] or "")
        c5, c6, c7 = st.columns([2, 1, 1])
        with c5:
            city = st.text_input("City", value=event["city"] or "")
        with c6:
            state = st.text_input("State", value=event["state"] or "")
        with c7:
            zip_code = st.text_input("ZIP code", value=event["zip_code"] or "")

        what_to_expect = st.text_area("What to expect", value=event["what_to_expect"] or "")
        what_to_bring = st.text_area("What to bring", value=event["what_to_bring"] or "")
        registration_notes = st.text_area("Registration notes", value=event["registration_notes"] or "")

        submitted = st.form_submit_button("Save changes")

    if submitted:
        try:
            start_at = f"{start_date.strftime('%Y-%m-%d')} {start_time.strftime('%H:%M')}"
            end_at = f"{end_date.strftime('%Y-%m-%d')} {end_time.strftime('%H:%M')}"

            update_event(
                event_id,
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
            )
            st.success("Event updated and sent for approval.")

            if st.button(
                "Back to Manage Events",
                 key="modify_done_back",
                 use_container_width=True
            ):
                set_page("Manage Events")
                st.rerun()

        except ValueError as e:
            st.error(str(e))
        except Exception:
            st.error("Something went wrong while updating the event.")


def page_dashboard() -> None:
    if not st.session_state.user:
        st.warning("Please log in to view your dashboard.")
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Go to Login", use_container_width=True, key="dash_login"):
                set_page("Login")
                st.rerun()
        return

    user = st.session_state.user

    st.header("My Dashboard")
    st.caption(f"Welcome back, {user['first_name']}.")

    my_events = get_events_by_organizer(user["id"])
    my_registrations = get_registered_events(user["id"])

    # Quick stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Events you've created", len(my_events))
    with c2:
        st.metric("Upcoming registrations", count_upcoming_registered(user["id"]))
    with c3:
        st.metric("Total events on Community Fed", count_events())

    st.divider()

    # My Events
    st.subheader("My Events")
    if not my_events:
        st.info("You haven't created any events yet.")
        if st.button("Create an event", use_container_width=True, key="dash_create_event"):
            set_page("Create Event")
            st.rerun()
    else:
        for e in my_events:
            with st.container(border=True):
                st.markdown(f"**{e['title']}**")

                meta = [f"When: {e['start_at']}" + (f" – {e['end_at']}" if e["end_at"] else "")]
                where_parts = [p for p in [e["address"], e["city"], e["state"], e["zip_code"]] if p]
                if where_parts:
                    meta.append("Where: " + ", ".join(where_parts))
                st.caption(" • ".join(meta))

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Edit", key=f"dash_edit_{e['id']}", use_container_width=True):
                        st.session_state.selected_event = e["id"]
                        set_page("Modify Event")
                        st.rerun()
                with c2:
                    confirm_key = f"confirm_delete_{e['id']}"
                    if st.session_state.get(confirm_key):
                        cc1, cc2 = st.columns(2)
                        with cc1:
                            if st.button("Confirm delete", key=f"dash_confirm_delete_{e['id']}", use_container_width=True):
                                delete_event(e["id"])
                                st.session_state[confirm_key] = False
                                st.success("Event deleted.")
                                st.rerun()
                        with cc2:
                            if st.button("Cancel", key=f"dash_cancel_delete_{e['id']}", use_container_width=True):
                                st.session_state[confirm_key] = False
                                st.rerun()
                    else:
                        if st.button("Delete", key=f"dash_delete_{e['id']}", use_container_width=True):
                            st.session_state[confirm_key] = True
                            st.rerun()

    st.divider()

    # My Registrations
    st.subheader("My Registrations")
    if not my_registrations:
        st.info("You haven't registered for any events yet.")
        if st.button("Browse events", use_container_width=True, key="dash_browse_events"):
            set_page("Home")
            st.rerun()
    else:
        for e in my_registrations:
            with st.container(border=True):
                st.markdown(f"**{e['title']}**")
                st.caption(f"When: {e['start_at']}" + (f" – {e['end_at']}" if e["end_at"] else ""))
                if st.button("Cancel registration", key=f"dash_cancel_reg_{e['id']}", use_container_width=True):
                    cancel_registration(user["id"], e["id"])
                    st.success("Registration cancelled.")
                    st.rerun()
    # My Favorites
    st.divider()

    st.subheader("My Favorites")

    favorites = get_favorite_events(st.session_state.user["id"])

    if not favorites:
        st.info("You haven't favorited any events yet.")
    else:
        for e in favorites:
            render_event_card(e)

def page_manage_events() -> None:
    if not st.session_state.user:
        st.warning("Please log in to manage events.")
        return

    user = st.session_state.user
    st.header("Manage Events")

    if st.button("Create new event", use_container_width=True):
        set_page("Create Event")
        st.rerun()

    if is_admin():
        if st.button("Review pending events", use_container_width=True):
            set_page("Admin")
            st.rerun()

    events = get_events_by_organizer(user["id"])

    if not events:
        st.info("You have not created any events yet.")
        return

    for event in events:
        with st.container(border=True):
            st.subheader(event["title"])
            st.write(f"Status: {event['approval_status'].title()}")
            st.caption(
                f"When: {event['start_at']}"
                + (f" – {event['end_at']}" if event["end_at"] else "")
            )

            view_col, edit_col, delete_col = st.columns(3)

            with view_col:
                if st.button(
                    "View",
                    key=f"manage_view_{event['id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_event_id = event["id"]
                    st.session_state.event_return_page = "Manage Events"
                    set_page("View Event")
                    st.rerun()

            with edit_col:
                if st.button(
                    "Edit",
                    key=f"manage_edit_{event['id']}",
                    use_container_width=True,
                ):
                    st.session_state.selected_event = event["id"]
                    set_page("Modify Event")
                    st.rerun()

            with delete_col:
                confirm_key = f"manage_confirm_delete_{event['id']}"

                if st.session_state.get(confirm_key):
                    if st.button(
                        "Confirm",
                        key=f"manage_confirm_{event['id']}",
                        use_container_width=True,
                    ):
                        delete_event(event["id"])
                        st.session_state[confirm_key] = False
                        st.rerun()

                    if st.button(
                        "Cancel",
                        key=f"manage_cancel_{event['id']}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = False
                        st.rerun()
                else:
                    if st.button(
                        "Delete",
                        key=f"manage_delete_{event['id']}",
                        use_container_width=True,
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()

def page_admin() -> None:
    if not is_admin():
        st.error("You do not have access to this page.")
        return

    if st.button("← Back to Manage Events"):
        set_page("Manage Events")
        st.rerun()

    st.header("Event Approval")
    events = get_pending_events()

    if not events:
        st.info("There are no pending events.")
        return

    for event in events:
        with st.container(border=True):
            st.subheader(event["title"])
            st.write(f"Organizer: {event['organizer'] or 'Not provided'}")
            st.write(f"When: {event['start_at']}")

            location = ", ".join(
                part
                for part in [
                    event["address"],
                    event["city"],
                    event["state"],
                    event["zip_code"],
                ]
                if part
            )

            if location:
                st.write(f"Location: {location}")

            approve_col, reject_col = st.columns(2)

            with approve_col:
                if st.button(
                    "Approve",
                    key=f"approve_{event['id']}",
                    use_container_width=True,
                ):
                    set_event_approval_status(event["id"], "approved")
                    st.rerun()

            with reject_col:
                if st.button(
                    "Reject",
                    key=f"reject_{event['id']}",
                    use_container_width=True,
                ):
                    set_event_approval_status(event["id"], "rejected")
                    st.rerun()

def page_profile() -> None:
    if not st.session_state.user:
        st.warning("Please log in to view your profile.")
        c1, c2, c3 = st.columns([2, 1, 2])
        with c2:
            if st.button("Go to Login", use_container_width=True):
                set_page("Login")
                st.rerun()
        return

    user = get_user_by_id(st.session_state.user["id"])

    st.header("My Profile")
    st.caption("View and update your account information.")

    with st.form("profile_form"):
        first_name = st.text_input(
            "First Name",
            value=user["first_name"],
        )

        last_name = st.text_input(
            "Last Name",
            value=user["last_name"],
        )

        email = st.text_input(
            "Email",
            value=user["email"],
        )

        submitted = st.form_submit_button("Save Changes")

    if submitted:
        try:
            update_user(
                user["id"],
                first_name,
                last_name,
                email,
            )

            st.session_state.user = {
                "id": user["id"],
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            }

            st.success("Profile updated successfully.")
            st.rerun()

        except ValueError as e:
            st.error(str(e))

    st.divider()

    if st.button("Return to Dashboard", use_container_width=True):
        set_page("Dashboard")
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
    elif st.session_state.page == "Create Event":
        page_create_event()
    elif st.session_state.page == "View Event":
        page_view_event()
    elif st.session_state.page == "Modify Event":
        page_modify_event()
    elif st.session_state.page == "Dashboard":
        page_dashboard()
    elif st.session_state.page == "Manage Events":
        page_manage_events()
    elif st.session_state.page == "Admin":
        page_admin()
    elif st.session_state.page == "Profile":
        page_profile()
    else:
        set_page("Home")
        st.rerun()



if __name__ == "__main__":
    main()
