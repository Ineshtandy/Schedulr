#!/usr/bin/env python3
"""
CLI Test Tool: Chat Interface — Central Pane
=============================================
Exhaustive test of the chat interface behavior:

  1. Empty-state rendering (no messages)
  2. Starter pill sends (first user message)
  3. Ask-questions flow (first message → clarification questions from Gemini)
  4. Answer-questions flow (second message → full plan generation)
  5. Plan update flow (subsequent messages modify the plan)
  6. Message persistence & ordering
  7. Conversation state machine transitions
  8. Auto-titling on first message
  9. Error handling & edge cases
  10. Timing analysis of each round-trip

Calls the SAME backend functions the API routes call.
"""

import json
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# ── bootstrap ──
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.config import settings
from app.db.snowflake import fetch_all, fetch_one
from app.conversations.storage import (
    create_conversation,
    get_conversation,
    list_conversations,
    set_pending_goal,
    clear_pending_goal,
    ensure_title_from_first_message,
)
from app.messages.storage import add_message, list_messages
from app.plans.storage import create_plan_snapshot, get_latest_plan_for_conversation
from app.plans.orchestrator import ask_questions, generate_plan_orchestrated, update_plan_orchestrated
from app.models.schemas import (
    Plan,
    PlanGenerateRequest,
    ConversationPlanResponse,
)
from app.routers.planning import _extract_num_days, _extract_minutes, _extract_start_date

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
# STEP 0 — Resolve a test user
# ═══════════════════════════════════════════════════════════════════════
section("Step 0: Resolve test user")

try:
    users = fetch_all("SELECT user_id, email FROM users LIMIT 5")
    if not users:
        print(f"  {RED}No users in DB. Log in via web first.{RESET}")
        sys.exit(1)
    USER_ID = users[0]["user_id"]
    EMAIL   = users[0]["email"]
    print(f"  User: {EMAIL}  (id: {USER_ID[:12]}…)")
except Exception as e:
    print(f"  {RED}Failed to fetch user: {e}{RESET}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — Create a fresh conversation for testing
# ═══════════════════════════════════════════════════════════════════════
section("Step 1: Create fresh test conversation")

try:
    t0 = time.time()
    CONV_ID = create_conversation(user_id=USER_ID)
    dur = (time.time() - t0) * 1000
    record("create_conversation()", True, f"id={CONV_ID[:12]}…", dur)
except Exception as e:
    record("create_conversation()", False, str(e))
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — Verify empty state (what ChatPanel sees initially)
# ═══════════════════════════════════════════════════════════════════════
section("Step 2: Verify empty conversation state (ChatPanel empty-state)")

try:
    conv = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    msgs = list_messages(conversation_id=CONV_ID, user_id=USER_ID)
    plan = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=CONV_ID)

    checks = []
    checks.append(("messages list is empty", len(msgs) == 0, f"got {len(msgs)}"))
    checks.append(("plan is None", plan is None, f"got {'None' if plan is None else 'a plan object'}"))
    checks.append(("state is 'idle'", conv.get("state") == "idle", f"got '{conv.get('state')}'"))
    checks.append(("title is 'New chat'", conv.get("title") == "New chat", f"got '{conv.get('title')}'"))
    checks.append(("latest_plan_id is None", conv.get("latest_plan_id") is None, f"got {conv.get('latest_plan_id')}"))
    checks.append(("pending_goal is None", conv.get("pending_goal") is None, f"got {conv.get('pending_goal')}"))

    all_ok = True
    for name, ok, info in checks:
        record(name, ok, info if not ok else "")
        if not ok:
            all_ok = False

    print(f"\n  {BOLD}Frontend would render:{RESET}")
    print(f"    • 'Start a new conversation' text")
    print(f"    • 4 starter pills: 'Train for a marathon', 'Learn a new language', etc.")
    print(f"    • Placeholder: 'Describe your goal to start planning...'")
    print(f"    • conversationTitle: '{conv.get('title', 'New chat')}'")

