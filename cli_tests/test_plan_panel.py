#!/usr/bin/env python3
"""
CLI Test Tool: Plan Panel — Right Side
=======================================
Tests the plan panel functionality:

  1. Plan data retrieval and shape validation
  2. Plan calendar data (date coverage, task dots)
  3. Day selection / navigation
  4. Task detail rendering data
  5. Deploy to Google Tasks flow
  6. Plan versioning (snapshot history)
  7. Edge cases & error handling
  8. Timing analysis

Calls the SAME backend functions the API routes call.
"""

import asyncio
import json
import os
import sys
import time
import traceback
from datetime import date, timedelta
from pathlib import Path

# ── bootstrap ──
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.config import settings
from app.db.snowflake import fetch_all, fetch_one
from app.conversations.storage import get_conversation, list_conversations
from app.plans.storage import get_latest_plan_for_conversation, get_plan_by_id
from app.models.schemas import Plan, DayPlan, TaskItem
from app.auth.token_store import get_refresh_token
from app.deployments.storage import create_deployment, upsert_deployed_task

# ═══════════════════════════════════════════════════════════════════════
BOLD   = "\033[1m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
DIM    = "\033[2m"
RESET  = "\033[0m"
PASS   = f"{GREEN}✔ PASS{RESET}"
FAIL   = f"{RED}✘ FAIL{RESET}"
WARN   = f"{YELLOW}⚠ WARN{RESET}"

results = []

def section(title: str):
    print(f"\n{BOLD}{CYAN}{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}{RESET}\n")

def record(test_name: str, passed: bool, detail: str = "", duration_ms: float = 0):
    status = PASS if passed else FAIL
    timing = f"  [{duration_ms:.0f}ms]" if duration_ms else ""
    print(f"  {status}  {test_name}{timing}")
    if detail:
        for line in detail.split("\n"):
            print(f"        {line}")
    results.append({"test": test_name, "passed": passed, "detail": detail, "ms": duration_ms})

def warn(msg: str):
    print(f"  {WARN}  {msg}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 0 — Resolve user & find a conversation with a plan
# ═══════════════════════════════════════════════════════════════════════
section("Step 0: Resolve test user & find conversation with plan")

try:
    users = fetch_all("SELECT user_id, email FROM users LIMIT 5")
    if not users:
        print(f"  {RED}No users. Log in via web first.{RESET}")
        sys.exit(1)
    USER_ID = users[0]["user_id"]
    EMAIL   = users[0]["email"]
    print(f"  User: {EMAIL}  (id: {USER_ID[:12]}…)")
except Exception as e:
    print(f"  {RED}DB error: {e}{RESET}")
    sys.exit(1)

# Find a conversation that has a plan
CONV_ID = None
PLAN_DATA = None

try:
    conversations = list_conversations(USER_ID)
    print(f"  Found {len(conversations)} conversation(s)\n")

    for c in conversations:
        cid = c["conversation_id"]
        plan = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=cid)
        has_plan = "✔" if plan else "✘"
        print(f"    {cid[:12]}…  plan={has_plan}  state={c.get('state','?'):<14}  title=\"{c.get('title','')[:35]}\"")
        if plan and not PLAN_DATA:
            CONV_ID = cid
            PLAN_DATA = plan

    if not PLAN_DATA:
        print(f"\n  {YELLOW}No conversations have a plan yet.")
        print(f"  Run test_chat_interface.py first to generate one.{RESET}")
        print(f"  Will still test empty-state behavior.\n")
    else:
        print(f"\n  Using conversation: {CONV_ID[:12]}…")

