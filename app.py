from __future__ import annotations

import json
import os
import time
import calendar as month_calendar
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
import tomllib

import streamlit as st
from dotenv import load_dotenv

from core.models import Event, FamilyMember, Task
from core.festivals import get_festival_for_date
from data.family_store import load_events_and_tasks, save_events_and_tasks, save_json_backup
from orchestrator import Orchestrator
from services.llm_service import LLMService

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
    st.session_state.setdefault("chat_contact", "Family Chat")
    st.session_state.setdefault("chat_threads", {})


def render_app_styles():
    st.markdown(
        """
        <style>
        :root {
            --page-bg: #f3f5fb;
            --surface: #ffffff;
            --surface-soft: #f5f6fc;
            --ink: #17233a;
            --muted: #71809d;
            --line: #e6eaf3;
            --purple: #7058f5;
            --purple-deep: #5d42e8;
            --green: #10b981;
            --orange: #f59e0b;
            --red: #f35e67;
        }
        .stApp { background: var(--page-bg) !important; color: var(--ink); }
        [data-testid="stAppViewContainer"], [data-testid="stMain"] { background: transparent !important; }
        .block-container { max-width: 1600px !important; padding: 3.5rem 1rem 1.4rem !important; }
        
        div[data-testid="stHeader"] { display: none; }
        .st-key-app-sidebar {
            min-height: calc(100vh - 1.8rem);
            padding: 1rem 0.7rem !important;
            border: 1px solid var(--line);
            border-radius: 16px;
            background: var(--surface);
            box-shadow: 0 8px 24px rgba(32, 48, 87, 0.06);
        }
        .brand-lockup { display:flex; align-items:center; gap:0.55rem; padding:0.15rem 0.15rem 1.2rem; color:var(--ink); font-size:1rem; font-weight:800; }
        .brand-mark { display:flex; width:30px; height:30px; align-items:center; justify-content:center; border-radius:9px; background:var(--purple); color:white; font-size:1rem; }
        .st-key-app-sidebar [data-testid="stVerticalBlock"] { gap:0.45rem; }
        .st-key-app-sidebar .stButton > button {
            min-height:36px; justify-content:flex-start; padding:0.35rem 0.65rem !important;
            border-radius:9px !important; border:1px solid transparent !important;
            background:transparent !important; color:#596987 !important; font-weight:650 !important;
            box-shadow:none !important; text-align:left !important;
        }
        .st-key-app-sidebar .stButton > button:hover { background:#f1efff !important; color:var(--purple-deep) !important; }
        .st-key-app-sidebar .stButton > button[kind="primary"] {
            background:linear-gradient(110deg,#6857f2,#9a46e8) !important;
            color:white !important; box-shadow:0 5px 12px rgba(104,87,242,0.22) !important;
        }
        .sidebar-profile { display:flex; align-items:center; gap:0.55rem; margin-top:1.2rem; padding:0.55rem; border-radius:10px; background:var(--surface-soft); color:var(--ink); font-size:0.8rem; }
        .profile-initial { display:grid; width:28px; height:28px; place-items:center; border-radius:50%; background:var(--purple); color:white; font-weight:750; }
        .topbar { display:flex; align-items:center; justify-content:flex-end; gap:0.55rem; margin-bottom:0.55rem; }
        .topbar .stTextInput { max-width:250px; }
        .topbar .stButton > button { min-height:34px; border:1px solid var(--line) !important; border-radius:999px !important; background:white !important; color:#596987 !important; font-size:0.8rem !important; box-shadow:none !important; }
        .page-heading { margin:0 0 0.8rem; }
        .page-heading .page-title { margin:0; color:var(--ink); font-size:1.75rem; line-height:1.2; font-weight:800; }
        .page-heading p { margin:0.2rem 0 0; color:var(--muted); font-size:0.84rem; }
        .ui-card { padding:0.9rem 1rem; border:1px solid var(--line); border-radius:14px; background:var(--surface); box-shadow:0 5px 18px rgba(34,48,81,0.045); }
        .ui-card-title { margin:0 0 0.65rem; color:var(--ink); font-size:0.98rem; font-weight:800; }
        .metric-label { color:var(--muted); font-size:0.75rem; }
        .metric-value { color:var(--ink); font-size:1.55rem; font-weight:800; line-height:1.15; }
        .st-key-dashboard-suggestion-panel { padding:0.75rem 0.85rem !important; border-radius:14px; background:linear-gradient(110deg,#654bea,#a12ee7); color:white; box-shadow:0 8px 20px rgba(96,65,222,0.18); }
        .st-key-dashboard-suggestion-panel [data-testid="stVerticalBlock"] { gap:0.35rem; }
        .st-key-dashboard-suggestion-panel .stButton > button { min-height:30px; padding:0.25rem 0.7rem !important; border-radius:9px !important; }
        .st-key-dashboard-suggestion-panel .stButton > button[kind="primary"] { background:#fff !important; color:#5d42e8 !important; border-color:#fff !important; }
        .st-key-dashboard-suggestion-panel .stButton > button[kind="secondary"] { background:rgba(255,255,255,0.22) !important; color:#fff !important; border-color:transparent !important; }
        .suggestion-card { min-height:0; margin:0; padding:0; border-radius:0; background:transparent; color:white; box-shadow:none; }
        .suggestion-eyebrow { margin-bottom:0.4rem; color:#efeaff; font-size:0.67rem; font-weight:800; text-transform:uppercase; }
        .suggestion-copy { color:white; font-size:1.12rem; font-weight:800; line-height:1.25; }
        .suggestion-subcopy { margin-top:0.35rem; color:#eee9ff; font-size:0.76rem; }
        .weather-card { display:flex; min-height:118px; align-items:center; justify-content:space-between; }
        .st-key-dashboard-weather-panel { min-height:118px; padding:0.75rem 0.85rem !important; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 5px 18px rgba(34,48,81,0.045); }
        .st-key-dashboard-weather-panel [data-testid="stHorizontalBlock"] { align-items:center; }
        .weather-current { color:var(--ink); font-size:1.65rem; font-weight:850; line-height:1.1; }
        .weather-condition { margin-top:0.22rem; color:var(--muted); font-size:0.74rem; }
        .weather-icon { text-align:center; font-size:2.65rem; }
        .eyebrow { color:var(--muted); font-size:0.68rem; font-weight:800; letter-spacing:0.08em; text-transform:uppercase; }
        .weather-status { margin:0.25rem 0; color:var(--ink); font-size:1.4rem; font-weight:800; }
        .weather-icon { font-size:2.5rem; }
        .muted { color:var(--muted); font-size:0.72rem; }
        .metric-card { min-height:62px; padding:0.55rem 0.75rem; }
        .dashboard-timeline, .workload-card, .assistant-card { margin-top:0.45rem; }
        .dashboard-timeline { min-height:0; }
        .timeline-row { display:flex; align-items:center; gap:0.55rem; margin:0.35rem 0; padding:0.52rem 0.58rem; border-radius:10px; background:var(--surface-soft); }
        .timeline-marker { width:4px; height:34px; flex:0 0 4px; border-radius:4px; background:var(--purple); }
        .timeline-copy { display:flex; min-width:0; flex:1; flex-direction:column; color:var(--ink); font-size:0.78rem; }
        .timeline-copy small { color:var(--muted); font-size:0.67rem; }
        .timeline-status { padding:0.18rem 0.4rem; border-radius:999px; background:#fff0d7; color:#c56c00; font-size:0.63rem; font-weight:750; }
        .workload-row { display:flex; align-items:center; gap:0.55rem; margin:0.65rem 0; color:var(--ink); font-size:0.76rem; }
        .workload-row > span { width:2rem; }
        .workload-track { height:7px; flex:1; overflow:hidden; border-radius:99px; background:#f0f2f8; }
        .workload-track i { display:block; height:100%; border-radius:inherit; background:var(--purple); }
        .assistant-preview { max-height:3.2rem; overflow:hidden; padding:0.5rem 0.6rem; border-radius:9px; background:var(--surface-soft); color:#394967; font-size:0.75rem; }
        .st-key-dashboard-festival-panel { margin-top:0.5rem; padding:0.55rem 0.7rem !important; border:1px solid #f7b2d6; border-radius:13px; background:linear-gradient(105deg,#f9ddea,#f8e5ce); }
        .st-key-dashboard-festival-panel [data-testid="stHorizontalBlock"] { align-items:center; }
        .festival-art { display:grid; width:38px; height:38px; place-items:center; border-radius:50%; background:#ffe7c2; font-size:1.45rem; }
        .festival-label { color:#e9468e; font-size:0.64rem; font-weight:800; letter-spacing:0.1em; text-transform:uppercase; }
        .festival-name { color:var(--ink); font-size:0.9rem; font-weight:800; }
        .festival-message { margin-top:0.15rem; color:var(--muted); font-size:0.67rem; line-height:1.3; }
        .st-key-dashboard-festival-panel .stButton > button { min-height:30px; padding:0.25rem 0.55rem !important; border-radius:8px !important; background:linear-gradient(100deg,#ef4f91,#f59e0b) !important; color:#fff !important; border-color:transparent !important; font-size:0.68rem !important; font-weight:750 !important; }
        .st-key-dashboard-assistant-panel { min-height:9rem; height:100%; margin-top:0.45rem; padding:0.75rem 0.8rem !important; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 5px 18px rgba(34,48,81,0.045); }
        .st-key-dashboard-assistant-panel [data-testid="stVerticalBlock"] { gap:0.5rem; }
        .st-key-dashboard-assistant-panel [data-testid="stForm"] { margin-top:auto; }
        .st-key-dashboard-assistant-panel .stTextInput input { min-height:32px; background:var(--surface-soft) !important; }
        .st-key-dashboard-assistant-panel [data-testid="stFormSubmitButton"] button { min-height:32px; padding:0.25rem 0.65rem !important; }
        [data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:14px !important; background:var(--surface) !important; }
        .status-summary { display:flex; align-items:baseline; gap:0.4rem; margin-bottom:0.3rem; color:var(--muted); font-size:0.75rem; }
        .status-summary strong { color:var(--ink); font-size:1.6rem; }
        .member-row { display:flex; align-items:center; gap:0.55rem; margin:0.35rem 0; padding:0.45rem; border-radius:9px; background:var(--surface-soft); color:var(--ink); font-size:0.78rem; }
        .member-row small { color:var(--muted); font-size:0.67rem; }
        .role-badge { margin-left:auto; padding:0.18rem 0.48rem; border-radius:999px; background:#d9f4ec; color:#0a9b74; font-size:0.64rem; font-weight:750; }
        .about-hero { margin-bottom:0.7rem; padding:1rem; border-radius:14px; background:linear-gradient(110deg,#654bea,#a12ee7); color:white; }
        .about-hero h2 { margin:0 0 0.25rem; color:white; font-size:1.35rem; }
        .about-hero p { margin:0; color:#f0eaff; font-size:0.82rem; }
        .feature-card { display:flex; min-height:104px; flex-direction:column; gap:0.3rem; margin-bottom:0.65rem; }
        .feature-card span { font-size:1.25rem; }
        .feature-card strong { color:var(--ink); font-size:0.82rem; }
        .feature-card small { color:var(--muted); font-size:0.7rem; line-height:1.35; }
        .step-row { margin:0.35rem 0; padding:0.55rem 0.65rem; border-radius:9px; background:var(--surface-soft); color:var(--ink); font-size:0.77rem; }
        .step-row small { display:block; margin-top:0.1rem; color:var(--muted); font-size:0.68rem; }
        .st-key-app-sidebar .stMarkdown { overflow:visible; }
        .stApp input, .stApp textarea, [data-baseweb="select"] > div { background:#fff; color:var(--ink); border-color:var(--line); }
        .stButton > button { border-radius:9px; }
        .stApp .stButton > button[kind="primary"] { background:linear-gradient(110deg,#6857f2,#9a46e8) !important; color:#fff !important; border-color:transparent !important; }
        .stTextInput input, .stTextArea textarea, [data-baseweb="select"] > div { border-radius:9px !important; }
        .stApp [data-testid="stDateInput"] input, .stApp [data-testid="stTimeInput"] input,
        .stApp [data-testid="stTextArea"] textarea { background:#f5f6fc !important; border-color:#e6eaf3 !important; }
        .stApp [data-testid="stFormSubmitButton"] button { min-height:34px; border-radius:9px !important; }
        .calendar-side-card { padding:0.8rem; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 5px 18px rgba(34,48,81,0.045); margin-bottom:0.65rem; }
        .calendar-side-card h4 { margin:0 0 0.5rem; color:var(--ink); font-size:0.9rem; }
        .event-check-success { padding:0.6rem 0.75rem; border-radius:10px; background:#e1f6ef; color:#0a9b74; font-size:0.8rem; font-weight:750; }
        .event-check-conflict { padding:0.6rem 0.75rem; border-radius:10px; background:#fff0ed; color:#d3444e; font-size:0.8rem; font-weight:750; }
        .suggestion-note { display:flex; gap:0.55rem; align-items:center; margin:0.35rem 0; padding:0.5rem 0.6rem; border-radius:9px; background:var(--surface-soft); color:var(--ink); font-size:0.76rem; }
        .suggestion-note i { width:4px; height:30px; flex:0 0 4px; border-radius:4px; background:var(--purple); }
        @media (max-width: 850px) {
            .block-container { padding:3.5rem 0.5rem 1rem !important; }
            .st-key-app-sidebar { min-height:auto; padding:0.55rem !important; }
            .brand-lockup { padding-bottom:0.45rem; }
            .st-key-app-sidebar .stButton > button { min-height:32px; padding:0.25rem 0.35rem !important; font-size:0.76rem !important; }
            .sidebar-profile { display:none; }
            .page-heading .page-title { font-size:1.45rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_app_sidebar() -> None:
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    user_role = next((member.role.title() for member in st.session_state.members if member.name == user_name), "Family member")
    with st.container(key="app-sidebar"):
        st.markdown(
            "<div class='brand-lockup'><span class='brand-mark'>&#128106;</span>FamilySync</div>",
            unsafe_allow_html=True,
        )
        navigation = [
            ("\U0001F3E0", "Dashboard", "dashboard"),
            ("\U0001F4C5", "Calendar", "calendar"),
            ("+", "Add Event", "add_event"),
            ("\U0001F4AC", "Family Chat", "chat"),
            ("\U0001F4CA", "Analytics", "analytics"),
            ("\u2699", "Settings", "settings"),
            ("\u2139", "About", "about"),
        ]
        for icon, label, page_key in navigation:
            if st.button(
                f"{icon}  {label}",
                key=f"shell_nav_{page_key}",
                type="primary" if st.session_state.page == page_key else "secondary",
                width="stretch",
            ):
                st.session_state.page = page_key
                st.rerun()
        st.markdown(
            f"<div class='sidebar-profile'><span class='profile-initial'>{user_name[:1].upper()}</span><span><strong>{escape(user_name)}</strong><br><small>{escape(user_role)}</small></span></div>",
            unsafe_allow_html=True,
        )


def render_topbar() -> None:
    controls = st.columns([0.8, 0.45, 0.38], gap="small", vertical_alignment="center")
    with controls[0]:
        theme_label = "Light" if st.session_state.get("theme_mode") != "dark" else "Dark"
        if st.button(theme_label, key="shell_theme", width="stretch"):
            st.session_state.theme_mode = "dark" if st.session_state.get("theme_mode") != "dark" else "light"
            st.rerun()
    with controls[1]:
        if st.button(chr(0x1F514), key="shell_notifications", help="Notifications", width="stretch"):
            st.toast("You are all caught up.")
    with controls[2]:
        initials = st.session_state.payload.get("demo_user", "Abhi")[:2].upper()
        st.markdown(f"<div class='profile-initial'>{escape(initials)}</div>", unsafe_allow_html=True)

def get_current_time_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good morning"
    if 12 <= hour < 17:
        return "Good afternoon"
    if 17 <= hour < 21:
        return "Good evening"
    return "Good night"


def get_dashboard_timestamp(current_time: datetime | None = None) -> tuple[str, str]:
    now = current_time or datetime.now()
    today = now.strftime("%A, %d %B %Y")
    clock = now.strftime("%I:%M %p")
    return today, clock


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


def render_dashboard_weather_panel() -> None:
    with st.container(key="dashboard-weather-panel"):
        details_col, icon_col = st.columns([4, 1], gap="small", vertical_alignment="center")
        with details_col:
            st.markdown(
                "<div class='eyebrow'>BENGALURU · DEMO FORECAST</div>",
                unsafe_allow_html=True,
            )
            st.markdown("<div class='weather-current'>27°C</div>", unsafe_allow_html=True)
            st.markdown("<div class='weather-status'>Sunny</div>", unsafe_allow_html=True)
            st.markdown(
                "<div class='weather-condition'>Good morning! A bright day ahead — carry a water bottle and enjoy the clear light.</div>",
                unsafe_allow_html=True,
            )
        with icon_col:
            st.markdown(
                f"<div class='weather-icon' aria-hidden='true'>{chr(0x2600)}{chr(0xFE0F)}</div>",
                unsafe_allow_html=True,
            )


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
    render_page_title(
        "Add Family Event",
        "Check the calendar before saving to avoid schedule conflicts.",
    )
    event_columns = st.columns([1.55, 1.05], gap="small")
    with event_columns[0]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Event details</div>", unsafe_allow_html=True)
            with st.form("event_form"):
                first_row = st.columns(2)
                with first_row[0]:
                    title = st.text_input("Title", placeholder="e.g. Gym work")
                with first_row[1]:
                    event_date = st.date_input("Date", value=date.today())
                second_row = st.columns(2)
                with second_row[0]:
                    member = st.selectbox("Member", [m.name for m in st.session_state.members], index=0)
                with second_row[1]:
                    category = st.selectbox("Category", ["personal", "school", "medical", "pickup", "errand", "family"])
                third_row = st.columns(2)
                with third_row[0]:
                    start_time = st.time_input("Start time", value=datetime.now().replace(second=0, microsecond=0).time())
                with third_row[1]:
                    end_time = st.time_input("End time", value=(datetime.now() + timedelta(hours=1)).replace(second=0, microsecond=0).time())
                notes = st.text_area("Notes", height=95, placeholder="Add useful details for your family")
                submitted = st.form_submit_button("Check schedule", type="primary")

        if submitted:
            if not title.strip():
                st.warning("Enter an event title before checking the schedule.")
            elif end_time <= start_time:
                st.warning("End time must be later than start time.")
            else:
                start_dt = datetime.combine(event_date, start_time).isoformat(timespec="seconds")
                end_dt = datetime.combine(event_date, end_time).isoformat(timespec="seconds")
                event = Event(
                    id=f"evt-{int(time.time())}", title=title.strip(), member=member,
                    start=start_dt, end=end_dt, category=category, notes=notes,
                )
                orchestrator = Orchestrator(
                    st.session_state.members,
                    [Event(**item) for item in st.session_state.events],
                    [Task(**item) for item in st.session_state.tasks],
                )
                result = orchestrator.coordinate_event(title, event)
                st.session_state.result = result.model_dump()
                st.session_state.decision_log = result.decision_log
                st.session_state.pending_event = event.model_dump()
                st.rerun()

        result = st.session_state.get("result")
        pending_event = st.session_state.get("pending_event")
        if result and pending_event:
            if result.get("status") == "resolved":
                st.success(result.get("recommendation", "Schedule check complete."))
                if st.button("Save event", key="save_checked_event", type="primary"):
                    st.session_state.events.append(pending_event)
                    st.session_state.pop("pending_event", None)
                    st.session_state.result = None
                    save_state_to_disk()
                    st.success("Event added to the family calendar.")
            else:
                st.error(result.get("explanation", "This time conflicts with the family schedule."))

    with event_columns[1]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Conflict check</div>", unsafe_allow_html=True)
            result = st.session_state.get("result")
            pending_event = st.session_state.get("pending_event")
            if result and pending_event and result.get("status") == "resolved":
                start_label = datetime.fromisoformat(pending_event["start"]).strftime("%I:%M %p").lstrip("0")
                end_label = datetime.fromisoformat(pending_event["end"]).strftime("%I:%M %p").lstrip("0")
                st.markdown(f"<div class='event-check-success'>No clashes found</div><p class='muted'>{escape(pending_event['member'])} is free from {start_label} to {end_label}.</p>", unsafe_allow_html=True)
            elif result and pending_event:
                st.markdown("<div class='event-check-conflict'>A schedule conflict was found</div>", unsafe_allow_html=True)
                st.caption(result.get("explanation", "Choose another time or family member."))
            else:
                st.markdown("<div class='event-check-success'>Check a time to see family availability</div>", unsafe_allow_html=True)
                st.caption("Existing events and tasks are checked before you save.")
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>AI suggestions</div>", unsafe_allow_html=True)
            for color, title_text, note in [
                ("#7058f5", "Best time slot", "Weekends at 6 AM suit your routine"),
                ("#f59e0b", "Set reminder", "Notify 30 min before"),
                ("#10b981", "Share with family", "Let family members see this event"),
            ]:
                st.markdown(f"<div class='suggestion-note'><i style='background:{color}'></i><span><strong>{title_text}</strong><br><small class='muted'>{note}</small></span></div>", unsafe_allow_html=True)

def render_dashboard():
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    entries = _calendar_entries()
    today_date = datetime.now().date()
    today_entries = [entry for entry in entries if entry["start"].date() == today_date]
    timeline_entries = today_entries or [entry for entry in entries if entry["start"] >= datetime.now()][:4]
    timeline_title = "Today's timeline" if today_entries else "Upcoming timeline"
    pending_tasks = [task for task in st.session_state.tasks if not task.get("completed", False)]
    completed_tasks = len(st.session_state.tasks) - len(pending_tasks)
    event_models = [Event(**event) for event in st.session_state.events]
    conflicts = Orchestrator(st.session_state.members, event_models, []).schedule_manager.detect_conflicts()
    member_task_counts = {
        member.name: sum(1 for task in st.session_state.tasks if task.get("owner") == member.name)
        for member in st.session_state.members
    }
    max_task_count = max(member_task_counts.values(), default=1) or 1
    greeting = get_current_time_greeting()
    today, clock = get_dashboard_timestamp()

    if 'last_tick' not in st.session_state:
        st.session_state.last_tick = time.time()
    tick = time.time()
    if tick - st.session_state.last_tick >= 60:
        st.session_state.last_tick = tick
        st.rerun()

    header = st.columns([5.2, 3.1], gap="small", vertical_alignment="center")
    with header[0]:
        st.markdown(
            f'<div class="page-heading"><div class="page-title">{greeting}, {escape(user_name)} &#128075;</div><p>{today} &middot; {clock} &middot; {len(st.session_state.members)} members &middot; {len(conflicts)} {"conflict" if len(conflicts) == 1 else "conflicts"} need attention</p></div>',
            unsafe_allow_html=True,
        )
    with header[1]:
        render_topbar()

    hero_cols = st.columns([1.65, 1], gap="small")
    with hero_cols[0]:
        conflict_text = conflicts[0].description if conflicts else "No schedule conflicts found. Your family's plans look clear."
        suggestion_key = conflicts[0].description if conflicts else "clear"
        with st.container(key="dashboard-suggestion-panel"):
            if st.session_state.get("dismissed_suggestion") != suggestion_key:
                st.markdown(
                    f"""
                    <div class="suggestion-card">
                        <div class="suggestion-eyebrow">✨ AI suggestion</div>
                        <div class="suggestion-copy">{escape(conflict_text)}</div>
                        <div class="suggestion-subcopy">Review the schedule before making changes.</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                suggestion_actions = st.columns([1, 0.65, 3], gap="small")
                with suggestion_actions[0]:
                    if st.button("Apply fix", key="dashboard_apply_suggestion", type="primary"):
                        st.session_state.page = "calendar"
                        st.rerun()
                with suggestion_actions[1]:
                    if st.button("Dismiss", key="dashboard_dismiss_suggestion"):
                        st.session_state.dismissed_suggestion = suggestion_key
                        st.rerun()
            else:
                st.markdown("<div class='suggestion-card'><strong>Suggestion dismissed</strong><br><span class='suggestion-subcopy'>You can review the schedule from Calendar.</span></div>", unsafe_allow_html=True)
    with hero_cols[1]:
        render_dashboard_weather_panel()

    metric_cols = st.columns([1, 1, 1, 1, 1.05], gap="small")
    metrics = [
        ("Events today", len(today_entries), "#17233a"),
        ("Tasks pending", len(pending_tasks), "#f59e0b"),
        ("Completed", completed_tasks, "#10b981"),
        ("Conflicts", len(conflicts), "#f35e67"),
    ]
    for column, (label, value, color) in zip(metric_cols[:4], metrics):
        with column:
            st.markdown(
                f"<div class='ui-card metric-card'><div class='metric-label'>{label}</div><div class='metric-value' style='color:{color}'>{value}</div></div>",
                unsafe_allow_html=True,
            )
    with metric_cols[4]:
        if st.button("+ Add Event", key="dashboard_add_event", type="primary", width="stretch"):
            st.session_state.page = "add_event"
            st.rerun()
                
    main_cols = st.columns([1.55, 1], gap="small")
    with main_cols[0]:
        st.markdown(f"<div class='ui-card dashboard-timeline'><div class='ui-card-title'>{timeline_title}</div>", unsafe_allow_html=True)
        if timeline_entries:
            for entry in timeline_entries[:5]:
                time_label = entry["start"].strftime("%I:%M %p").lstrip("0")
                entry_status = "Pending" if entry["kind"] == "Task" and not next(
                    (task.get("completed", False) for task in st.session_state.tasks if task.get("title") == entry["title"]),
                    False,
                ) else entry["kind"]
                st.markdown(
                    f"<div class='timeline-row'><span class='timeline-marker'></span><div class='timeline-copy'><strong>{escape(entry['title'])}</strong><small>{time_label} · {escape(entry['owner'])}</small></div><span class='timeline-status'>{entry_status}</span></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Nothing else is scheduled. Add an event to plan ahead.")
        st.markdown("</div>", unsafe_allow_html=True)
        festival = get_festival_for_date(today_date)
        festival_name = festival.name if festival else "Special Day"
        festival_message = festival.message if festival else "A good day to plan a moment together."
        festival_emoji = festival.emoji if festival else chr(0x2728)
        with st.container(key="dashboard-festival-panel"):
            art_col, copy_col, action_col = st.columns([0.5, 3.2, 1.55], gap="small", vertical_alignment="center")
            with art_col:
                st.markdown(f"<div class='festival-art' role='img' aria-label='{escape(festival_name)} illustration'>{festival_emoji}</div>", unsafe_allow_html=True)
            with copy_col:
                st.markdown(
                    f"<div class='festival-label'>&#10024; Today's festival &middot; {today_date.strftime('%d %B')}</div><div class='festival-name'>{escape(festival_name)}</div><div class='festival-message'>{escape(festival_message)}</div>",
                    unsafe_allow_html=True,
                )
            with action_col:
                if st.button("Plan a family moment", key="dashboard_festival_plan", type="primary", width="stretch"):
                    st.session_state.page = "add_event"
                    st.rerun()


    with main_cols[1]:
        st.markdown("<div class='ui-card workload-card'><div class='ui-card-title'>Family workload</div>", unsafe_allow_html=True)
        for member in st.session_state.members:
            count = member_task_counts[member.name]
            width = int(count / max_task_count * 100) if count else 0
            st.markdown(
                f"<div class='workload-row'><span>{escape(member.name)}</span><div class='workload-track'><i style='width:{width}%'></i></div></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        latest_ai = next(
            (
                item["text"]
                for item in reversed(st.session_state.get("chat_threads", {}).get("FamilySync AI", []))
                if item["sender"] == "FamilySync"
            ),
            "Ask about the family schedule or how to share tasks.",
        )
        with st.container(key="dashboard-assistant-panel"):
            st.markdown(
                f"<div class='ui-card-title'>&#128172; FamilySync AI</div><div class='assistant-preview'>{escape(latest_ai)}</div>",
                unsafe_allow_html=True,
            )
            with st.form("dashboard_ai_form", clear_on_submit=True):
                prompt = st.text_input("Ask FamilySync AI", placeholder="Ask or tell the assistant...", label_visibility="collapsed")
                ask_ai = st.form_submit_button("Ask")
            if ask_ai and prompt.strip():
                thread = st.session_state.chat_threads.setdefault("FamilySync AI", [])
                now = datetime.now().strftime("%I:%M %p")
                thread.append({"sender": user_name, "text": prompt.strip(), "time": now})
                thread.append({"sender": "FamilySync", "text": _family_ai_reply(prompt.strip(), thread[:-1]), "time": now})
                st.rerun()


    if st.session_state.get("result"):
        st.markdown("### Decision Log")
        for entry in st.session_state.decision_log:
            st.write(f"- {entry}")


def render_page_title(title: str, subtitle: str = ""):
    header = st.columns([5.2, 3.1], gap="small", vertical_alignment="center")
    with header[0]:
        st.markdown(
            f'<div class="page-heading"><div class="page-title">{escape(title)}</div><p>{escape(subtitle)}</p></div>',
            unsafe_allow_html=True,
        )
    with header[1]:
        render_topbar()

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
    render_page_title("Family Calendar", "Weekly view · colour-coded by category")
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
        if st.button("+ Add Event", key="calendar_add_event", width="stretch"):
            st.session_state.page = "add_event"
            st.rerun()

    calendar_cols = st.columns([3.6, 1.15], gap="small")
    with calendar_cols[0]:
        with st.container(border=True):
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
        st.caption(f"{len(day_entries)} item{'s' if len(day_entries) != 1 else ''} planned")
        if day_entries:
            for entry in day_entries:
                category = "".join(c for c in entry["category"].lower() if c.isalnum() or c == "-")
                st.markdown(f"<div class='calendar-event category-{category}'><strong>{escape(entry['title'])}</strong><small>{entry['start'].strftime('%I:%M %p')} | {escape(entry['owner'])}</small></div>", unsafe_allow_html=True)
        else:
            st.caption("No events or tasks on this date yet.")
        if st.button("+ Add Event", key="calendar_selected_add", type="primary", width="stretch"):
            st.session_state.page = "add_event"
            st.rerun()
        member_rows = "".join(
            f"<div class='member-row'><span class='profile-initial'>{escape(member.name[:1].upper())}</span><strong>{escape(member.name)}</strong><span style='margin-left:auto;color:#10a981;font-size:.66rem'>online</span></div>"
            for member in st.session_state.members
        )
        st.markdown(f"<div class='calendar-side-card'><h4>Family</h4>{member_rows}</div>", unsafe_allow_html=True)


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


def _configured_secret(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        value = st.secrets.get(name)
    except Exception:
        value = None
    if value:
        return str(value)

    secrets_path = Path(__file__).resolve().parent / "API.streamlit" / "secrets.toml"
    try:
        with secrets_path.open("rb") as secrets_file:
            return tomllib.load(secrets_file).get(name)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _family_ai_reply(message: str, history: list[dict[str, str]]) -> str:
    family_context = {
        "today": date.today().isoformat(),
        "current_user": st.session_state.payload.get("demo_user", "Abhi"),
        "family_members": [
            {"name": member.name, "role": member.role}
            for member in st.session_state.members
        ],
        "events": st.session_state.events,
        "tasks": st.session_state.tasks,
    }
    recent_history = [
        {
            "role": "assistant" if item["sender"] == "FamilySync" else "user",
            "content": item["text"],
        }
        for item in history[-10:]
    ]
    service = LLMService(
        api_key=_configured_secret("OPENAI_API_KEY"),
        gemini_api_key=_configured_secret("GEMINI_API_KEY"),
    )
    try:
        return service.chat_response(
            message,
            json.dumps(family_context, ensure_ascii=True),
            recent_history,
        )
    except ValueError:
        return "FamilySync AI needs an API key. Configure GEMINI_API_KEY or OPENAI_API_KEY, then try again."
    except Exception as exc:
        status_code = getattr(exc, "status_code", None)
        if status_code in (401, 403):
            return "The AI provider denied access. Check that the Gemini API key is valid and its project has Gemini API access enabled."
        if status_code == 429:
            return "The AI provider rate limit or quota was reached. Check the project's Gemini API quota and try again."
        if status_code == 404:
            return "The configured AI model was not found. Check GEMINI_MODEL or OPENAI_MODEL in your app settings."
        return "I couldn't reach the AI service just now. Please check the API key and connection, then try again."


def render_chat():
    render_page_title("Family Chat", f"{len(st.session_state.members)} members | shared schedule")
    st.markdown(
        """
        <style>
        .chat-shell-title { color:#17233a; font-size:0.95rem; font-weight:800; margin-bottom:0.55rem; }
        .chat-contact-status { color:#71809d; font-size:0.72rem; }
        .chat-message-row { display:flex; margin:0.65rem 0; }
        .chat-message-row.mine { justify-content:flex-end; }
        .chat-bubble { max-width:82%; border-radius:12px; padding:0.6rem 0.75rem; background:#f4f6fb; color:#17233a; font-size:0.78rem; line-height:1.45; overflow-wrap:anywhere; }
        .chat-message-row.mine .chat-bubble { background:linear-gradient(120deg,#625cf4,#a34ce8); color:white; }
        .chat-message-sender { display:block; font-size:0.66rem; font-weight:800; color:#71809d; margin-bottom:0.2rem; }
        .chat-message-row.mine .chat-message-sender { color:#eeeaff; }
        .chat-detail-row { margin:0.35rem 0; padding:0.55rem 0.65rem; border-radius:9px; background:#f5f6fc; color:#17233a; font-size:0.76rem; }
        .chat-family-row { display:flex; gap:0.4rem; align-items:center; padding:0.28rem 0; color:#17233a; font-size:0.72rem; }
        .chat-online { width:7px; height:7px; border-radius:50%; background:#10b981; display:inline-block; }
        .st-key-family_chat_form [data-testid="stFormSubmitButton"] button { min-height:38px; border-radius:9px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state.setdefault("chat_contact", "FamilySync AI")
    st.session_state.setdefault("chat_threads", {})
    contacts = ["Family Chat", "FamilySync AI"] + [member.name for member in st.session_state.members]
    if st.session_state.chat_contact not in contacts:
        st.session_state.chat_contact = "FamilySync AI"
    selected_contact = st.session_state.chat_contact
    chat_cols = st.columns([1.1, 2.75, 1.1], gap="small")

    with chat_cols[0]:
        with st.container(border=True):
            st.markdown("<div class='chat-shell-title'>Messages</div>", unsafe_allow_html=True)
            query = st.text_input("Search family", placeholder="Search family", label_visibility="collapsed", key="chat_search")
            for contact in contacts:
                if query and query.lower() not in contact.lower():
                    continue
                initials = "F" if contact in ("Family Chat", "FamilySync AI") else contact[:1].upper()
                if st.button(f"{initials}    {contact}", key=f"chat_contact_{contact}", type="primary" if contact == selected_contact else "secondary", width="stretch"):
                    st.session_state.chat_contact = contact
                    st.rerun()

    with chat_cols[1]:
        with st.container(border=True):
            messages = st.session_state.chat_threads.setdefault(selected_contact, [])
            st.markdown(
                f"<div class='chat-shell-title'>{escape(selected_contact)} <span class='chat-contact-status'>| schedule-aware</span></div>",
                unsafe_allow_html=True,
            )
            with st.container(height=440):
                if not messages:
                    st.markdown(
                        "<div class='chat-message-row'><div class='chat-bubble'><span class='chat-message-sender'>FamilySync</span>Welcome! Share a family plan or ask about today's schedule.</div></div>",
                        unsafe_allow_html=True,
                    )
                for message in messages:
                    mine = message["sender"] == st.session_state.payload.get("demo_user", "Abhi")
                    row_class = "mine" if mine else ""
                    st.markdown(
                        f"<div class='chat-message-row {row_class}'><div class='chat-bubble'><span class='chat-message-sender'>{escape(message['sender'])} | {escape(message['time'])}</span>{escape(message['text'])}</div></div>",
                        unsafe_allow_html=True,
                    )
            with st.form("family_chat_form", clear_on_submit=True):
                input_cols = st.columns([5, 0.9], vertical_alignment="bottom")
                with input_cols[0]:
                    message_text = st.text_input("Message", placeholder="Write a message...", label_visibility="collapsed", key="family_chat_message")
                with input_cols[1]:
                    sent = st.form_submit_button("Send", type="primary", width="stretch")
            if sent and message_text.strip():
                now = datetime.now().strftime("%I:%M %p")
                messages.append({"sender": st.session_state.payload.get("demo_user", "Abhi"), "text": message_text.strip(), "time": now})
                reply_sender = "FamilySync" if selected_contact == "FamilySync AI" else selected_contact
                reply_text = _family_ai_reply(message_text, messages[:-1]) if selected_contact == "FamilySync AI" else _chat_reply(message_text)
                messages.append({"sender": reply_sender, "text": reply_text, "time": now})
                st.rerun()

    with chat_cols[2]:
        with st.container(border=True):
            st.markdown("<div class='chat-shell-title'>Chat details</div>", unsafe_allow_html=True)
            for detail in (
                f"{len(st.session_state.members)} family members",
                "Shared family schedule",
                f"{len(st.session_state.events)} calendar events",
                f"{len(st.session_state.tasks)} household tasks",
            ):
                st.markdown(f"<div class='chat-detail-row'><strong>{escape(detail)}</strong></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='chat-shell-title'>Family</div>", unsafe_allow_html=True)
            for member in st.session_state.members:
                st.markdown(
                    f"<div class='chat-family-row'><span class='chat-online'></span><strong>{escape(member.name)}</strong><span class='muted'>| {escape(member.role)}</span></div>",
                    unsafe_allow_html=True,
                )

def render_analytics():
    render_page_title("Analytics", "Workload, completion and fairness across the family")
    task_counts = {
        member.name: sum(1 for task in st.session_state.tasks if task.get("owner") == member.name)
        for member in st.session_state.members
    }
    total_tasks = len(st.session_state.tasks)
    completed = sum(1 for task in st.session_state.tasks if task.get("completed", False))
    pending = total_tasks - completed
    entries = _calendar_entries()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    weekly_entries = [entry for entry in entries if week_start <= entry["start"].date() < week_end]
    busiest = max(task_counts.values(), default=0)
    least_busy = min(task_counts.values(), default=0)
    fairness = 100 if not task_counts or busiest == 0 else max(0, round(100 - (busiest - least_busy) * 25))
    completion_rate = round(completed / total_tasks * 100) if total_tasks else 0

    st.markdown(
        """
        <style>
        .analytics-metric { min-height:72px; padding:0.7rem 0.85rem; }
        .analytics-chart-card { min-height:238px; padding:0.85rem 1rem; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 5px 18px rgba(34,48,81,.045); }
        .analytics-bottom-card { min-height:230px; padding:0.85rem 1rem; border:1px solid var(--line); border-radius:14px; background:#fff; box-shadow:0 5px 18px rgba(34,48,81,.045); }
        .donut-layout { display:flex; align-items:center; gap:1rem; margin-top:0.7rem; }
        .donut-ring { position:relative; display:grid; place-items:center; width:94px; height:94px; flex:0 0 94px; border-radius:50%; }
        .donut-ring:before { content:''; position:absolute; width:66px; height:66px; border-radius:50%; background:#fff; }
        .donut-ring span { position:relative; z-index:1; color:#17233a; font-size:1rem; font-weight:800; }
        .donut-legend { color:#334155; font-size:.76rem; line-height:2; }
        .legend-dot { display:inline-block; width:8px; height:8px; margin-right:.35rem; border-radius:50%; }
        .week-bars { display:flex; align-items:flex-end; justify-content:space-between; gap:.65rem; height:150px; margin-top:.6rem; }
        .week-bar { display:flex; flex:1; height:100%; flex-direction:column; align-items:center; justify-content:flex-end; gap:.35rem; color:#71809d; font-size:.65rem; }
        .week-bar i { display:block; width:100%; max-width:44px; min-height:7px; border-radius:6px 6px 3px 3px; background:linear-gradient(180deg,#625cf4,#a34ce8); }
        .balance-alert { display:flex; align-items:center; justify-content:space-between; gap:.6rem; margin-top:.75rem; padding:.55rem .65rem; border-radius:9px; background:#fff1d8; color:#17233a; font-size:.74rem; font-weight:700; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4, gap="small")
    metrics = (
        ("Total tasks", total_tasks, "#17233a"),
        ("Completion rate", f"{completion_rate}%", "#10b981"),
        ("Events this week", len(weekly_entries), "#17233a"),
        ("Fairness score", f"{fairness}/100", "#f59e0b"),
    )
    for column, (label, value, color) in zip(metric_cols, metrics):
        with column:
            st.markdown(f"<div class='ui-card analytics-metric'><div class='metric-label'>{label}</div><div class='metric-value' style='color:{color}'>{value}</div></div>", unsafe_allow_html=True)

    chart_cols = st.columns([1.2, 1], gap="small")
    with chart_cols[0]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Workload per member</div>", unsafe_allow_html=True)
            max_count = max(task_counts.values(), default=1) or 1
            colors = ("#625cf4", "#a34ce8", "#f36b72", "#10b981", "#f59e0b")
            for index, member in enumerate(st.session_state.members):
                count = task_counts[member.name]
                width = round(count / max_count * 100)
                st.markdown(f"<div class='workload-row'><strong>{escape(member.name)}</strong><div class='workload-track'><i style='width:{width}%;background:{colors[index % len(colors)]}'></i></div><small>{count} tasks</small></div>", unsafe_allow_html=True)
            if len(task_counts) > 1 and busiest - least_busy >= 2:
                st.markdown(f"<div class='balance-alert'><span>Workload is uneven: {escape(max(task_counts, key=task_counts.get))} has {busiest} tasks; {escape(min(task_counts, key=task_counts.get))} has {least_busy}.</span></div>", unsafe_allow_html=True)
                if st.button("Ask AI to rebalance", key="analytics_rebalance", type="primary"):
                    st.session_state.chat_contact = "FamilySync AI"
                    st.session_state.family_chat_message = "Can you suggest a fair way to rebalance the household tasks?"
                    st.session_state.page = "chat"
                    st.rerun()

    with chart_cols[1]:
        st.markdown(f"<div class='analytics-chart-card'><div class='ui-card-title'>Task status</div><div class='donut-layout'><div class='donut-ring' style='background:conic-gradient(#10b981 0 {completion_rate}%, #f59e0b {completion_rate}% 100%)'><span>{completion_rate}%</span></div><div class='donut-legend'><span class='legend-dot' style='background:#10b981'></span>Done &middot; {completed}<br><span class='legend-dot' style='background:#f59e0b'></span>Pending &middot; {pending}</div></div></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Events this week</div>", unsafe_allow_html=True)
            event_counts = [
                sum(1 for entry in weekly_entries if entry["start"].date() == week_start + timedelta(days=offset))
                for offset in range(7)
            ]
            max_events = max(event_counts, default=1) or 1
            bar_html = "".join(
                f"<div class='week-bar'><i style='height:{max(8, round(value / max_events * 100))}%'></i><span>{(week_start + timedelta(days=index)).strftime('%a')[0]}</span></div>"
                for index, value in enumerate(event_counts)
            )
            st.markdown(f"<div class='week-bars' role='img' aria-label='Events by weekday'>{bar_html}</div>", unsafe_allow_html=True)

def render_settings():
    render_page_title("Settings", "Personalise FamilySync for you and your family")
    columns = st.columns([1, 1, 1], gap="small")
    user_name = st.session_state.payload.get("demo_user", "Abhi")
    current_member = next((member for member in st.session_state.members if member.name == user_name), None)
    role_options = ["student", "family manager", "family organizer", "member"]

    with columns[0]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Profile</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='profile-initial' style='width:48px;height:48px;font-size:1rem;margin:.2rem 0 .65rem'>{escape(user_name[:1].upper())}</div>", unsafe_allow_html=True)
            st.text_input("Name", value=user_name, key="settings_profile_name")
            st.text_input("Email", value=f"{user_name.lower().replace(' ', '.')}@familysync.app", disabled=True)
            current_role = current_member.role.lower() if current_member else "member"
            role_index = role_options.index(current_role) if current_role in role_options else role_options.index("member")
            role = st.selectbox("Role", role_options, index=role_index, key="settings_profile_role")
            if st.button("Save changes", key="save_profile", type="primary"):
                st.session_state.payload["demo_user"] = st.session_state.settings_profile_name.strip() or user_name
                if current_member:
                    current_member.role = role
                save_state_to_disk()
                st.success("Profile saved.")
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Appearance</div>", unsafe_allow_html=True)
            st.caption("Theme")
            theme = st.radio(
                "Theme",
                ["Light", "Dark", "System"],
                index=1 if st.session_state.get("theme_mode") == "dark" else 0,
                horizontal=True,
                label_visibility="collapsed",
                key="settings_theme_choice",
            )
            st.session_state.theme_mode = "dark" if theme == "Dark" else "light"
            st.caption("Your preference applies across every page.")

    with columns[1]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Notifications</div>", unsafe_allow_html=True)
            for label, description, key, default in [
                ("Event reminders", "30 minutes before each event", "setting_event_reminders", True),
                ("Task due alerts", "When a chore is almost due", "setting_task_alerts", True),
                ("Conflict warnings", "Instantly when schedules clash", "setting_conflict_warnings", True),
                ("Daily summary", "Morning brief at 7:00 AM", "setting_daily_summary", False),
                ("Festival highlights", "Show today's special day", "setting_festival_highlights", True),
            ]:
                st.toggle(label, value=default, key=key)
                st.caption(description)
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>AI assistant</div>", unsafe_allow_html=True)
            for label, description, key, default in [
                ("Auto-resolve conflicts", "Suggest a fix automatically", "setting_auto_resolve", True),
                ("Smart task assignment", "Balance chores by workload", "setting_smart_assignment", True),
                ("Weather-aware tips", "Adjust plans for the forecast", "setting_weather_tips", False),
            ]:
                st.toggle(label, value=default, key=key)
                st.caption(description)

    with columns[2]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Family members</div>", unsafe_allow_html=True)
            for member in st.session_state.members:
                badge = "Admin" if "manager" in member.role.lower() or "organizer" in member.role.lower() else "Member"
                st.markdown(
                    f"<div class='member-row'><span class='profile-initial'>{escape(member.name[:1].upper())}</span><span><strong>{escape(member.name)}</strong><br><small>{escape(member.role.title())}</small></span><span class='role-badge'>{badge}</span></div>",
                    unsafe_allow_html=True,
                )
            with st.expander("+ Invite member"):
                with st.form("invite_family_member"):
                    invite_name = st.text_input("Name")
                    invite_role = st.selectbox("Role", role_options)
                    invited = st.form_submit_button("Add member", type="primary")
                if invited and invite_name.strip():
                    if any(member.name.lower() == invite_name.strip().lower() for member in st.session_state.members):
                        st.warning("That family member is already listed.")
                    else:
                        st.session_state.members.append(FamilyMember(name=invite_name.strip(), role=invite_role))
                        save_state_to_disk()
                        st.success("Family member added.")
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Data &amp; privacy</div>", unsafe_allow_html=True)
            export_payload = {
                "family_members": [member.model_dump() for member in st.session_state.members],
                "events": st.session_state.events,
                "tasks": st.session_state.tasks,
            }
            st.download_button(
                "Export data",
                data=json.dumps(export_payload, indent=2),
                file_name="familysync-data.json",
                mime="application/json",
                width="stretch",
            )
            st.caption("Your family schedule is stored in the local project data files.")

def render_about():
    render_page_title("About FamilySync", "What it is and how it works")
    st.markdown(
        """
        <div class="about-hero"><h2>Coordinate your family, effortlessly.</h2>
        <p>FamilySync Agent brings schedules, shared responsibilities, and thoughtful task assignment together in one clear workspace.</p></div>
        """,
        unsafe_allow_html=True,
    )
    feature_cols = st.columns(4, gap="small")
    features = [
        ("◉", "Smart scheduling", "Plans checked against family availability."),
        ("ϟ", "Conflict detection", "Spots overlapping events before saving."),
        ("⚖", "Fair task split", "See how chores are distributed."),
        ("☏", "Schedule-aware chat", "Ask about plans in everyday language."),
    ]
    for column, (icon, title, description) in zip(feature_cols, features):
        with column:
            st.markdown(
                f"<div class='ui-card feature-card'><span>{icon}</span><strong>{title}</strong><small>{description}</small></div>",
                unsafe_allow_html=True,
            )
    about_cols = st.columns([1, 1], gap="small")
    with about_cols[0]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>How it works</div>", unsafe_allow_html=True)
            for number, title, description in [
                ("1", "Add an event or task", "By form or in the family chat"),
                ("2", "Check the schedule", "The engine validates family commitments"),
                ("3", "Make a clear plan", "Review conflicts and assignments"),
            ]:
                st.markdown(f"<div class='step-row'><strong>{number} · {title}</strong><small>{description}</small></div>", unsafe_allow_html=True)
    with about_cols[1]:
        with st.container(border=True):
            st.markdown("<div class='ui-card-title'>Built with</div>", unsafe_allow_html=True)
            st.markdown("Python　 Streamlit　 Scheduling engine　 Gemini/OpenAI API")
            st.markdown("**Team**\n\nProject by Abhi · FamilySync Agent")


def render_theme_styles():
    if st.session_state.get("theme_mode") == "dark":
        theme_styles = """
        <style>
        .stApp {
            background: radial-gradient(ellipse at top left, #25204a 0, #15192d 42%, #101522 100%) !important;
            color: #e8edf8 !important;
        }
        [data-testid="stAppViewContainer"], [data-testid="stMain"] {
            background: transparent !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p,
        .stApp label, .stApp [data-testid="stMarkdownContainer"],
        .stApp [data-testid="stCaptionContainer"] {
            color: #e8edf8 !important;
        }
        .home-shell, .nav-rail, .section-shell, .settings-shell,
        .glass-card, .weather-tile, .task-row, .calendar-side-card,
        .calendar-month-cell, .chat-panel {
            background: linear-gradient(145deg, #202a40, #1a2235) !important;
            border-color: #35415d !important;
            color: #e8edf8 !important;
            box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2) !important;
        }
        .nav-rail { background: linear-gradient(180deg, #242c45, #1b2338) !important; }
        .title-text, .section-title, .glass-card strong, .task-row strong,
        .calendar-toolbar-title, .calendar-day-header,
        .calendar-day-header strong, .calendar-side-card h4,
        .chat-shell-title, .chat-contact-name {
            color: #f4f1ff !important;
        }
        .glass-card [style*="color:"] { color: #dbe5f7 !important; }
        .meta-text {
            background: rgba(200, 214, 255, 0.12) !important;
            border: 1px solid rgba(170, 190, 255, 0.55) !important;
            color: #ffffff !important;
            box-shadow: inset 0 0 0 1px rgba(255,255,255,0.05) !important;
        }
        .task-row small, .festival-message, .calendar-day-header small,
        .calendar-month-item, .calendar-event small, .chat-contact-status,
        .chat-message-sender, .chat-detail-row {
            color: #d3defa !important;
        }
        .greeting-badge {
            background: linear-gradient(120deg, #463b75, #344d78) !important;
            color: #e8ddff !important;
        }
        .hero-avatar, .nav-logo, .page-logo {
            background: linear-gradient(135deg, #6c82ff, #bd78e8) !important;
            color: #fff !important;
        }
        .status-pending { background: #594522 !important; color: #ffe0a3 !important; }
        .status-done { background: #174a3d !important; color: #a9f1d2 !important; }
        .festival-card {
            background: linear-gradient(130deg, #3a3044, #34304d 55%, #283853) !important;
            border-color: #5a4c70 !important;
        }
        .festival-art { background: linear-gradient(135deg, #755638, #74465f 58%, #465781) !important; }
        .festival-label { color: #f5cb80 !important; }
        .festival-name { color: #fff0d4 !important; }
        .calendar-day-header { border-color: #3b4861 !important; }
        .calendar-day-header.is-selected { color: #a9c6ff !important; border-color: #8b9eff !important; }
        .calendar-event { background: #263957 !important; border-color: #78a9ff !important; color: #edf4ff !important; }
        .calendar-event.category-medical { background: #482f3a !important; border-color: #f28b83 !important; }
        .calendar-event.category-school { background: #393351 !important; border-color: #b5a0ff !important; }
        .calendar-event.category-family, .calendar-event.category-household { background: #24443e !important; border-color: #76d5a9 !important; }
        .calendar-event.category-errand { background: #4b402b !important; border-color: #f3c56b !important; }
        .calendar-event small { color: #d0d9eb !important; }
        .calendar-month-cell.today { border-color: #8b9eff !important; }
        .chat-bubble { background: #2b3549 !important; color: #e8edf8 !important; }
        .chat-message-row.mine .chat-bubble { background: #343764 !important; color: #f0eaff !important; }
        .chat-detail-row { border-color: #35415d !important; }
        .quick-panel .stButton > button, .nav-rail .stButton > button,
        .page-nav .stButton > button, .stApp .stButton > button,
        .stApp [data-testid="stBaseButton-secondary"] {
            background: linear-gradient(135deg, #343d5b, #293753) !important;
            border: 1px solid #4b5a7b !important;
            color: #f1f4ff !important;
        }
        .stApp .stButton > button:hover { border-color: #a99aff !important; }
        .stApp input, .stApp textarea, .stApp [data-baseweb="select"] > div {
            background-color: #202a40 !important;
            color: #f1f4ff !important;
            border-color: #4b5a7b !important;
        }
        .stApp input::placeholder, .stApp textarea::placeholder { color: #aab6ce !important; }
        .stApp [data-testid="stRadio"] label { color: #e8edf8 !important; }
        .splash-app {
            background: radial-gradient(ellipse at top left, #39305e, #141a2d 72%) !important;
        }
        .splash-card {
            background: rgba(31, 39, 62, 0.82) !important;
            border-color: #52517d !important;
        }
        .splash-title { color: #f4f1ff !important; }
        .splash-name, .splash-brand { color: #c7d4f2 !important; }
        </style>
        """
    else:
        theme_styles = """
        <style>
        .stApp {
            background: radial-gradient(ellipse at top left, #f5efff 0, #f6f8ff 42%, #f1f8ff 100%) !important;
        }
        .glass-card {
            border-top: 3px solid #a69aff !important;
            box-shadow: 0 16px 36px rgba(92, 103, 171, 0.14) !important;
        }
        .weather-tile { border-top-color: #69bde8 !important; }
        .task-row { border-left: 3px solid #8e83ef !important; }
        .quick-panel .stButton > button, .stApp .stButton > button {
            background: linear-gradient(120deg, #f1edff, #eaf5ff) !important;
            border-color: #d7d5fa !important;
            color: #344675 !important;
            border-radius: 14px !important;
            font-weight: 700 !important;
            transition: transform 0.18s ease, box-shadow 0.18s ease !important;
        }
        .stApp .stButton > button:hover {
            transform: translateY(-1px);
            border-color: #9c91ee !important;
            box-shadow: 0 8px 20px rgba(104, 98, 190, 0.16) !important;
        }
        .splash-app {
            background: radial-gradient(ellipse at top left, #e9e5ff, #eaf5ff 72%) !important;
        }
        </style>
        """
    st.markdown(theme_styles, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="FamilySync Agent", layout="wide")
    init_state()

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
        render_theme_styles()
        return

    render_app_styles()
    app_columns = st.columns([1.05, 5.9], gap="small")
    with app_columns[0]:
        render_app_sidebar()
    with app_columns[1]:
        page = st.session_state.get("page", "dashboard")
        if page == "dashboard":
            render_dashboard()
        else:
            render_sidebar(page)
    render_theme_styles()


if __name__ == "__main__":
    main()