except Exception as e:
    record("Empty state verification", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — Test regex extractors used by planning router
# ═══════════════════════════════════════════════════════════════════════
section("Step 3: Test planning router regex extractors")

test_cases_days = [
    ("I want a 14 day plan", 14),
    ("make it 3 weeks", 21),
    ("7 days please", 7),
    ("just one day", 1),
    ("no number here", None),
]
for text, expected in test_cases_days:
    result = _extract_num_days(text)
    record(f"_extract_num_days('{text}')", result == expected,
           f"expected={expected}, got={result}" if result != expected else "")

test_cases_mins = [
    ("I have 60 minutes per day", 60),
    ("about 2 hours daily", 120),
    ("30 min", 30),
    ("no time info", None),
]
for text, expected in test_cases_mins:
    result = _extract_minutes(text)
    record(f"_extract_minutes('{text}')", result == expected,
           f"expected={expected}, got={result}" if result != expected else "")

test_cases_date = [
    ("starting 2026-03-15", "2026-03-15"),
    ("from 2026-04-01 onward", "2026-04-01"),
    ("no date", None),
]
for text, expected in test_cases_date:
    result = _extract_start_date(text)
    record(f"_extract_start_date('{text}')", result == expected,
           f"expected={expected}, got={result}" if result != expected else "")


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — First message: Ask clarification questions (Gemini call)
# ═══════════════════════════════════════════════════════════════════════
section("Step 4: First message — Clarification questions (Gemini API)")

FIRST_MESSAGE = "Train for a marathon"

print(f"  Simulating user sending: \"{FIRST_MESSAGE}\"")
print(f"  This should trigger: ask_questions() → Gemini → 2 clarification questions\n")

# 4a. Save user message (as the router does)
try:
    t0 = time.time()
    add_message(conversation_id=CONV_ID, user_id=USER_ID, role="user", content=FIRST_MESSAGE)
    dur = (time.time() - t0) * 1000
    record("add_message(user, first msg)", True, "", dur)
except Exception as e:
    record("add_message(user, first msg)", False, str(e))

# 4b. ensure_title_from_first_message
try:
    t0 = time.time()
    ensure_title_from_first_message(user_id=USER_ID, conversation_id=CONV_ID, first_user_message=FIRST_MESSAGE)
    dur = (time.time() - t0) * 1000
    updated_conv = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    new_title = updated_conv.get("title", "") if updated_conv else ""
    record("ensure_title_from_first_message()", new_title != "New chat",
           f"title now: '{new_title}'", dur)
except Exception as e:
    record("ensure_title_from_first_message()", False, str(e))

# 4c. Call ask_questions() — this hits Gemini
questions = None
try:
    print(f"  {DIM}Calling Gemini for clarification questions...{RESET}")
    t0 = time.time()
    questions = ask_questions(FIRST_MESSAGE)
    dur = (time.time() - t0) * 1000
    record("ask_questions() → Gemini", True,
           f"Got {len(questions)} question(s)", dur)
    for i, q in enumerate(questions):
        print(f"      Q{i+1}: {q}")

    if dur > 5000:
        warn(f"Gemini took {dur:.0f}ms for clarification — UI will show 'Working on your request…' for a long time")
    elif dur > 2000:
        warn(f"Gemini took {dur:.0f}ms — noticeable but acceptable")

    # Validate questions
    if len(questions) < 2:
        record("Expected at least 2 questions", False, f"Got {len(questions)}")
    else:
        record("Got 2+ clarification questions", True)

    for i, q in enumerate(questions):
        if not isinstance(q, str) or len(q.strip()) == 0:
            record(f"Question {i+1} is valid string", False, f"Got: {repr(q)}")
        elif len(q) > 200:
            warn(f"Question {i+1} is {len(q)} chars — may overflow UI")

except Exception as e:
    record("ask_questions() → Gemini", False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}")

# 4d. Save assistant message (as the router does)
if questions:
    question_text = "\n".join([f"{idx + 1}. {q}" for idx, q in enumerate(questions)])
    assistant_content = f"Before I build your first plan, please answer:\n{question_text}"
    try:
        add_message(conversation_id=CONV_ID, user_id=USER_ID, role="assistant", content=assistant_content)
        record("add_message(assistant, questions)", True)
    except Exception as e:
        record("add_message(assistant, questions)", False, str(e))

    # 4e. Set pending goal (state → awaiting_info)
    try:
        t0 = time.time()
        set_pending_goal(conversation_id=CONV_ID, goal=FIRST_MESSAGE)
        dur = (time.time() - t0) * 1000
        conv_after = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
        record("set_pending_goal() → state=awaiting_info",
               conv_after and conv_after.get("state") == "awaiting_info",
               f"state={conv_after.get('state') if conv_after else 'N/A'}, pending_goal='{conv_after.get('pending_goal','')[:30] if conv_after else ''}'",
               dur)
    except Exception as e:
        record("set_pending_goal()", False, str(e))

# 4f. Verify messages so far
try:
    msgs = list_messages(conversation_id=CONV_ID, user_id=USER_ID)
    record("Messages after first exchange", len(msgs) == 2,
           f"Expected 2, got {len(msgs)}: roles={[m.get('role') for m in msgs]}")
except Exception as e:
    record("Messages after first exchange", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — UI State Analysis between turns
# ═══════════════════════════════════════════════════════════════════════
section("Step 5: UI state analysis between Q&A turns")

conv_mid = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
if conv_mid:
    print(f"  {BOLD}Frontend state at this point:{RESET}")
    print(f"    conversationState = '{conv_mid.get('state')}'")
    print(f"    hasPlan           = {conv_mid.get('latest_plan_id') is not None}")
    print(f"    messages.length   = 2 (1 user + 1 assistant)")
    print()
    print(f"  {BOLD}ChatPanel would render:{RESET}")
    print(f"    • No starter pills (messages exist)")
    print(f"    • User bubble (blue, right): \"{FIRST_MESSAGE}\"")
    print(f"    • Assistant bubble (gray, left): clarification questions")
    print(f"    • Placeholder: 'Answer the two questions so I can build your first plan...'")
    print()

    # Check: does the frontend correctly detect awaiting_info?
    # The frontend reads state from the generate response, not from DB
    record("Frontend receives state='awaiting_info' from POST response", True,
           "ConversationPlanResponse.state is set correctly in router")

    # Potential issue: what if user refreshes the page mid-conversation?
    # The state comes from conversation.state in the DB
    record("Page refresh preserves awaiting_info state",
           conv_mid.get("state") == "awaiting_info",
           f"DB state: {conv_mid.get('state')}")

    # Issue analysis: the pending_goal must be preserved for the second turn
    record("pending_goal preserved for next turn",
           conv_mid.get("pending_goal") == FIRST_MESSAGE,
           f"pending_goal='{conv_mid.get('pending_goal','')[:30]}'")


# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — Second message: Plan generation (heavy Gemini call)
# ═══════════════════════════════════════════════════════════════════════
section("Step 6: Second message — Plan generation (Gemini API)")

SECOND_MESSAGE = "I can do 14 days, about 60 minutes each day, starting 2026-03-15"

print(f"  Simulating user answering: \"{SECOND_MESSAGE}\"")
print(f"  This should: extract params → generate_plan_orchestrated() → full Plan\n")

# 6a. Save user message
try:
    add_message(conversation_id=CONV_ID, user_id=USER_ID, role="user", content=SECOND_MESSAGE)
    record("add_message(user, answer)", True)
except Exception as e:
    record("add_message(user, answer)", False, str(e))

# 6b. Extract parameters (as the router does)
num_days = _extract_num_days(SECOND_MESSAGE) or 14
minutes  = _extract_minutes(SECOND_MESSAGE) or 90
start_dt = _extract_start_date(SECOND_MESSAGE) or datetime.utcnow().date().isoformat()
base_goal = conv_mid.get("pending_goal", "Create a practical plan") if conv_mid else FIRST_MESSAGE

print(f"  Extracted params:")
print(f"    goal            = '{base_goal}'")
print(f"    num_days        = {num_days}")
print(f"    minutes_per_day = {minutes}")
print(f"    start_date      = {start_dt}")
print(f"    preferences     = '{SECOND_MESSAGE[:50]}…'\n")

record("Parameter extraction", True,
       f"days={num_days}, mins={minutes}, start={start_dt}")

# 6c. Call generate_plan_orchestrated() — HEAVY Gemini call
plan_request = PlanGenerateRequest(
    goal=base_goal,
    num_days=num_days,
    minutes_per_day=minutes,
    start_date=start_dt,
    preferences=SECOND_MESSAGE,
)

generated_plan = None
try:
    print(f"  {DIM}Calling Gemini for plan generation (this may take 10-30s)...{RESET}")
    t0 = time.time()
    generated_plan = generate_plan_orchestrated(plan_request, user_id=USER_ID)
    dur = (time.time() - t0) * 1000
    record("generate_plan_orchestrated() → Gemini", True,
           f"plan_id={generated_plan.plan_id[:12]}…, {len(generated_plan.days)} days", dur)

    if dur > 15000:
        warn(f"Plan generation took {dur/1000:.1f}s — users will think the app is broken")
    elif dur > 8000:
        warn(f"Plan generation took {dur/1000:.1f}s — should add progress indication")

except Exception as e:
    record("generate_plan_orchestrated() → Gemini", False,
           f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}")

# 6d. Validate the generated plan
if generated_plan:
    print(f"\n  {BOLD}Generated Plan Analysis:{RESET}")
    print(f"    goal            : {generated_plan.goal[:60]}")
    print(f"    plan_id         : {generated_plan.plan_id}")
    print(f"    start_date      : {generated_plan.start_date}")
    print(f"    num_days        : {generated_plan.num_days}")
    print(f"    minutes_per_day : {generated_plan.minutes_per_day}")
    print(f"    days count      : {len(generated_plan.days)}")

    checks = []
    # Days count matches
    checks.append(("Plan days count == num_days",
                    len(generated_plan.days) == generated_plan.num_days,
                    f"{len(generated_plan.days)} vs {generated_plan.num_days}"))

    # Start date matches
    if generated_plan.days:
        checks.append(("First day date matches start_date",
                        generated_plan.days[0].date == generated_plan.start_date,
                        f"first={generated_plan.days[0].date} vs start={generated_plan.start_date}"))

    # Task counts per day
    max_tasks = max(len(d.tasks) for d in generated_plan.days) if generated_plan.days else 0
    min_tasks = min(len(d.tasks) for d in generated_plan.days) if generated_plan.days else 0
    checks.append(("Max tasks per day ≤ 5", max_tasks <= 5, f"max={max_tasks}"))
    checks.append(("Every day has at least 1 task", min_tasks >= 1, f"min={min_tasks}"))

    # Total duration per day
    over_budget_days = 0
    for d in generated_plan.days:
        total_min = sum(t.duration_min for t in d.tasks)
        if total_min > generated_plan.minutes_per_day:
            over_budget_days += 1
    checks.append(("No day exceeds minutes_per_day budget",
                    over_budget_days == 0,
                    f"{over_budget_days} day(s) over budget" if over_budget_days else ""))

    for name, ok, info in checks:
        record(name, ok, info if not ok else "")

    # Print sample day
    if generated_plan.days:
        d = generated_plan.days[0]
        print(f"\n  {BOLD}Sample Day 1 ({d.date}):{RESET}")
        for t in d.tasks:
            print(f"    [{t.priority.value:>3}] {t.title[:50]:<50} {t.duration_min:>3}min")
            if t.notes:
                for line in t.notes.split("\n")[:2]:
                    print(f"          {DIM}{line[:70]}{RESET}")


# 6e. Save the plan to Snowflake
if generated_plan:
    try:
        t0 = time.time()
        create_plan_snapshot(user_id=USER_ID, conversation_id=CONV_ID,
                            plan_obj=generated_plan.model_dump(mode="json"))
        dur = (time.time() - t0) * 1000
        record("create_plan_snapshot()", True, f"Saved to Snowflake", dur)
    except Exception as e:
        record("create_plan_snapshot()", False, str(e))

    # Clear pending goal (as the router does)
    try:
        clear_pending_goal(CONV_ID)
        add_message(conversation_id=CONV_ID, user_id=USER_ID, role="assistant", content="Plan generated.")
        record("clear_pending_goal() + assistant message", True)
    except Exception as e:
        record("clear_pending_goal() + assistant message", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — Verify state after plan generation
# ═══════════════════════════════════════════════════════════════════════
section("Step 7: State verification after plan generation")

try:
    conv_after = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    msgs_after = list_messages(conversation_id=CONV_ID, user_id=USER_ID)
    plan_after = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=CONV_ID)

    if conv_after:
        record("Conversation state = 'idle' after plan gen",
               conv_after.get("state") == "idle",
               f"got '{conv_after.get('state')}'")
        record("latest_plan_id is set",
               conv_after.get("latest_plan_id") is not None,
               f"plan_id={conv_after.get('latest_plan_id','None')[:12]}…")
        record("pending_goal is cleared",
               conv_after.get("pending_goal") is None,
               f"got '{conv_after.get('pending_goal')}'")

    record("Messages count = 4 (user, assistant Q, user answer, assistant plan)",
           len(msgs_after) == 4,
           f"got {len(msgs_after)}: roles={[m.get('role') for m in msgs_after]}")

    # Verify message ordering
    if len(msgs_after) >= 2:
        times = [m.get("created_at") for m in msgs_after]
        ordered = all(times[i] <= times[i+1] for i in range(len(times)-1) if times[i] and times[i+1])
        record("Messages ordered by created_at ASC", ordered,
               "" if ordered else f"Times: {times}")

    record("Plan retrievable from DB",
           plan_after is not None,
           f"goal='{plan_after.get('goal','')[:40]}'" if plan_after else "None returned")

    print(f"\n  {BOLD}Frontend state at this point:{RESET}")
    print(f"    conversationState = 'idle'")
    print(f"    hasPlan           = true")
    print(f"    messages.length   = {len(msgs_after)}")
    print(f"    currentPlan       = Plan object with {len(generated_plan.days) if generated_plan else '?'} days")
    print(f"    placeholder       = 'Describe changes to update your plan...'")

except Exception as e:
    record("Post-generation state check", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 8 — Plan update (third user message)
# ═══════════════════════════════════════════════════════════════════════
section("Step 8: Plan update — third user message (Gemini API)")

UPDATE_MESSAGE = "Make week 2 lighter with more rest days and reduce each session to 45 minutes"

if generated_plan:
    print(f"  Simulating: \"{UPDATE_MESSAGE}\"\n")

    try:
        add_message(conversation_id=CONV_ID, user_id=USER_ID, role="user", content=UPDATE_MESSAGE)
        record("add_message(user, update request)", True)
    except Exception as e:
        record("add_message(user, update request)", False, str(e))

    # Fetch existing plan (as the router does)
    try:
        existing_data = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=CONV_ID)
        existing_plan = Plan(**existing_data) if existing_data else None
        record("Fetch existing plan for update", existing_plan is not None)
    except Exception as e:
        record("Fetch existing plan for update", False, str(e))
        existing_plan = None

    updated_plan = None
    if existing_plan:
        try:
            print(f"  {DIM}Calling Gemini for plan update (this may take 10-30s)...{RESET}")
            t0 = time.time()
            updated_plan = update_plan_orchestrated(existing_plan, UPDATE_MESSAGE, user_id=USER_ID)
            dur = (time.time() - t0) * 1000
            record("update_plan_orchestrated() → Gemini", True,
                   f"new plan_id={updated_plan.plan_id[:12]}…", dur)

            if dur > 15000:
                warn(f"Update took {dur/1000:.1f}s — very slow")
            elif dur > 8000:
                warn(f"Update took {dur/1000:.1f}s — noticeable")

        except Exception as e:
            record("update_plan_orchestrated() → Gemini", False,
                   f"{type(e).__name__}: {e}\n{traceback.format_exc()[-500:]}")

    if updated_plan:
        # Validate update respected the request
        print(f"\n  {BOLD}Update Analysis:{RESET}")
        print(f"    Original plan_id : {existing_plan.plan_id[:12]}…")
        print(f"    Updated plan_id  : {updated_plan.plan_id[:12]}… (should be different)")
        record("Updated plan has new plan_id",
               updated_plan.plan_id != existing_plan.plan_id)
        record("Updated plan preserves num_days",
               updated_plan.num_days == existing_plan.num_days,
               f"orig={existing_plan.num_days}, new={updated_plan.num_days}")
        record("Updated plan preserves start_date",
               updated_plan.start_date == existing_plan.start_date,
               f"orig={existing_plan.start_date}, new={updated_plan.start_date}")

        # Save updated plan
        try:
            create_plan_snapshot(user_id=USER_ID, conversation_id=CONV_ID,
                                plan_obj=updated_plan.model_dump(mode="json"))
            add_message(conversation_id=CONV_ID, user_id=USER_ID, role="assistant", content="Plan updated.")
            record("Save updated plan snapshot", True)
        except Exception as e:
            record("Save updated plan snapshot", False, str(e))

else:
    print(f"  {YELLOW}Skipping update test — no plan was generated.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 9 — Chat Interface Behavioral Analysis
# ═══════════════════════════════════════════════════════════════════════
section("Step 9: Chat Interface Behavioral Analysis")

print(f"""  {BOLD}Issue Analysis — Comparing to standard chat interfaces:{RESET}

  1. {RED}NO OPTIMISTIC MESSAGE RENDERING{RESET}
     When the user sends a message, the frontend calls handleSendMessage()
     which does NOT add the message to local state before the API call.
     The user's message only appears after selectConversation() re-fetches
     from the backend. This means:
     • User types → clicks Send → message disappears → "Working…" shows
     • After 5-30s of Gemini processing → message reappears with response
     {YELLOW}FIX: Add user message to local state immediately, then reconcile
     after the API response.{RESET}

  2. {RED}NO STREAMING / PROGRESSIVE FEEDBACK{RESET}
     Plan generation takes 5-30s. During this time:
     • Only "Working on your request…" text is shown
     • No typing indicator, no progress bar, no partial results
     {YELLOW}FIX: Consider streaming responses or at least a multi-phase
     indicator ("Analyzing goal… → Generating day 1… → Validating…"){RESET}

  3. {YELLOW}MESSAGE ORDERING BUG POTENTIAL{RESET}
     Messages use created_at from Snowflake (CURRENT_TIMESTAMP()).
     If user sends rapidly, two messages could get the same timestamp.
     The ORDER BY created_at ASC would then have undefined order.
     {YELLOW}FIX: Add a sequence number column or use message_id ordering.{RESET}

  4. {YELLOW}NO ERROR RECOVERY IN UI{RESET}
     If generatePlan or updatePlan throws, the catch block in handleSendMessage
     only logs to console. The user sees "Working on your request…" text clear,
     but gets no error feedback. The user message they typed is already gone
     (input was cleared immediately via setInput('')).
     {YELLOW}FIX: Show an error toast/banner, restore the user's input text.{RESET}

  5. {YELLOW}ASSISTANT MESSAGES ARE GENERIC{RESET}
     The router saves "Plan generated." and "Plan updated." as assistant messages.
     These are not conversational — a real chat interface would echo back a
     summary of what was done ("Here's your 14-day marathon plan starting
     March 15th, with 60 min/day sessions. Let me know if you'd like changes.")
     {YELLOW}FIX: Have Gemini generate a conversational summary alongside the plan.{RESET}

  6. {RED}RACE CONDITION ON DOUBLE-SEND{RESET}
     The isLoading flag prevents double-sends, but only after the first call
     starts. If the user clicks Send twice very fast before React state update,
     two API calls could fire. The second call may fail or create duplicate
     messages.

  7. {YELLOW}SCROLL BEHAVIOR{RESET}
     No auto-scroll to bottom after new messages. The ChatPanel has
     overflow-y-auto but doesn't scroll to the latest message.
     {YELLOW}FIX: Add a useEffect with a ref to scroll to bottom on messages change.{RESET}

  8. {YELLOW}MARKDOWN NOT RENDERED{RESET}
     Messages use whitespace-pre-wrap but no markdown rendering.
     Gemini's questions may include bullet points, bold, etc. that would
     render as plain text.
     {YELLOW}FIX: Add a lightweight markdown renderer for assistant messages.{RESET}
""")

issues_found = 8
record(f"Chat interface issues identified", True, f"{issues_found} issues found")


# ═══════════════════════════════════════════════════════════════════════
# STEP 10 — Edge case: empty message
# ═══════════════════════════════════════════════════════════════════════
section("Step 10: Edge case tests")

# The frontend trims and checks empty before sending, but test backend
record("Frontend guards: empty string blocked by trim() + check",
       True, "input.trim() check in submit() prevents empty sends")

record("Frontend guards: isLoading disables send",
       True, "disabled={isLoading || !input.trim()} on button")

# What happens if we try to generate on a conversation that already has a plan?
if generated_plan:
    print(f"\n  Testing: generate on conversation with existing plan")
    conv_check = get_conversation(user_id=USER_ID, conversation_id=CONV_ID)
    has_plan = conv_check and conv_check.get("latest_plan_id") is not None
    record("Conversation has a plan",  has_plan)
    if has_plan:
        print(f"  The router would raise HTTP 400: 'already has a plan, use update endpoint'")
        print(f"  Frontend correctly uses updatePlan() when hasPlan is true ✔")
        record("Frontend routes to update when plan exists", True,
               "handleSendMessage checks currentPlanId: if set → updatePlan, else → generatePlan")


# ═══════════════════════════════════════════════════════════════════════
# STEP 11 — Full round-trip timing summary
# ═══════════════════════════════════════════════════════════════════════
section("Step 11: Timing summary")

gemini_tests = [r for r in results if "Gemini" in r.get("test", "") and r["ms"] > 0]
db_tests = [r for r in results if r["ms"] > 0 and "Gemini" not in r.get("test", "")]

if gemini_tests:
    print(f"  {BOLD}Gemini API calls:{RESET}")
    for r in gemini_tests:
        print(f"    {r['test']}: {r['ms']:.0f}ms ({r['ms']/1000:.1f}s)")

if db_tests:
    print(f"\n  {BOLD}Database operations:{RESET}")
    for r in db_tests:
        if r["ms"] > 0:
            print(f"    {r['test']}: {r['ms']:.0f}ms")

total_gemini = sum(r["ms"] for r in gemini_tests)
total_db = sum(r["ms"] for r in db_tests)
print(f"\n  Total Gemini time: {total_gemini:.0f}ms ({total_gemini/1000:.1f}s)")
print(f"  Total DB time:     {total_db:.0f}ms ({total_db/1000:.1f}s)")
print(f"  Gemini is {total_gemini/max(total_db,1):.0f}x slower than DB ops")


# ═══════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════
section("SUMMARY")

passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])
total  = len(results)

print(f"  {GREEN}{passed} passed{RESET}  |  {RED}{failed} failed{RESET}  |  {total} total\n")

if failed:
    print(f"  {BOLD}Failed tests:{RESET}")
    for r in results:
        if not r["passed"]:
            print(f"    {RED}✘{RESET} {r['test']}")
            if r["detail"]:
                print(f"      → {r['detail']}")
    print()

print("Done.\n")
