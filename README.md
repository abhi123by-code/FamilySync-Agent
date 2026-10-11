# FamilySync Agent

FamilySync Agent is a Python + Streamlit prototype for coordinating family calendars, household tasks, and scheduling decisions. The app uses a deterministic scheduling engine and a structured LLM integration path so teams can test conflict detection, candidate selection, and visible decision logs in a local demo environment.

## Problem addressed

Families often have overlapping obligations, school schedules, errands, pickups, and household tasks. FamilySync Agent helps identify conflicts early, evaluate available family members, and recommend the most suitable assignment for a task without silently overwriting existing commitments.

## Key features

- Personalized dashboard for a demo family profile
- Sidebar navigation for Calendar, Family Chat, Analytics, Settings, and About
- Demo welcome splash experience and time-aware greeting
- Family event/task data loaded from local JSON sample data
- Conflict detection using interval overlap logic
- Eligibility checks and task assignment scoring
- Decision log showing orchestration steps and outcomes
- LLM request parser with a deterministic fallback when no API key is configured
- Local automated tests for overlap detection and resolution logic

## Architecture

- app.py: Streamlit dashboard and UI flow
- orchestrator.py: coordinates request flow across agents
- agents/schedule_manager.py: reads calendar data and validates scheduling constraints
- agents/task_coordinator.py: ranks eligible family members
- agents/communication_agent.py: turns structured results into human-friendly explanations
- core/scheduler.py: overlap logic and scheduling validation
- core/resolver.py: candidate ranking and feasibility checks
- services/llm_service.py: LLM access and local fallback
- tests/: automated scheduling and resolution tests

## Local setup

1. Open a terminal in the project folder.
2. Create and activate a virtual environment:

```powershell
cd F:\Agent
F:\Python312\python.exe -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:

```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

4. Create a local environment file:

```powershell
Copy-Item .env.example .env
```

5. If you have an OpenAI key, update `.env` with a real API value. Otherwise, the app will use the deterministic fallback mode.

## Launch the app

```powershell
cd F:\Agent
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.headless true --server.port 8501
```

Open the browser to:

- http://localhost:8501

## Demo scenarios

The app includes a sample family and event data loaded from `data/sample_family.json`.

- Scenario A: a valid conflict resolution path is recommended when a feasible family member is available.
- Scenario B: no candidate is available and the task stays unresolved instead of being wrongly assigned.

## Running tests

```powershell
cd F:\Agent
.\.venv\Scripts\Activate.ps1
python -m pytest tests -q
```

## API configuration

The app reads the following environment variables:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
WEATHER_API_KEY=
WEATHER_LOCATION=Hyderabad
```

If `OPENAI_API_KEY` is missing or the API request fails, the app falls back to local structured parsing and clearly labels the result as a demo fallback. This preserves local testing without inventing a live LLM response.

## Limitations

- This is a prototype, not a production scheduling system.
- The app uses local demo data instead of real user accounts or external calendars.
- The weather card is demo data unless a real API is configured.
- The family chat is a mock interface for the demo flow.

## Judge demo script

1. Open the app and show the welcome screen.
2. Explain that the demo user is Abhi and the family includes Mom, Dad, and Arjun.
3. Click "Load Scenario A: Conflict resolution" and highlight the conflict between Mom's appointment and the pickup task.
4. Show the AI companion card and explain how the system checks the calendar before choosing a candidate.
5. Open the decision log and explain the sequence: request received, schedule checked, candidate members ranked, final recommendation selected.
6. Click "Load Scenario B: No one available" and explain the unresolved case: the app refuses to assign a task when every family member is busy.
7. Open the calendar and analytics pages to reinforce the schedule-aware workflow and family balancing view.
8. Close by saying the prototype combines deterministic logic with an LLM path and is designed for explainability, not fake intelligence.

## Final presentation narrative

"FamilySync Agent is an AI-powered coordination system for household planning. It helps families manage overlapping schedules, shared responsibilities, and time-sensitive tasks without blindly assigning work to whoever is available. The system validates real schedule conflicts first, then evaluates eligible candidates, and only recommends a change after checking the full family calendar. In our demo, the app shows both a successful resolution scenario and an unsolvable scenario, which proves the system can explain why it accepted or rejected a plan."

## Future improvements

- Real authentication and multi-user profiles
- Persistent JSON or SQLite storage
- Better calendar UX with weekly/monthly views
- Real weather integration via a configured API
- More advanced assignment scoring and travel buffers
- Expanded decision logs and exported reports
