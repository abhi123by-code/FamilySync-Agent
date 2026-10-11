from __future__ import annotations

import json
import os
import time
import calendar as month_calendar
from datetime import date, datetime, timedelta
from html import escape

import streamlit as st
from dotenv import load_dotenv

from core.models import Event, FamilyMember, Task
from core.festivals import get_festival_for_date
from data.family_store import load_events_and_tasks, save_events_and_tasks, save_json_backup
from orchestrator import Orchestrator

load_dotenv()

APP_DATA_PATH = os.path.join("data", "family_state.json")


def load_family_data():
    with open("data/sample_family.json", "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    members = [FamilyMember(**member) for member in payload["family_members"]]
    events = [Event(**event) for event in payload["events"]]
    tasks = [Task(**task) for task in payload["tasks"]]
    return payload, members, events, tasks


def save_state_to_disk():
    payload = {
        "demo_user": st.session_state.payload.get("demo_user", "Abhi"),
        "family_members": [member.model_dump() for member in st.session_state.members],
        "events": st.session_state.events,
        "tasks": st.session_state.tasks,
    }
    os.makedirs("data", exist_ok=True)
    save_events_and_tasks(st.session_state.events, st.session_state.tasks)
    save_json_backup(payload)


def load_state_from_disk():
    try:
        events, tasks = load_events_and_tasks()
        if events or tasks:
            payload = {"demo_user": "Abhi", "family_members": [member.model_dump() for member in load_family_data()[1]], "events": events, "tasks": tasks}
            members = [FamilyMember(**member) for member in payload["family_members"]]
            return payload, members, events, tasks
    except Exception:
        pass

    if not os.path.exists(APP_DATA_PATH):
        return None
    with open(APP_DATA_PATH, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not payload:
        return None
    members = [FamilyMember(**member) for member in payload["family_members"]]
    return payload, members, payload["events"], payload["tasks"]


def init_state():
    if "app_loaded" not in st.session_state:
        saved = load_state_from_disk()
        if saved is not None:
            payload, members, events, tasks = saved
        else:
            payload, members, events, tasks = load_family_data()
        st.session_state.payload = payload
        st.session_state.members = members
        st.session_state.events = [event if isinstance(event, dict) else event.model_dump() for event in events]
        st.session_state.tasks = [task if isinstance(task, dict) else task.model_dump() for task in tasks]
        st.session_state.page = "dashboard"
        st.session_state.theme_mode = "light"
        st.session_state.splash_start = time.time()
        st.session_state.splash_complete = False
        st.session_state.result = None
        st.session_state.decision_log = ["System initialized."]
        st.session_state.app_loaded = True


def get_current_time_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 21:
        return "Good evening"
    return "Good night"


def render_splash():
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    st.markdown(
        """
        <style>
        .splash-app {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, #edf5ff 0%, #f4ecff 100%);
            text-align: center;
            padding: 2rem;
        }
        .splash-card {
            width: min(100%, 700px);
            min-height: 80vh;
            border-radius: 28px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            position: relative;
            background: rgba(255,255,255,0.55);
            border: 1px solid rgba(140, 165, 255, 0.28);
            box-shadow: 0 20px 60px rgba(72, 91, 166, 0.12);
        }
        .splash-title {
            font-size: clamp(2.2rem, 4vw, 4rem);
            font-weight: 800;
            color: #1d3557;
            margin-bottom: 0.5rem;
        }
        .splash-name {
            font-size: clamp(1.2rem, 2.5vw, 2.2rem);
            font-weight: 600;
            color: #3d5a80;
            margin-bottom: 4rem;
        }
        .splash-brand {
            position: absolute;
            bottom: 2.2rem;
            left: 50%;
            transform: translateX(-50%);
            font-size: clamp(0.9rem, 1.8vw, 1.2rem);
            font-weight: 700;
            letter-spacing: 0.08em;
            color: #5b6b8d;
            text-transform: uppercase;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="splash-app">
            <div class="splash-card">
                <div class="splash-title">Welcome Back!</div>
                <div class="splash-name">{user_name}</div>
                <div class="splash-brand">FamilySync Agent</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    elapsed = time.time() - st.session_state.splash_start
    if elapsed >= 5:
        st.session_state.splash_complete = True
        st.rerun()
    else:
        time.sleep(0.2)
        st.rerun()


def render_sidebar(page_name="dashboard"):
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    st.markdown(
        """
        <style>
        .page-shell {
            margin-top: 0;
            padding-top: 0;
        }
        .page-nav {
            background: transparent;
            border-radius: 0;
            border: 0;
            padding: 0.75rem 0 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.75rem;
            box-shadow: none;
        }
        .page-logo {
            width: 52px; height: 52px; margin: 0 auto 0.35rem;
            box-sizing: border-box; overflow: visible; border-radius: 50%;
            background: linear-gradient(135deg,#8ec5ff,#cda8ff);
            color: #183a5e; font-weight: 800; display:flex; align-items:center; justify-content:center;
            font-size: 1.1rem; box-shadow: 0 10px 20px rgba(132,156,255,0.28);
        }
        .page-nav .stButton > button {
            width: 52px !important;
            height: 52px !important;
            border-radius: 16px !important;
            border: 1px solid rgba(146, 167, 224, 0.24) !important;
            background: #ffffff !important;
            color: #47638c !important;
            font-size: 1.45rem !important;
            padding: 0 !important;
            box-shadow: 0 8px 18px rgba(118, 134, 185, 0.12) !important;
        }
        .page-nav .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(78, 118, 215, 0.45) !important;
            box-shadow: 0 12px 24px rgba(94, 118, 191, 0.18) !important;
        }
        .st-key-page_navigation {
            padding: 10px 4px 12px !important;
            overflow: visible !important;
        }
        .st-key-page_navigation [data-testid="stVerticalBlock"],
        .st-key-page_navigation .stMarkdown {
            overflow: visible !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    nav_cols = st.columns([0.8, 5])
    with nav_cols[0]:
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        with st.container(key="page_navigation"):
            st.markdown(f'<div class="page-logo">{user_name[:2].upper()}</div>', unsafe_allow_html=True)
            menu = [
                ("🏠", "dashboard"),
                ("🗓️", "calendar"),
                ("💬", "chat"),
                ("📊", "analytics"),
                ("⚙️", "settings"),
                ("ℹ️", "about"),
            ]
            for icon, key in menu:
                if st.button(icon, key=f"nav_{key}", help=key.title(), use_container_width=True):
                    st.session_state.page = key
            if st.button("↺", key="reset_demo_data_sidebar", help="Reset demo data", use_container_width=True):
                payload, members, events, tasks = load_family_data()
                st.session_state.payload = payload
                st.session_state.members = members
                st.session_state.events = [event.model_dump() for event in events]
                st.session_state.tasks = [task.model_dump() for task in tasks]
                st.session_state.result = None
                st.session_state.decision_log = ["Demo data restored."]
                save_state_to_disk()
                st.rerun()

    with nav_cols[1]:
        if page_name == "calendar":
            render_calendar()
        elif page_name == "chat":
            render_chat()
        elif page_name == "analytics":
            render_analytics()
        elif page_name == "settings":
            render_settings()
        elif page_name == "about":
            render_about()
        elif page_name == "add_event":
            render_add_event_page()


def get_weather_summary():
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        weather_status = "Sunny"
        emoji = "☀️"
        suggestion = "Good morning! A bright day ahead — carry a water bottle and enjoy the clear light."
    elif 12 <= current_hour < 17:
        weather_status = "Partly cloudy"
        emoji = "⛅"
        suggestion = "A mild afternoon — keep sunglasses handy and stay comfortable outdoors."
    elif 17 <= current_hour < 21:
        weather_status = "Rainy"
        emoji = "🌧️"
        suggestion = "Heavy rain expected later — take an umbrella and leave a little extra time for travel."
    else:
        weather_status = "Clear night"
        emoji = "🌙"
        suggestion = "It is a calm night — a quiet evening is ideal for rest and planning."
    return weather_status, emoji, suggestion


@st.dialog("Weekly Family Todo List")
def show_weekly_todo_dialog():
    st.markdown("### This Week")
    for member in st.session_state.members:
        member_tasks = [task for task in st.session_state.tasks if task.get("owner") == member.name]
        if not member_tasks:
            continue
        st.markdown(f"**{member.name}**")
        for task in member_tasks:
            st.write(f"- {task['title']} — {task['start'][:10]} at {task['start'][11:16]}")


@st.dialog("Monthly Family Todo List")
def show_monthly_todo_dialog():
    st.markdown("### This Month")
    for task in sorted(st.session_state.tasks, key=lambda item: item["start"]):
        st.write(f"- **{task['title']}** — {task['owner']} — {task['start']} to {task['end']}")


def render_add_event_page():
    st.markdown(
        """
        <style>
        .section-shell { background: linear-gradient(135deg,#f8fbff,#edf7ff); border-radius: 22px; padding: 1.5rem; border: 1px solid #dfe8ff; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.title("Add Family Event")
    st.caption("Check the family calendar before saving the new event to avoid schedule conflicts.")
    with st.form("event_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Title")
            member = st.selectbox("Member", [m.name for m in st.session_state.members], index=0)
            category = st.selectbox("Category", ["personal", "school", "medical", "pickup", "errand", "family"])
        with col2:
            event_date = st.date_input("Date")
            start_time = st.time_input("Start time")
            end_time = st.time_input("End time")
        notes = st.text_area("Notes", height=100)
        submitted = st.form_submit_button("Check schedule", use_container_width=True)

        if submitted and title:
            start_dt = datetime.combine(event_date, start_time).isoformat(timespec="seconds")
            end_dt = datetime.combine(event_date, end_time).isoformat(timespec="seconds")
            event = Event(
                id=f"evt-{int(time.time())}",
                title=title,
                member=member,
                start=start_dt,
                end=end_dt,
                category=category,
                notes=notes,
            )
            orchestrator = Orchestrator(
                st.session_state.members,
                [Event(**e) for e in st.session_state.events],
                [Task(**t) for t in st.session_state.tasks],
            )
            result = orchestrator.coordinate_event(title, event)
            st.session_state.result = result.model_dump()
            st.session_state.decision_log = result.decision_log
            if result.status == "resolved":
                st.success(f"AI recommendation: {result.recommendation}")
            elif result.status == "rejected":
                st.warning(result.explanation)
            else:
                st.info(result.explanation)

            if result.status == "resolved":
                accept = st.checkbox("Accept recommendation and save event")
                if accept:
                    st.session_state.events.append(event.model_dump())
                    save_state_to_disk()
                    st.success("Event has been added to the family schedule.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_dashboard():
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    weather_status, weather_icon, weather_tip = get_weather_summary()
    greeting = get_current_time_greeting()
    today = datetime.now().strftime("%A, %d %B %Y")
    clock = datetime.now().strftime("%I:%M %p")

    st.markdown(
        """
        <style>
        .home-shell {
            min-height: auto;
            background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
            border-radius: 28px;
            padding: 0.2rem 0.25rem 0.5rem 0.25rem;
            margin-top: 0;
        }
        .nav-rail {
            background: linear-gradient(180deg, #f8faff, #edf4ff);
            border-radius: 26px;
            padding: 0.9rem 0.7rem;
            border: 1px solid #dde9ff;
            min-height: auto;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.8rem;
            box-shadow: 0 20px 40px rgba(81, 106, 170, 0.12);
            margin-top: 0;
        }
        .nav-logo {
            width: 52px; height: 52px; margin: 0 auto 0.35rem;
            box-sizing: border-box; overflow: visible; border-radius: 50%;
            background: linear-gradient(135deg,#8ec5ff,#cda8ff);
            color: #183a5e; font-weight: 800; display:flex; align-items:center; justify-content:center; margin-bottom: 0.4rem;
            font-size: 1.1rem; box-shadow: 0 10px 20px rgba(132,156,255,0.28);
        }
        .st-key-home_navigation,
        .st-key-page_navigation {
            padding: 10px 4px 12px !important;
            overflow: visible !important;
        }
        .st-key-home_navigation [data-testid="stVerticalBlock"],
        .st-key-page_navigation [data-testid="stVerticalBlock"] {
            gap: 0.75rem;
            overflow: visible !important;
        }
        .st-key-home_navigation .stMarkdown,
        .st-key-page_navigation .stMarkdown {
            overflow: visible !important;
        }
        .nav-rail .stButton > button {
            width: 52px !important;
            height: 52px !important;
            border-radius: 16px !important;
            border: 1px solid rgba(146, 167, 224, 0.24) !important;
            background: #ffffff !important;
            color: #47638c !important;
            font-size: 1.45rem !important;
            padding: 0 !important;
            box-shadow: 0 8px 18px rgba(118, 134, 185, 0.12) !important;
        }
        .nav-rail .stButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(78, 118, 215, 0.45) !important;
            box-shadow: 0 12px 24px rgba(94, 118, 191, 0.18) !important;
        }
        .header-row {
            display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.85rem; margin-top: 0; gap: 0.8rem;
        }
        .title-text { font-size: clamp(2rem, 2.5vw, 2.8rem); font-weight: 800; color: #1d3557; margin: 0; }
        .meta-text { font-size: 0.88rem; color: #5d6f8d; font-weight: 700; background: rgba(227, 235, 255, 0.8); border: 1px solid rgba(149,169,211,0.3); border-radius: 999px; padding: 0.5rem 0.8rem; }
        .glass-card {
            background: linear-gradient(135deg, rgba(255,255,255,0.98), rgba(243,247,255,0.98));
            border-radius: 24px; border: 1px solid rgba(156,171,209,0.22); box-shadow: 0 18px 36px rgba(81,109,176,0.12); padding: 1.25rem; height: 100%;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .glass-card:hover { transform: translateY(-2px); box-shadow: 0 20px 40px rgba(81,109,176,0.15); }
        .greeting-badge {
            display: inline-flex; align-items: center; gap: 0.5rem; border-radius: 999px; background: linear-gradient(135deg, rgba(115,165,255,0.14), rgba(202,168,255,0.12)); color: #2a5bbd; padding: 0.38rem 0.8rem; font-weight: 700; margin-bottom: 0.9rem;
        }
        .weather-tile { background: linear-gradient(135deg, #edf7ff, #f2edff); }
        .weather-emoji { font-size: 2.8rem; display: block; margin-top: 0.35rem; }
        .section-title {
            font-size: 1.05rem; font-weight: 800; color: #1d3557; margin: 0 0 0.7rem 0;
        }
        .task-row {
            display:flex; justify-content:space-between; align-items:center; gap: 0.8rem; padding: 0.9rem 1rem; border-radius: 16px; background: linear-gradient(180deg, #fbfdff, #f4f8ff); border: 1px solid #e3ebf8; margin-bottom: 0.7rem; box-shadow: 0 6px 16px rgba(118,130,172,0.05);
        }
        .task-row strong { color: #1f3357; }
        .task-row small { color: #5e7397; }
        .status-pill { border-radius: 999px; padding: 0.38rem 0.7rem; font-size: 0.72rem; font-weight: 800; }
        .status-pending { background: #fff3da; color: #b26d00; }
        .status-done { background: #dff9ec; color: #0c7b4d; }
        .quick-panel {
            display: flex; flex-direction: column; gap: 0.8rem; padding: 0; background: transparent; border: none; border-radius: 0;
        }
        .quick-panel .stButton > button {
            border: 1px solid rgba(132, 158, 220, 0.18) !important;
            background: linear-gradient(135deg, #f2f7ff, #f6f8ff) !important;
            color: #234075 !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            box-shadow: none !important;
        }
        .quick-panel .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 12px 22px rgba(99, 122, 195, 0.12) !important;
        }
        .hero-avatar {
            width: 62px; height: 62px; border-radius: 50%; background: linear-gradient(135deg,#9ed0ff,#d7c6ff); display:flex; align-items:center; justify-content:center; font-size: 2rem; box-shadow: 0 12px 24px rgba(133, 148, 211, 0.16);
        }
        .festival-card {
            display: grid;
            grid-template-columns: 68px minmax(0, 1fr);
            align-items: center;
            gap: 0.9rem;
            margin-top: 1.25rem;
            padding: 1rem;
            border: 1px solid rgba(149, 169, 211, 0.28);
            border-radius: 22px;
            background: linear-gradient(135deg, #fff9e9, #fff1f5 55%, #f2f5ff);
            box-shadow: 0 14px 30px rgba(104, 111, 160, 0.10);
        }
        .festival-art {
            width: 64px;
            height: 64px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 20px;
            background: linear-gradient(135deg, #ffe5a3, #ffd9e8 58%, #dce6ff);
            font-size: 2.35rem;
            box-shadow: inset 0 1px 4px rgba(255,255,255,0.9), 0 8px 18px rgba(148, 116, 150, 0.14);
        }
        .festival-label {
            color: #76551c;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }
        .festival-name {
            color: #243b53;
            font-size: 1.05rem;
            font-weight: 800;
            line-height: 1.25;
            margin-top: 0.28rem;
        }
        .festival-message {
            color: #5d6b82;
            font-size: 0.82rem;
            line-height: 1.45;
            margin-top: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    nav_cols = st.columns([0.8, 5])
    with nav_cols[0]:
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        with st.container(key="home_navigation"):
            st.markdown('<div class="nav-logo">' + user_name[:2].upper() + '</div>', unsafe_allow_html=True)
            for label, icon, page_key, active in [
                ("Home", "🏠", "dashboard", st.session_state.page == "dashboard"),
                ("Calendar", "🗓️", "calendar", st.session_state.page == "calendar"),
                ("Family Chat", "💬", "chat", st.session_state.page == "chat"),
                ("Charts", "📊", "analytics", st.session_state.page == "analytics"),
                ("Settings", "⚙️", "settings", st.session_state.page == "settings"),
                ("About", "ℹ️", "about", st.session_state.page == "about"),
            ]:
                if st.button(icon, key=f"nav_{page_key}", help=label, use_container_width=True):
                    st.session_state.page = page_key

    with nav_cols[1]:
        st.markdown('<div class="home-shell">', unsafe_allow_html=True)
        st.markdown('<div class="header-row"><h2 class="title-text">Hi, ' + user_name + '</h2><div class="meta-text">' + today + ' · ' + clock + '</div></div>', unsafe_allow_html=True)

        top_row = st.columns([2, 1])
        with top_row[0]:
            st.markdown(
                f"""
                <div class="glass-card">
                    <div class="greeting-badge">✨ Personal assistant</div>
                    <div style="display:flex; align-items:center; gap:1rem;">
                        <div class="hero-avatar">🧑</div>
                        <div>
                            <div style="font-size:1.22rem; font-weight:800; color:#1d3557;">{greeting}, {user_name}</div>
                            <div style="font-size:0.96rem; color:#4d648a; margin-top:0.3rem;">Your schedule is organized and ready to review.</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with top_row[1]:
            st.markdown(
                f"""
                <div class="glass-card weather-tile">
                    <div style="font-size:0.8rem; font-weight:800; color:#345692; text-transform:uppercase; letter-spacing:0.08em;">Today Weather</div>
                    <div style="font-size:1.3rem; font-weight:800; color:#1d3557; margin-top:0.5rem;">{weather_status}</div>
                    <div class="weather-emoji">{weather_icon}</div>
                    <div style="margin-top:0.75rem; color:#496b97; font-size:0.92rem; line-height:1.45;">{weather_tip}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

        lower = st.columns([1.5, 1])
        with lower[0]:
            st.markdown("<div class='section-title'>To-Do Today</div>", unsafe_allow_html=True)
            personal_tasks = [task for task in st.session_state.tasks if task.get("owner") == user_name]
            if personal_tasks:
                for task in personal_tasks:
                    done = bool(task.get("completed", False))
                    row = st.columns([4, 1])
                    with row[0]:
                        st.markdown(f"<div class='task-row'><div><strong>{task['title']}</strong><br><small>{task['start']}</small></div></div>", unsafe_allow_html=True)
                    with row[1]:
                        if st.checkbox("Done", value=done, key=f"home_task_{task['id']}"):
                            task["completed"] = True
                        else:
                            task["completed"] = False
                        save_state_to_disk()
            else:
                st.info("No personal tasks scheduled for today.")

            st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>Household Tasks</div>", unsafe_allow_html=True)
            household = [task for task in st.session_state.tasks if task.get("owner") != user_name]
            if household:
                for task in household:
                    status = "Done" if task.get("completed", False) else "Pending"
                    pill_class = "status-done" if task.get("completed", False) else "status-pending"
                    st.markdown(f"<div class='task-row'><div><strong>{task['title']}</strong><br><small>{task['owner']} · {task['start']}</small></div><span class='status-pill {pill_class}'>{status}</span></div>", unsafe_allow_html=True)
            else:
                st.info("No household tasks for the family today.")

        with lower[1]:
            st.markdown("<div class='section-title'>Quick actions</div>", unsafe_allow_html=True)
            st.markdown('<div class="quick-panel">', unsafe_allow_html=True)
            if st.button("+ Add Event", key="add_event_btn", use_container_width=True):
                st.session_state.page = "add_event"
                st.rerun()

            if st.button("View weekly family list", key="weekly_todo_button", use_container_width=True):
                show_weekly_todo_dialog()

            if st.button("View monthly todo list", key="monthly_todo_button", use_container_width=True):
                show_monthly_todo_dialog()

            if st.button("Open calendar", use_container_width=True):
                st.session_state.page = "calendar"
                st.rerun()
            if st.button("Open charts", use_container_width=True):
                st.session_state.page = "analytics"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

            festival = get_festival_for_date(datetime.now().date())
            festival_name = festival.name if festival else "No major festival today"
            festival_message = (
                festival.message
                if festival
                else "We'll celebrate the next special day with you right here."
            )
            festival_emoji = festival.emoji if festival else "✨"
            st.markdown(
                f"""
                <div class="festival-card">
                    <div class="festival-art" role="img" aria-label="{festival_name} illustration">{festival_emoji}</div>
                    <div>
                        <div class="festival-label">Today's festival</div>
                        <div class="festival-name">{festival_name}</div>
                        <div class="festival-message">{festival_message}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("result"):
        st.markdown("### Decision Log")
        for entry in st.session_state.decision_log:
            st.write(f"- {entry}")


def render_page_title(title: str):
    title_color = "#f4f7ff" if st.session_state.get("theme_mode") == "dark" else "#1d3557"
    st.markdown(
        f"""
        <style>
        .page-title-shell {{
            display: block;
            margin: 0 0 0.8rem 0;
            padding: 0.75rem 0 0.15rem;
        }}
        .page-title-shell h3 {{
            margin: 0;
            font-size: clamp(2rem, 2.4vw, 2.8rem);
            font-weight: 800;
            color: {title_color};
            line-height: 1.25;
        }}
        </style>
        <div class="page-title-shell"><h3>{title}</h3></div>
        """,
        unsafe_allow_html=True,
    )


def _calendar_entries():
    entries = []
    for event_data in st.session_state.events:
        event = Event(**event_data)
        start = datetime.fromisoformat(event.start)
        end = datetime.fromisoformat(event.end)
        entries.append(
            {
                "title": event.title,
                "owner": event.member,
                "start": start,
                "end": end,
                "category": event.category,
                "kind": "Event",
            }
        )
    for task in st.session_state.tasks:
        start = datetime.fromisoformat(task["start"])
        end = datetime.fromisoformat(task["end"])
        entries.append(
            {
                "title": task["title"],
                "owner": task["owner"],
                "start": start,
                "end": end,
                "category": task.get("category", "household"),
                "kind": "Task",
            }
        )
    return sorted(entries, key=lambda entry: entry["start"])


def _calendar_month_offset(current: date, offset: int) -> date:
    month_index = current.year * 12 + current.month - 1 + offset
    year, month = divmod(month_index, 12)
    return current.replace(year=year, month=month + 1, day=1)


def render_calendar():
    if "calendar_selected_date" not in st.session_state:
        st.session_state.calendar_selected_date = date.today()
    if "calendar_view" not in st.session_state:
        st.session_state.calendar_view = "Weekly"

    selected_date = st.session_state.calendar_selected_date
    entries = _calendar_entries()
    render_page_title("Family Calendar")
    st.markdown(
        """
        <style>
        .calendar-toolbar-title { font-size: 1.05rem; font-weight: 800; color: #233b59; }
        .calendar-day-header { text-align:center; padding:0.65rem 0.15rem; border-bottom:1px solid #dce4ef; color:#334155; }
        .calendar-day-header strong { display:block; font-size:1.2rem; }
        .calendar-day-header small { color:#718096; }
        .calendar-day-header.is-selected { color:#1473e6; border-bottom:3px solid #1473e6; }
        .calendar-event {
            margin:0.5rem 0; padding:0.55rem 0.6rem; border-radius:10px;
            background:#e8f2ff; border-left:3px solid #3984e8; color:#233b59;
            font-size:0.78rem; line-height:1.35;
        }
        .calendar-event small { display:block; color:#61758f; margin-top:0.2rem; }
        .calendar-event.category-medical { background:#fff0ed; border-color:#e78069; }
        .calendar-event.category-school { background:#eee9ff; border-color:#8c77db; }
        .calendar-event.category-family, .calendar-event.category-household { background:#e9f5eb; border-color:#68a878; }
        .calendar-event.category-errand { background:#fff4dd; border-color:#e2a940; }
        .calendar-month-cell {
            min-height:105px; padding:0.45rem; border:1px solid #e6ebf2;
            border-radius:10px; margin-bottom:0.4rem; color:#334155;
            background:rgba(255,255,255,0.76); font-size:0.75rem;
        }
        .calendar-month-cell.outside { opacity:0.42; }
        .calendar-month-cell.today { border-color:#3984e8; box-shadow:inset 0 0 0 1px #3984e8; }
        .calendar-month-cell strong { display:block; margin-bottom:0.25rem; }
        .calendar-month-item { overflow:hidden; white-space:nowrap; text-overflow:ellipsis; color:#4d648a; margin-top:0.16rem; }
        .calendar-side-card {
            padding:1rem; border:1px solid #e3eaf4; border-radius:18px;
            background:linear-gradient(180deg,#ffffff,#f5f8fd); margin-bottom:0.9rem;
        }
        .calendar-side-card h4 { margin:0 0 0.6rem; color:#233b59; }
        @media (max-width: 900px) {
            .calendar-month-cell { min-height:78px; padding:0.3rem; font-size:0.68rem; }
            .calendar-event { padding:0.4rem; font-size:0.7rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    toolbar = st.columns([0.45, 0.45, 2.2, 2.4, 0.65, 0.8])
    with toolbar[0]:
        if st.button("‹", key="calendar_previous", help="Previous period"):
            if st.session_state.calendar_view == "Monthly":
                st.session_state.calendar_selected_date = _calendar_month_offset(selected_date, -1)
            else:
                st.session_state.calendar_selected_date = selected_date - timedelta(days=7 if st.session_state.calendar_view == "Weekly" else 1)
            st.rerun()
    with toolbar[1]:
        if st.button("›", key="calendar_next", help="Next period"):
            if st.session_state.calendar_view == "Monthly":
                st.session_state.calendar_selected_date = _calendar_month_offset(selected_date, 1)
            else:
                st.session_state.calendar_selected_date = selected_date + timedelta(days=7 if st.session_state.calendar_view == "Weekly" else 1)
            st.rerun()
    with toolbar[2]:
        st.markdown(
            f"<div class='calendar-toolbar-title'>{selected_date.strftime('%B %Y')}</div>",
            unsafe_allow_html=True,
        )
    with toolbar[3]:
        st.radio(
            "Calendar view",
            ["Daily", "Weekly", "Monthly"],
            horizontal=True,
            key="calendar_view",
            label_visibility="collapsed",
        )
    with toolbar[4]:
        if st.button("Today", key="calendar_today"):
            st.session_state.calendar_selected_date = date.today()
            st.rerun()
    with toolbar[5]:
        if st.button("+ Add Event", key="calendar_add_event", use_container_width=True):
            st.session_state.page = "add_event"
            st.rerun()

    calendar_cols = st.columns([3.6, 1.15], gap="large")
    with calendar_cols[0]:
        if st.session_state.calendar_view == "Weekly":
            week_start = selected_date - timedelta(days=selected_date.weekday())
            week_days = [week_start + timedelta(days=offset) for offset in range(7)]
            day_columns = st.columns(7, gap="small")
            for day, day_column in zip(week_days, day_columns):
                with day_column:
                    selected_class = "is-selected" if day == selected_date else ""
                    st.markdown(
                        f"<div class='calendar-day-header {selected_class}'><strong>{day.day}</strong><small>{day.strftime('%a')}</small></div>",
                        unsafe_allow_html=True,
                    )
                    day_entries = [entry for entry in entries if entry["start"].date() == day]
                    if not day_entries:
                        st.markdown("<div style='height:2rem'></div>", unsafe_allow_html=True)
                    for entry in day_entries:
                        category = "".join(c for c in entry["category"].lower() if c.isalnum() or c == "-")
                        st.markdown(
                            f"<div class='calendar-event category-{category}'><strong>{escape(entry['title'])}</strong><small>{entry['start'].strftime('%I:%M %p')} · {escape(entry['owner'])}</small></div>",
                            unsafe_allow_html=True,
                        )
        elif st.session_state.calendar_view == "Daily":
            st.markdown(f"### {selected_date.strftime('%A, %B %d')}")
            day_entries = [entry for entry in entries if entry["start"].date() == selected_date]
            if not day_entries:
                st.info("Nothing scheduled for this day. Use Add Event to plan something.")
            for entry in day_entries:
                category = "".join(c for c in entry["category"].lower() if c.isalnum() or c == "-")
                st.markdown(
                    f"<div class='calendar-event category-{category}'><strong>{escape(entry['title'])}</strong><small>{entry['start'].strftime('%I:%M %p')}–{entry['end'].strftime('%I:%M %p')} · {escape(entry['owner'])} · {escape(entry['kind'])}</small></div>",
                    unsafe_allow_html=True,
                )
        else:
            month_start = selected_date.replace(day=1)
            month_weeks = month_calendar.Calendar(firstweekday=0).monthdatescalendar(
                selected_date.year, selected_date.month
            )
            weekday_columns = st.columns(7, gap="small")
            for weekday, weekday_column in zip(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"), weekday_columns):
                with weekday_column:
                    st.markdown(f"<div class='calendar-day-header'><small>{weekday}</small></div>", unsafe_allow_html=True)
            for week in month_weeks:
                week_columns = st.columns(7, gap="small")
                for day, day_column in zip(week, week_columns):
                    day_entries = [entry for entry in entries if entry["start"].date() == day]
                    classes = []
                    if day.month != month_start.month:
                        classes.append("outside")
                    if day == date.today():
                        classes.append("today")
                    items = "".join(
                        f"<div class='calendar-month-item'>• {escape(entry['title'])}</div>"
                        for entry in day_entries[:3]
                    )
                    if len(day_entries) > 3:
                        items += f"<small>+{len(day_entries) - 3} more</small>"
                    with day_column:
                        st.markdown(
                            f"<div class='calendar-month-cell {' '.join(classes)}'><strong>{day.day}</strong>{items}</div>",
                            unsafe_allow_html=True,
                        )

    with calendar_cols[1]:
        st.markdown(
            f"""
            <div class="calendar-side-card">
                <h4>Selected day</h4>
                <strong>{selected_date.strftime('%A, %d %B')}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )
        day_entries = [entry for entry in entries if entry["start"].date() == selected_date]
        st.markdown(
            f"<div class='calendar-side-card'><h4>Schedule</h4><span>{len(day_entries)} items planned</span></div>",
            unsafe_allow_html=True,
        )
        if day_entries:
            for entry in day_entries:
                st.caption(f"{entry['start'].strftime('%I:%M %p')} · {entry['title']}")
        else:
            st.caption("No events or tasks on this date yet.")
        st.markdown(
            f"<div class='calendar-side-card'><h4>Family</h4><span>{len(st.session_state.members)} members sharing the calendar</span></div>",
            unsafe_allow_html=True,
        )


def _chat_reply(message: str) -> str:
    lower = message.lower()
    if "pickup" in lower or "drop" in lower:
        return "I checked the family calendar. I’ll help avoid overlaps with existing commitments and keep pickup plans clear."
    if "cleanup" in lower or "household" in lower:
        return "Household tasks are listed for everyone. We can coordinate the next task around each person's schedule."
    if "today" in lower or "schedule" in lower:
        today = date.today()
        todays_entries = [entry for entry in _calendar_entries() if entry["start"].date() == today]
        if not todays_entries:
            return "The family calendar has no events or tasks scheduled for today. It looks like a good day to plan something together!"
        summary = ", ".join(f"{entry['title']} ({entry['start'].strftime('%I:%M %p')})" for entry in todays_entries[:3])
        return f"Here’s what I found for today: {summary}."
    return "I can help coordinate family events, pickups, and household tasks. Ask me about today's schedule or a specific plan."


def render_chat():
    render_page_title("Family Chat")
    st.markdown(
        """
        <style>
        .chat-shell-title { color:#26384e; font-size:1.1rem; font-weight:800; }
        .chat-panel {
            border:1px solid #e2e9f1; border-radius:18px;
            background:#ffffff; padding:0.9rem; margin-bottom:0.7rem;
        }
        .chat-contact-name { color:#26384e; font-weight:700; font-size:0.9rem; }
        .chat-contact-status { color:#8291a4; font-size:0.72rem; }
        .chat-message-row { display:flex; margin:0.7rem 0; }
        .chat-message-row.mine { justify-content:flex-end; }
        .chat-bubble {
            max-width:82%; border-radius:16px 16px 16px 4px;
            padding:0.65rem 0.8rem; background:#f0f3f7; color:#334155;
            font-size:0.86rem; line-height:1.45; overflow-wrap:anywhere;
        }
        .chat-message-row.mine .chat-bubble {
            background:#dfeeff; color:#234075; border-radius:16px 16px 4px 16px;
        }
        .chat-message-sender { display:block; font-size:0.68rem; font-weight:800; color:#74849a; margin-bottom:0.2rem; }
        .chat-detail-row { border-bottom:1px solid #edf0f4; padding:0.55rem 0; color:#506176; font-size:0.8rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("chat_contact", "Family Chat")
    st.session_state.setdefault("chat_threads", {})
    contacts = ["Family Chat", "FamilySync AI"] + [member.name for member in st.session_state.members]
    selected_contact = st.session_state.chat_contact
    chat_cols = st.columns([0.9, 2.5, 1.05], gap="medium")

    with chat_cols[0]:
        st.markdown("<div class='chat-shell-title'>Messages</div>", unsafe_allow_html=True)
        query = st.text_input("Search", placeholder="Search family", label_visibility="collapsed", key="chat_search")
        for contact in contacts:
            if query and query.lower() not in contact.lower():
                continue
            marker = "🟢" if contact != "FamilySync AI" else "✨"
            if st.button(f"{marker}  {contact}", key=f"chat_contact_{contact}", use_container_width=True):
                st.session_state.chat_contact = contact
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with chat_cols[1]:
        messages = st.session_state.chat_threads.setdefault(selected_contact, [])
        st.markdown(
            f"<div class='chat-panel'><div class='chat-shell-title'>{escape(selected_contact)}</div><div class='chat-contact-status'>{len(st.session_state.members)} family members · schedule-aware chat</div></div>",
            unsafe_allow_html=True,
        )
        with st.container(height=420, border=True):
            if not messages:
                st.markdown(
                    "<div class='chat-message-row'><div class='chat-bubble'><span class='chat-message-sender'>FamilySync</span>Welcome! Share a family plan or ask about today's schedule.</div></div>",
                    unsafe_allow_html=True,
                )
            for message in messages:
                mine = message["sender"] == st.session_state.payload.get("demo_user", "Abhi")
                row_class = "mine" if mine else ""
                st.markdown(
                    f"<div class='chat-message-row {row_class}'><div class='chat-bubble'><span class='chat-message-sender'>{escape(message['sender'])} · {escape(message['time'])}</span>{escape(message['text'])}</div></div>",
                    unsafe_allow_html=True,
                )

        with st.form("family_chat_form", clear_on_submit=True):
            input_cols = st.columns([5, 1])
            with input_cols[0]:
                message_text = st.text_input(
                    "Message",
                    placeholder="Write a message...",
                    label_visibility="collapsed",
                )
            with input_cols[1]:
                sent = st.form_submit_button("Send", use_container_width=True)
        if sent and message_text.strip():
            now = datetime.now().strftime("%I:%M %p")
            messages.append(
                {
                    "sender": st.session_state.payload.get("demo_user", "Abhi"),
                    "text": message_text.strip(),
                    "time": now,
                }
            )
            reply_sender = "FamilySync" if selected_contact == "FamilySync AI" else selected_contact
            messages.append(
                {"sender": reply_sender, "text": _chat_reply(message_text), "time": now}
            )
            st.rerun()

    with chat_cols[2]:
        st.markdown(
            f"""
            <div class="chat-panel">
                <div class="chat-shell-title">Chat details</div>
                <div class="chat-detail-row"><strong>{len(st.session_state.members)}</strong> family members</div>
                <div class="chat-detail-row">Shared family schedule</div>
                <div class="chat-detail-row">{len(st.session_state.events)} calendar events</div>
                <div class="chat-detail-row">{len(st.session_state.tasks)} household tasks</div>
            </div>
            <div class="chat-panel">
                <div class="chat-shell-title">Family</div>
                {"".join(f"<div class='chat-detail-row'>🟢 {escape(member.name)} <span style='color:#8291a4'>· {escape(member.role)}</span></div>" for member in st.session_state.members)}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_analytics():
    render_page_title("Analytics")
    task_counts = {member.name: sum(1 for task in st.session_state.tasks if task["owner"] == member.name) for member in st.session_state.members}
    total = max(sum(task_counts.values()), 1)
    for member in st.session_state.members:
        count = task_counts.get(member.name, 0)
        st.write(f"**{member.name}**")
        st.progress(count / total if total else 0)
        st.caption(f"{count} assigned tasks")


def render_settings():
    render_page_title("Settings")
    theme = st.radio("Appearance", ["Light mode", "Dark mode"], index=0 if st.session_state.get("theme_mode") == "light" else 1)
    if theme == "Dark mode":
        st.session_state.theme_mode = "dark"
    else:
        st.session_state.theme_mode = "light"

    st.markdown(
        """
        <style>
        .settings-shell {
            background: linear-gradient(135deg, #f6f9ff, #eef3ff);
            border-radius: 22px;
            padding: 1.2rem;
            border: 1px solid #dfe8ff;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="settings-shell">', unsafe_allow_html=True)
    st.checkbox("Enable AI recommendations", value=True)
    st.checkbox("Use demo weather", value=True)
    st.text_input("Timezone", value="Local system time")
    if st.button("Save current state"):
        save_state_to_disk()
        st.success("State saved successfully.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_about():
    render_page_title("About Us")
    st.markdown(
        """
        FamilySync Agent is a prototype for coordinating family schedules, shared responsibilities, and intelligent task assignment.
        It combines a deterministic scheduling engine with an LLM service fallback so the workflow is explainable, testable, and easy to present to judges.
        """
    )


def main():
    st.set_page_config(page_title="FamilySync Agent", layout="wide")
    init_state()

    st.markdown(
        """
        <style>
        section.main > div {
            padding-top: 0 !important;
        }
        .block-container {
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            margin-top: 0 !important;
        }
        .stApp {
            padding-top: 0 !important;
        }
        div[data-testid="stHeader"] {
            display: none;
        }
        div[data-testid="stVerticalBlock"], div[data-testid="stVerticalBlockBorderWrapper"] {
            margin-top: 0 !important;
        }
        .main .block-container {
            padding-top: 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    if st.session_state.get("theme_mode") == "dark":
        st.markdown(
            """
            <style>
            .stApp { background: linear-gradient(180deg, #0f172a, #111827); color: #e5eef8; }
            div[data-testid="stAppViewContainer"] > .main { background: transparent; }
            </style>
            """,
            unsafe_allow_html=True,
        )

    if not st.session_state.get("splash_complete", False):
        render_splash()
        return

    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        render_dashboard()
    else:
        render_sidebar(page)


if __name__ == "__main__":
    main()