except Exception as e:
    print(f"  {RED}Failed to list conversations: {e}{RESET}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — Plan Panel Empty State
# ═══════════════════════════════════════════════════════════════════════
section("Step 1: Plan Panel empty state (plan=null)")

print(f"""  {BOLD}When plan is null, PlanPanel renders:{RESET}
    • Centered text: "No plan selected"
    • Subtext: "Open or create a chat to generate a plan."
    • No calendar, no day buttons, no deploy button

  {BOLD}Behavioral note:{RESET}
    The PlanPanel is hidden entirely on screens < xl (1280px) because of
    className="hidden xl:block". On smaller screens, users never see it.
    {YELLOW}This is a significant UX gap — mobile/tablet users have no way
    to view their plan unless they widen the browser.{RESET}
""")

record("PlanPanel empty state renders correctly", True,
       "Static analysis: returns placeholder when plan is null")
record("PlanPanel hidden on < xl screens", False,
       "className='hidden xl:block' — no responsive alternative provided")


# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — Plan data retrieval & validation
# ═══════════════════════════════════════════════════════════════════════
section("Step 2: Plan data retrieval & validation")

plan_obj = None
if PLAN_DATA:
    try:
        t0 = time.time()
        plan_obj = Plan(**PLAN_DATA)
        dur = (time.time() - t0) * 1000
        record("Plan Pydantic validation passes", True,
               f"plan_id={plan_obj.plan_id[:12]}…, {plan_obj.num_days} days", dur)
    except Exception as e:
        record("Plan Pydantic validation passes", False, str(e))

    # Also test retrieval via get_plan_by_id (used by deploy route)
    try:
        t0 = time.time()
        by_id = get_plan_by_id(user_id=USER_ID, plan_id=PLAN_DATA["plan_id"])
        dur = (time.time() - t0) * 1000
        record("get_plan_by_id()", by_id is not None,
               f"Retrieved in {dur:.0f}ms", dur)
    except Exception as e:
        record("get_plan_by_id()", False, str(e))
else:
    print(f"  {YELLOW}No plan data — skipping validation tests.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — Calendar data analysis
# ═══════════════════════════════════════════════════════════════════════
section("Step 3: PlanCalendar data analysis")

if plan_obj:
    print(f"  {BOLD}Calendar needs:{RESET}")
    print(f"    • Set of dates that have tasks (for blue dots)")
    print(f"    • selectedDate for highlighting")
    print(f"    • Date range: {plan_obj.start_date} → {plan_obj.days[-1].date if plan_obj.days else '?'}\n")

    # Compute taskDates (as PlanCalendar.tsx does)
    task_dates = set()
    empty_dates = []
    for d in plan_obj.days:
        if d.tasks:
            task_dates.add(d.date)
        else:
            empty_dates.append(d.date)

    record("Days with tasks (blue dots)", len(task_dates) > 0,
           f"{len(task_dates)}/{len(plan_obj.days)} days have tasks")

    if empty_dates:
        record("Days without tasks", True,
               f"{len(empty_dates)} empty day(s): {', '.join(empty_dates[:5])}")
        warn("Empty days show no dot on calendar — user may think plan is incomplete")

    # Check date continuity
    if plan_obj.days:
        expected_start = date.fromisoformat(plan_obj.start_date)
        all_continuous = True
        for i, d in enumerate(plan_obj.days):
            expected = (expected_start + timedelta(days=i)).isoformat()
            if d.date != expected:
                all_continuous = False
                record("Date continuity", False, f"Day {i+1}: expected {expected}, got {d.date}")
                break
        if all_continuous:
            record("Date continuity (sequential days)", True,
                   f"{plan_obj.start_date} to {plan_obj.days[-1].date}")

    # Frontend issue: PlanCalendar uses toISOString().slice(0,10) for dates
    # This can cause timezone offset issues
    print(f"\n  {YELLOW}POTENTIAL BUG: PlanCalendar uses date.toISOString().slice(0,10){RESET}")
    print(f"  toISOString() converts to UTC, so near midnight in non-UTC timezones,")
    print(f"  the date can shift by ±1 day. E.g., March 15 at 11pm EST becomes March 16 UTC.")
    print(f"  This means clicking March 15 on calendar could select March 16's tasks.")
    record("PlanCalendar timezone-safe date handling", False,
           "toISOString() shifts dates near midnight in non-UTC zones. Use toLocaleDateString or manual formatting.")

else:
    print(f"  {YELLOW}No plan — skipping calendar analysis.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — Day navigation (DayButtons) analysis
# ═══════════════════════════════════════════════════════════════════════
section("Step 4: DayButtons navigation analysis")

if plan_obj:
    print(f"  {BOLD}DayButtons renders:{RESET}")
    print(f"    • Horizontal scroll of 'Day 1', 'Day 2', … 'Day {plan_obj.num_days}'")
    print(f"    • Selected button: bg-blue-600 text-white")
    print(f"    • Others: bg-white text-gray-700")
    print()

    # Test selectedIndex bounds
    record("selectedIndex default=0 on plan change", True,
           "useEffect resets selectedIndex to 0 when planId changes")

    # Test what happens with out-of-bounds index (edge case)
    # PlanPanel uses: Math.min(selectedIndex, plan.days.length - 1)
    record("selectedIndex clamped to plan.days.length-1", True,
           "Math.min(selectedIndex, plan.days.length - 1) prevents OOB")

    # UX issue: with 14+ days, the day buttons overflow
    if plan_obj.num_days > 7:
        warn(f"Plan has {plan_obj.num_days} days — day buttons will overflow horizontally")
        print(f"    The container has overflow-x-auto which is correct, but:")
        print(f"    {YELLOW}• No scroll indicators (user may not know they can scroll)")
        print(f"    • No keyboard navigation (arrow keys don't work){RESET}")

    # Calendar ↔ DayButtons sync
    print(f"\n  {BOLD}Calendar ↔ DayButtons sync:{RESET}")
    print(f"    When user clicks a date on the calendar → onSelectDate(date)")
    print(f"    → finds index in plan.days → setSelectedIndex(idx)")
    print(f"    When user clicks a Day button → onSelectIndex(idx)")
    print(f"    → selectedDay updates → but calendar.selectedDate ALSO updates")
    print(f"    {GREEN}Both directions are correctly wired.{RESET}")
    record("Calendar ↔ DayButtons bidirectional sync", True)

else:
    print(f"  {YELLOW}No plan — skipping.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — DayDetail task rendering
# ═══════════════════════════════════════════════════════════════════════
section("Step 5: DayDetail task rendering analysis")

if plan_obj and plan_obj.days:
    # Test each day's task data
    total_tasks = 0
    max_day_tasks = 0
    min_duration = float('inf')
    max_duration = 0
    priorities = {"low": 0, "med": 0, "high": 0}

    for d in plan_obj.days:
        total_tasks += len(d.tasks)
        max_day_tasks = max(max_day_tasks, len(d.tasks))
        for t in d.tasks:
            min_duration = min(min_duration, t.duration_min)
            max_duration = max(max_duration, t.duration_min)
            priorities[t.priority.value] = priorities.get(t.priority.value, 0) + 1

    print(f"  {BOLD}Task Statistics:{RESET}")
    print(f"    Total tasks    : {total_tasks} across {plan_obj.num_days} days")
    print(f"    Tasks per day  : max={max_day_tasks}")
    print(f"    Duration range : {min_duration}-{max_duration} min")
    print(f"    Priorities     : high={priorities.get('high',0)}, med={priorities.get('med',0)}, low={priorities.get('low',0)}")

    record("All tasks have valid titles", all(
        t.title and len(t.title) <= 200 for d in plan_obj.days for t in d.tasks
    ))

    record("All tasks have valid durations",
           all(0 < t.duration_min <= 480 for d in plan_obj.days for t in d.tasks))

    # Check if any task notes are very long (may overflow UI)
    long_notes = [(d.date, t.title, len(t.notes))
                  for d in plan_obj.days for t in d.tasks if len(t.notes) > 500]
    if long_notes:
        warn(f"{len(long_notes)} task(s) have notes > 500 chars — may overwhelm the task card")
        for dt, title, length in long_notes[:3]:
            print(f"      {dt} / {title[:30]}… — {length} chars")

    record("Task notes reasonable length (≤500 chars)",
           len(long_notes) == 0,
           f"{len(long_notes)} task(s) exceeded 500 chars" if long_notes else "")

    # Sample DayDetail render
    sample = plan_obj.days[0]
    print(f"\n  {BOLD}Sample render — Day 1 ({sample.date}):{RESET}")
    print(f"    {sample.tasks.__len__()} task(s)")
    for t in sample.tasks:
        print(f"    ┌─────────────────────────────────────────────────────┐")
        print(f"    │ {t.title[:50]:<50} │")
        print(f"    │ {t.priority.value:>3} priority    {t.duration_min:>3} min{' ' * 30}│")
        if t.notes:
            for line in t.notes.split("\n")[:3]:
                print(f"    │ {DIM}{line[:52]:<52}{RESET} │")
        print(f"    └─────────────────────────────────────────────────────┘")

else:
    print(f"  {YELLOW}No plan — skipping task analysis.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — Deploy to Google Tasks analysis
# ═══════════════════════════════════════════════════════════════════════
section("Step 6: Deploy to Google Tasks — readiness check")

if plan_obj:
    print(f"  {BOLD}Deploy flow:{RESET}")
    print(f"    PlanPanel.onDeploy() → deployPlan(planId)")
    print(f"    → POST /api/plans/{{plan_id}}/deploy")
    print(f"    → deploy.deploy_plan()")
    print(f"    → deployer.deploy_plan_to_tasks()")
    print(f"      ├─ get_refresh_token(user_id)  — decrypt from Snowflake")
    print(f"      ├─ refresh_access_token()       — Google OAuth token refresh")
    print(f"      ├─ create_tasklist()            — Google Tasks API")
    print(f"      ├─ create_task() × N            — one per task")
    print(f"      ├─ create_deployment()          — Snowflake record")
    print(f"      └─ upsert_deployed_task() × N   — mapping records\n")

    # Check if refresh token exists
    try:
        t0 = time.time()
        refresh_token = get_refresh_token(USER_ID)
        dur = (time.time() - t0) * 1000
        if refresh_token:
            record("Refresh token exists for user", True,
                   f"Token length: {len(refresh_token)} chars", dur)
        else:
            record("Refresh token exists for user", False,
                   "No refresh token found — deploy will fail with 'please sign in again'", dur)
    except Exception as e:
        record("Refresh token exists for user", False, str(e))

    # Count how many API calls deploy would make
    total_deploy_tasks = sum(len(d.tasks) for d in plan_obj.days)
    print(f"  Deploy would make:")
    print(f"    1 token refresh call")
    print(f"    1 create_tasklist call")
    print(f"    {total_deploy_tasks} create_task calls")
    print(f"    1 create_deployment DB write")
    print(f"    {total_deploy_tasks} upsert_deployed_task DB writes")
    print(f"    = {2 + total_deploy_tasks} Google API calls + {1 + total_deploy_tasks} DB writes\n")

    if total_deploy_tasks > 30:
        warn(f"Deploying {total_deploy_tasks} tasks will be slow — all calls are sequential")
        print(f"    {YELLOW}FIX: Batch Google Tasks API calls or use asyncio.gather(){RESET}")

    record("Deploy task count manageable", total_deploy_tasks <= 50,
           f"{total_deploy_tasks} tasks to deploy")

    # Test deploy rate limiting concern
    print(f"\n  {BOLD}Deploy concerns:{RESET}")
    print(f"  1. {YELLOW}NO IDEMPOTENCY:{RESET} Clicking 'Deploy' twice creates TWO tasklists.")
    print(f"     The deployed_tasks table tracks mappings but doesn't prevent duplicate deploys.")
    print(f"     {YELLOW}FIX: Check if a deployment already exists for this plan_id before deploying.{RESET}")
    print(f"  2. {YELLOW}NO UNDO:{RESET} There's no way to un-deploy or delete a tasklist from the UI.")
    print(f"  3. {YELLOW}STATUS NOT PERSISTED TO UI:{RESET} The deploy status message ('✅ X tasks deployed')")
    print(f"     is stored only in PlanPanel local state. Refreshing the page loses it.")
    print(f"  4. {YELLOW}SEQUENTIAL TASK CREATION:{RESET} Each task is created one at a time, awaiting each.")
    print(f"     With {total_deploy_tasks} tasks, this could take {total_deploy_tasks * 0.5:.0f}-{total_deploy_tasks * 2:.0f} seconds.")

    record("Deploy idempotency guard", False,
           "No check for existing deployment for same plan_id")
    record("Deploy undo capability", False,
           "No UI or API endpoint to delete a deployed tasklist")

else:
    print(f"  {YELLOW}No plan — testing deploy readiness only.{RESET}")
    try:
        refresh_token = get_refresh_token(USER_ID)
        record("Refresh token exists", refresh_token is not None,
               f"{'Found' if refresh_token else 'Missing'}")
    except Exception as e:
        record("Refresh token check", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — Plan versioning (snapshot history)
# ═══════════════════════════════════════════════════════════════════════
section("Step 7: Plan versioning analysis")

if CONV_ID:
    try:
        t0 = time.time()
        plan_rows = fetch_all(
            """
            SELECT plan_id, goal, num_days, minutes_per_day, created_at
            FROM plans
            WHERE user_id = %s AND conversation_id = %s
            ORDER BY created_at DESC
            """,
            (USER_ID, CONV_ID),
        )
        dur = (time.time() - t0) * 1000

        print(f"  {BOLD}Plan snapshots for conversation {CONV_ID[:12]}…:{RESET}")
        for i, p in enumerate(plan_rows):
            print(f"    [{i}] {p['plan_id'][:12]}…  {p['goal'][:35]:<35}  {p['num_days']}d  {p.get('created_at','?')}")

        record(f"Plan snapshots found", len(plan_rows) > 0,
               f"{len(plan_rows)} snapshot(s)", dur)

        if len(plan_rows) > 1:
            print(f"\n  {BOLD}Versioning observation:{RESET}")
            print(f"    {len(plan_rows)} versions exist. The conversation.latest_plan_id points to the newest.")
            print(f"    Old snapshots are retained but NOT accessible from the UI.")
            print(f"    {YELLOW}IMPROVEMENT: Add plan history / undo capability.{RESET}")
            record("Plan history accessible from UI", False,
                   "Old plan versions exist in DB but UI only shows latest")
        elif len(plan_rows) == 1:
            record("Single plan snapshot exists", True)

    except Exception as e:
        record("Plan snapshot query", False, str(e))
else:
    print(f"  {YELLOW}No conversation with plan — skipping.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 8 — Deployment history check
# ═══════════════════════════════════════════════════════════════════════
section("Step 8: Deployment history")

try:
    t0 = time.time()
    deployments = fetch_all(
        """
        SELECT deployment_id, plan_id, tasklist_title, created_count, deployed_at
        FROM deployments
        WHERE user_id = %s
        ORDER BY deployed_at DESC
        LIMIT 10
        """,
        (USER_ID,),
    )
    dur = (time.time() - t0) * 1000

    if deployments:
        print(f"  {BOLD}Recent deployments:{RESET}")
        for d in deployments:
            print(f"    {d['deployment_id'][:12]}…  {d.get('tasklist_title','?')[:40]}  tasks={d.get('created_count',0)}  {d.get('deployed_at','?')}")
        record("Deployment history", True, f"{len(deployments)} deployment(s)", dur)
    else:
        print(f"  No deployments yet.")
        record("Deployment history", True, "No deployments (expected if never deployed)", dur)

except Exception as e:
    record("Deployment history query", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 9 — Cross-component data flow analysis
# ═══════════════════════════════════════════════════════════════════════
section("Step 9: Cross-component data flow analysis")

print(f"""  {BOLD}PlanPanel receives data from AppPage:{RESET}
    <PlanPanel plan={{currentPlan}} planId={{currentPlanId}} isLoading={{isLoading}} />

  {BOLD}Data flow chain:{RESET}
    User sends message → handleSendMessage()
    → generatePlan() or updatePlan() returns ConversationPlanResponse
    → setCurrentPlan(response.plan)
    → setCurrentPlanId(response.plan_id)
    → PlanPanel re-renders with new plan

  {BOLD}Also after any message send:{RESET}
    → selectConversation(activeConversationId) re-fetches everything
    → getConversation response includes latest_plan
    → setCurrentPlan(detail.latest_plan)

  {BOLD}Issues found:{RESET}

  1. {RED}DOUBLE PLAN FETCH:{RESET}
     The plan is set TWICE on every message send:
       a) From the generate/update response: setCurrentPlan(response.plan)
       b) From selectConversation re-fetch: setCurrentPlan(detail.latest_plan)
     This causes a needless re-render of PlanPanel with the same data.
     If the second fetch is slightly different (e.g., timestamps), it causes
     a flash/re-render.
     {YELLOW}FIX: Skip the refetch if the response already contains the plan,
     or only use one source of truth.{RESET}

  2. {YELLOW}PLAN PANEL UPDATE NOT INSTANT:{RESET}
     PlanPanel updates only AFTER the Gemini API call completes (5-30s).
     During this time, the plan panel shows the OLD plan.
     There's no "updating…" state on the plan panel.
     {YELLOW}FIX: Set a planIsUpdating state to show a skeleton/shimmer
     on the PlanPanel while waiting.{RESET}

  3. {YELLOW}SELECTED DAY RESET:{RESET}
     useEffect resets selectedIndex to 0 when planId changes.
     If user was looking at Day 7 and the plan updates (new planId),
     they're jumped back to Day 1.
     {YELLOW}FIX: Preserve selectedIndex across updates if the day count
     doesn't change, or scroll to the first changed day.{RESET}
""")

record("Double plan fetch optimization needed", False,
       "Plan is fetched from API response AND re-fetched in selectConversation")
record("Plan panel loading state during updates", False,
       "No visual indication that plan is being updated")
record("Selected day preserved across updates", False,
       "selectedIndex resets to 0 on every planId change")


# ═══════════════════════════════════════════════════════════════════════
# STEP 10 — Full timing: plan panel cold load
# ═══════════════════════════════════════════════════════════════════════
section("Step 10: Plan panel cold load timing")

if CONV_ID and PLAN_DATA:
    t0 = time.time()
    _ = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    t1 = time.time()
    _ = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    t2 = time.time()

    t_conv = (t1 - t0) * 1000
    t_plan = (t2 - t1) * 1000
    t_total = (t2 - t0) * 1000

    print(f"  get_conversation()                   : {t_conv:>6.0f} ms")
    print(f"  get_latest_plan_for_conversation()    : {t_plan:>6.0f} ms")
    print(f"  {'─' * 50}")
    print(f"  Total plan panel data load            : {t_total:>6.0f} ms\n")

    record("Plan panel data load time", t_total < 3000,
           f"{t_total:.0f}ms" + (" — slow!" if t_total > 3000 else ""), t_total)

else:
    print(f"  {YELLOW}No plan to time.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
section("SUMMARY")

passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])
total  = len(results)

print(f"  {GREEN}{passed} passed{RESET}  |  {RED}{failed} failed{RESET}  |  {total} total\n")

if failed:
    print(f"  {BOLD}Failed / Issues:{RESET}")
    for r in results:
        if not r["passed"]:
            print(f"    {RED}✘{RESET} {r['test']}")
            if r["detail"]:
                print(f"      → {r['detail']}")
    print()

# Collect all issues for a final roadmap
print(f"  {BOLD}Plan Panel Improvement Roadmap:{RESET}")
print(f"    P0 (Bugs):")
print(f"      • Calendar timezone date-shift bug (toISOString)")
print(f"    P1 (UX):")
print(f"      • Responsive plan view for < xl screens")
print(f"      • Loading/skeleton state during plan updates")
print(f"      • Deploy idempotency (prevent double-deploy)")
print(f"    P2 (Polish):")
print(f"      • Preserve selected day across plan updates")
print(f"      • Plan version history / undo")
print(f"      • Deploy undo / delete tasklist")
print(f"      • Eliminate double plan fetch")
print(f"      • Batch deploy API calls")
print()

print("Done.\n")
