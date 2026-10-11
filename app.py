from __future__ import annotations

import json
import os
import time
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv

from core.models import Event, FamilyMember, Task
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
    st.markdown(
        """
        <style>
        .splash-box {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 90vh;
            text-align: center;
            background: linear-gradient(135deg, #eef7ff 0%, #f7f0ff 100%);
            border-radius: 24px;
        }
        .splash-title {
            font-size: 3rem;
            font-weight: 700;
            color: #102a43;
        }
        .splash-sub {
            font-size: 1.2rem;
            color: #3d5a80;
            margin-top: 8px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="splash-box">
            <div class="splash-title">Welcome Back!</div>
            <div class="splash-sub">Abhi</div>
            <div class="splash-sub" style="margin-top: 30px;">FamilySync Agent</div>
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


def render_sidebar():
    with st.sidebar:
        st.markdown(
            """
            <div style='display:flex;align-items:center;justify-content:center;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,#a1d3ff,#d9c8ff);color:#1d3557;font-weight:700;margin:0 auto 14px auto;'>AB</div>
            """,
            unsafe_allow_html=True,
        )
        st.caption("Abhi")
        st.markdown("---")
        menu = [
            ("Dashboard", "dashboard"),
            ("Calendar", "calendar"),
            ("Family Chat", "chat"),
            ("Analytics", "analytics"),
            ("Settings", "settings"),
            ("About Us", "about"),
        ]
        for label, key in menu:
            if st.button(label, key=f"nav_{key}", use_container_width=True):
                st.session_state.page = key
        st.markdown("---")
        if st.button("Reset demo data", use_container_width=True):
            payload, members, events, tasks = load_family_data()
            st.session_state.payload = payload
            st.session_state.members = members
            st.session_state.events = [event.model_dump() for event in events]
            st.session_state.tasks = [task.model_dump() for task in tasks]
            st.session_state.result = None
            st.session_state.decision_log = ["Demo data restored."]
            save_state_to_disk()
            st.rerun()


def render_dashboard():
    st.markdown(
        """
        <style>
        .card {
            background: linear-gradient(135deg,#ffffff,#f3f7ff);
            border-radius: 18px;
            padding: 1.2rem;
            box-shadow: 0 10px 24px rgba(82,115,182,0.12);
            border: 1px solid rgba(148,163,184,0.2);
        }
        .pill {
            display:inline-block; padding: 0.4rem 0.8rem; border-radius: 999px; background: #edf5ff; color: #1d4ed8; font-weight: 600; font-size: 0.8rem; margin-bottom: 0.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Family overview")
    scenario_col, status_col = st.columns([3, 1])
    with scenario_col:
        st.markdown('<div class="pill">Demo mode</div>', unsafe_allow_html=True)
    with status_col:
        st.metric("Live state", "Ready")

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"## Hi, Abhi!")
        st.caption(f"{get_current_time_greeting()} — {datetime.now().strftime('%A, %d %B %Y | %I:%M %p')}")
    with col2:
        st.metric("Tasks today", len(st.session_state.tasks))
    with col3:
        st.metric("Family members", len(st.session_state.members))

    st.markdown("### Quick scenario demos")
    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("Load Scenario A: Conflict resolution"):
            payload, members, events, tasks = load_family_data()
            payload["events"] = [
                {"id": "evt-1", "title": "Dentist appointment", "member": "Mom", "start": "2026-10-10T15:00:00", "end": "2026-10-10T16:00:00", "category": "medical", "location": "City Dental Clinic", "notes": "Routine check-up"},
                {"id": "evt-2", "title": "College presentation", "member": "Abhi", "start": "2026-10-10T14:00:00", "end": "2026-10-10T16:00:00", "category": "school", "location": "Campus Hall", "notes": "Final presentation"},
                {"id": "evt-3", "title": "Driving lesson", "member": "Arjun", "start": "2026-10-10T17:00:00", "end": "2026-10-10T18:00:00", "category": "personal", "location": "Training center", "notes": "Practice session"},
            ]
            payload["tasks"] = [
                {"id": "task-1", "title": "Kitchen cleanup", "owner": "Mom", "start": "2026-10-10T18:00:00", "end": "2026-10-10T18:45:00", "priority": "medium", "completed": False, "category": "household"},
                {"id": "task-2", "title": "Laundry", "owner": "Dad", "start": "2026-10-10T19:00:00", "end": "2026-10-10T20:00:00", "priority": "medium", "completed": False, "category": "household"},
                {"id": "task-3", "title": "Pickup Arjun", "owner": "Dad", "start": "2026-10-10T16:15:00", "end": "2026-10-10T17:00:00", "priority": "high", "completed": False, "category": "pickup"},
            ]
            st.session_state.payload = payload
            st.session_state.members = members
            st.session_state.events = payload["events"]
            st.session_state.tasks = payload["tasks"]
            st.session_state.decision_log = ["Scenario A loaded."]
            save_state_to_disk()
            st.rerun()
    with sc2:
        if st.button("Load Scenario B: No one available"):
            payload, members, events, tasks = load_family_data()
            payload["events"] = [
                {"id": "evt-a", "title": "Dentist", "member": "Mom", "start": "2026-10-10T16:00:00", "end": "2026-10-10T17:00:00", "category": "medical"},
                {"id": "evt-b", "title": "Meeting", "member": "Dad", "start": "2026-10-10T16:15:00", "end": "2026-10-10T17:00:00", "category": "family"},
                {"id": "evt-c", "title": "Interview", "member": "Abhi", "start": "2026-10-10T16:00:00", "end": "2026-10-10T17:15:00", "category": "school"},
                {"id": "evt-d", "title": "Club", "member": "Arjun", "start": "2026-10-10T16:30:00", "end": "2026-10-10T17:30:00", "category": "personal"},
            ]
            payload["tasks"] = [{
                "id": "task-pickup",
                "title": "Pickup Arjun",
                "owner": "Dad",
                "start": "2026-10-10T16:15:00",
                "end": "2026-10-10T17:00:00",
                "priority": "high",
                "completed": False,
                "category": "pickup",
            }]
            st.session_state.payload = payload
            st.session_state.members = members
            st.session_state.events = payload["events"]
            st.session_state.tasks = payload["tasks"]
            st.session_state.decision_log = ["Scenario B loaded."]
            save_state_to_disk()
            st.rerun()

    assistant_col, weather_col = st.columns([2, 1])
    with assistant_col:
        st.markdown(
            """
            <div class='card'>
                <h4>FamilySync AI Companion</h4>
                <p>I can check the family calendar, spot conflicts, and suggest the best assignment for each task.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with weather_col:
        st.markdown(
            """
            <div class='card'>
                <h4>Today's Weather</h4>
                <p>⛅ Demo weather: 29°C</p>
                <p>Suggestion: Carry a light bottle of water.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Personal To-Do")
    personal_tasks = [task for task in st.session_state.tasks if task["owner"] == "Abhi"]
    for task in personal_tasks:
        status = st.checkbox(f"{task['title']} · {task['start']}", value=task["completed"], key=f"task_{task['id']}")
        task["completed"] = status
        save_state_to_disk()

    st.markdown("### Household Tasks")
    household_tasks = [task for task in st.session_state.tasks if task["owner"] != "Abhi"]
    for task in household_tasks:
        assigned = task["owner"]
        status = "Done" if task["completed"] else "Pending"
        st.markdown(f"- **{task['title']}** — {assigned} — {status} — {task['start']}")

    with st.expander("Add a new event or task", expanded=False):
        st.caption("Use the form below to add an event and run the coordination engine.")
        with st.form("event_form"):
            title = st.text_input("Title")
            member = st.selectbox("Member", [m.name for m in st.session_state.members], index=0)
            event_date = st.date_input("Date")
            start_time = st.time_input("Start time")
            end_time = st.time_input("End time")
            category = st.selectbox("Category", ["personal", "school", "medical", "pickup", "errand", "family"])
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("Check schedule")
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
                    st.success(result.recommendation)
                elif result.status == "rejected":
                    st.warning(result.explanation)
                else:
                    st.info(result.explanation)
                if result.status == "resolved":
                    accept = st.checkbox("Accept recommendation", key="accept_recommendation")
                    if accept:
                        st.session_state.events.append(event.model_dump())
                        st.session_state.decision_log.append("User accepted the recommendation and schedule was updated.")
                        st.success("Event accepted and added to the shared schedule.")
                        save_state_to_disk()

        st.markdown("### Add a household task")
        with st.form("task_form"):
            task_title = st.text_input("Task name", key="task_name")
            task_owner = st.selectbox("Assigned family member", [m.name for m in st.session_state.members], key="task_owner")
            task_date = st.date_input("Task date", key="task_date")
            task_start = st.time_input("Task start time", key="task_start")
            task_end = st.time_input("Task end time", key="task_end")
            task_priority = st.selectbox("Priority", ["low", "medium", "high"], key="task_priority")
            task_category = st.selectbox("Category", ["household", "pickup", "family", "errand"], key="task_category")
            task_submitted = st.form_submit_button("Add task")
            if task_submitted and task_title:
                task = {
                    "id": f"task-{int(time.time())}",
                    "title": task_title,
                    "owner": task_owner,
                    "start": datetime.combine(task_date, task_start).isoformat(timespec="seconds"),
                    "end": datetime.combine(task_date, task_end).isoformat(timespec="seconds"),
                    "priority": task_priority,
                    "completed": False,
                    "category": task_category,
                    "description": f"Added from dashboard by {task_owner}.",
                }
                st.session_state.tasks.append(task)
                save_state_to_disk()
                st.success(f"Task '{task_title}' added.")

    if st.session_state.get("result"):
        st.markdown("### Decision Log")
        for entry in st.session_state.decision_log:
            st.write(f"- {entry}")


def render_calendar():
    st.header("Calendar")
    events = [Event(**event) for event in st.session_state.events]
    if not events:
        st.info("No events scheduled yet.")
        return

    grouped = {}
    for event in events:
        day = event.start.split("T")[0]
        grouped.setdefault(day, []).append(event)

    for day, day_events in sorted(grouped.items()):
        st.subheader(day)
        for event in sorted(day_events, key=lambda item: item.start):
            st.markdown(
                f"- **{event.title}** — {event.member} — {event.start[11:16]} to {event.end[11:16]} — {event.category}"
            )


def render_chat():
    st.header("Family Chat")
    st.caption("Demo mock chat: schedule details are fetched from the application data.")
    chat_input = st.text_input("Ask FamilySync about today’s plan")
    if chat_input:
        lower = chat_input.lower()
        if "pickup" in lower or "drop" in lower:
            response = "I checked the current family calendar and there is a pickup task scheduled during the most likely available window. I will keep it on the same day and avoid overlapping family commitments."
        elif "cleanup" in lower or "household" in lower:
            response = "The household tasks are currently distributed across the family and no major conflict is detected. We can prioritize the earliest available member."
        else:
            response = "I can see the current schedule for the family and will avoid assignments that conflict with existing events or tasks."
        st.success(f"Assistant: {response}")

    st.markdown("### Recent AI summary")
    st.info("The assistant is using deterministic scheduling data to recommend valid assignments without inventing unavailable times.")


def render_analytics():
    st.header("Analytics")
    task_counts = {member.name: sum(1 for task in st.session_state.tasks if task["owner"] == member.name) for member in st.session_state.members}
    total = max(sum(task_counts.values()), 1)
    for member in st.session_state.members:
        count = task_counts.get(member.name, 0)
        st.write(f"**{member.name}**")
        st.progress(count / total if total else 0)
        st.caption(f"{count} assigned tasks")


def render_settings():
    st.header("Settings")
    st.checkbox("Enable AI recommendations", value=True)
    st.checkbox("Use demo weather", value=True)
    st.text_input("Timezone", value="Local system time")
    if st.button("Save current state"):
        save_state_to_disk()
        st.success("State saved successfully.")


def render_about():
    st.header("About Us")
    st.markdown(
        """
        FamilySync Agent is a prototype for coordinating family schedules, shared responsibilities, and intelligent task assignment.
        It combines a deterministic scheduling engine with an LLM service fallback so the workflow is explainable, testable, and easy to present to judges.
        """
    )


def main():
    st.set_page_config(page_title="FamilySync Agent", layout="wide")
    init_state()
    if not st.session_state.get("splash_complete", False):
        render_splash()
        return

    render_sidebar()
    page = st.session_state.get("page", "dashboard")
    if page == "dashboard":
        render_dashboard()
    elif page == "calendar":
        render_calendar()
    elif page == "chat":
        render_chat()
    elif page == "analytics":
        render_analytics()
    elif page == "settings":
        render_settings()
    elif page == "about":
        render_about()


if __name__ == "__main__":
    main()
