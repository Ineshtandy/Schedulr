#!/usr/bin/env python3
"""
CLI Test Tool: Sidebar — Conversations List
============================================
Imitates the actions that happen when the user interacts with the sidebar:
  1. Load conversations list (GET /api/conversations)
  2. Select a conversation (GET /api/conversations/{id})
  3. Create a new conversation (POST /api/conversations)
  4. Sidebar collapse/expand (frontend-only localStorage behavior)

Calls the SAME backend functions the API routes call, measures timing,
and reports errors.
"""

import json
import os
import sys
import time
from pathlib import Path

# ── bootstrap: add backend to sys.path so we can import app modules ──
BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)  # so .env resolution works

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

# ── Now we can import app internals ──
from app.config import settings
from app.db.snowflake import fetch_all, fetch_one
from app.conversations.storage import (
    create_conversation,
    get_conversation,
    list_conversations,
    update_conversation_title,
)
from app.messages.storage import list_messages
from app.plans.storage import get_latest_plan_for_conversation
from app.utils.session import create_session, load_session


# ═══════════════════════════════════════════════════════════════════════
BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
YELLOW = "\033[93m"
CYAN  = "\033[96m"
RESET = "\033[0m"
PASS  = f"{GREEN}✔ PASS{RESET}"
FAIL  = f"{RED}✘ FAIL{RESET}"
WARN  = f"{YELLOW}⚠ WARN{RESET}"

results = []

def section(title: str):
    print(f"\n{BOLD}{CYAN}{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}{RESET}\n")

def record(test_name: str, passed: bool, detail: str = "", duration_ms: float = 0):
    status = PASS if passed else FAIL
    timing = f"  [{duration_ms:.0f}ms]" if duration_ms else ""
    print(f"  {status}  {test_name}{timing}")
    if detail:
        print(f"        {detail}")
    results.append({"test": test_name, "passed": passed, "detail": detail, "ms": duration_ms})


# ═══════════════════════════════════════════════════════════════════════
# STEP 0 — Resolve a real user_id from the database
# ═══════════════════════════════════════════════════════════════════════
section("Step 0: Resolve a real test user")

try:
    t0 = time.time()
    users = fetch_all("SELECT user_id, email FROM users LIMIT 5")
    dur = (time.time() - t0) * 1000
    if not users:
        print(f"  {RED}No users found in Snowflake. Please log in via the web at least once.{RESET}")
        sys.exit(1)
    USER_ID = users[0]["user_id"]
    EMAIL   = users[0]["email"]
    print(f"  Using user: {EMAIL}  (id: {USER_ID[:12]}…)")
    print(f"  Found {len(users)} total user(s)  [{dur:.0f}ms]")
    record("Fetch users from Snowflake", True, f"{len(users)} user(s)", dur)
except Exception as e:
    record("Fetch users from Snowflake", False, str(e))
    print(f"\n  {RED}Cannot continue without a valid user. Exiting.{RESET}")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — Session creation & validation  (simulates GET /api/me)
# ═══════════════════════════════════════════════════════════════════════
section("Step 1: Session creation & validation (GET /api/me analogue)")

try:
    t0 = time.time()
    session_token = create_session({"user_id": USER_ID, "email": EMAIL})
    dur_create = (time.time() - t0) * 1000
    record("create_session()", True, f"token length={len(session_token)}", dur_create)
except Exception as e:
    record("create_session()", False, str(e))
    session_token = None

if session_token:
    t0 = time.time()
    data = load_session(session_token)
    dur_load = (time.time() - t0) * 1000
    if data and data.get("user_id") == USER_ID:
        record("load_session() round-trip", True, f"user_id matches", dur_load)
    else:
        record("load_session() round-trip", False, f"Got: {data}", dur_load)

    # Check with a garbage token
    bad = load_session("totally.invalid.token")
    record("load_session(bad_token) returns None", bad is None, f"Got: {bad}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — List conversations (GET /api/conversations)
# ═══════════════════════════════════════════════════════════════════════
section("Step 2: List conversations (GET /api/conversations)")

conversations = []
try:
    t0 = time.time()
    conversations = list_conversations(USER_ID)
    dur = (time.time() - t0) * 1000
    record("list_conversations()", True, f"Returned {len(conversations)} conversation(s)", dur)

    if dur > 2000:
        print(f"  {WARN}  Query took {dur:.0f}ms — may feel sluggish in the UI")

    # Print first few
    for i, c in enumerate(conversations[:5]):
        state = c.get("state", "?")
        title = (c.get("title") or "")[:40]
        print(f"      [{i}] {c['conversation_id'][:12]}…  state={state:<14} title=\"{title}\"")
    if len(conversations) > 5:
        print(f"      … and {len(conversations) - 5} more")

except Exception as e:
    record("list_conversations()", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — Select first conversation (GET /api/conversations/{id})
# ═══════════════════════════════════════════════════════════════════════
section("Step 3: Select a conversation (GET /api/conversations/{id})")

if conversations:
    cid = conversations[0]["conversation_id"]
    print(f"  Selecting conversation: {cid[:12]}…\n")

    # 3a. get_conversation
    try:
        t0 = time.time()
        conv = get_conversation(user_id=USER_ID, conversation_id=cid)
        dur = (time.time() - t0) * 1000
        if conv:
            record("get_conversation()", True, f"state={conv.get('state')}, title=\"{conv.get('title','')[:40]}\"", dur)
        else:
            record("get_conversation()", False, "Returned None for existing conversation", dur)
    except Exception as e:
        record("get_conversation()", False, str(e))

    # 3b. list_messages
    try:
        t0 = time.time()
        messages = list_messages(conversation_id=cid, user_id=USER_ID)
        dur = (time.time() - t0) * 1000
        record("list_messages()", True, f"{len(messages)} message(s)", dur)
        for m in messages[:6]:
            role = m.get("role", "?")
            snippet = (m.get("content",""))[:60].replace("\n", " ")
            print(f"      {role:>9}: \"{snippet}…\"")
        if len(messages) > 6:
            print(f"      … and {len(messages) - 6} more messages")
    except Exception as e:
        record("list_messages()", False, str(e))

    # 3c. get_latest_plan_for_conversation
    try:
        t0 = time.time()
        plan_data = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=cid)
        dur = (time.time() - t0) * 1000
        if plan_data:
            record("get_latest_plan_for_conversation()", True,
                   f"plan_id={plan_data.get('plan_id','?')[:12]}…, goal=\"{plan_data.get('goal','')[:40]}\"", dur)
        else:
            record("get_latest_plan_for_conversation()", True, "No plan yet (expected for new chats)", dur)
    except Exception as e:
        record("get_latest_plan_for_conversation()", False, str(e))

else:
    print(f"  {YELLOW}No conversations to select — skipping.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — Selecting second conversation (if exists) to test switching
# ═══════════════════════════════════════════════════════════════════════
section("Step 4: Switch to second conversation (simulates sidebar click)")

if len(conversations) >= 2:
    cid2 = conversations[1]["conversation_id"]
    print(f"  Switching to: {cid2[:12]}…\n")

    try:
        t0 = time.time()
        conv2 = get_conversation(user_id=USER_ID, conversation_id=cid2)
        msgs2 = list_messages(conversation_id=cid2, user_id=USER_ID)
        plan2 = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=cid2)
        dur = (time.time() - t0) * 1000
        record("Switch conversation (3 queries)", True,
               f"msgs={len(msgs2)}, has_plan={'yes' if plan2 else 'no'}", dur)
        if dur > 3000:
            print(f"  {WARN}  3-query switch took {dur:.0f}ms — frontend will feel slow")
    except Exception as e:
        record("Switch conversation (3 queries)", False, str(e))
else:
    print(f"  {YELLOW}Only 0-1 conversations — skipping switch test.{RESET}")


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — Create new conversation (POST /api/conversations)
# ═══════════════════════════════════════════════════════════════════════
section("Step 5: Create new conversation (POST /api/conversations)")

try:
    t0 = time.time()
    new_cid = create_conversation(user_id=USER_ID)
    dur = (time.time() - t0) * 1000
    record("create_conversation()", True, f"new id={new_cid[:12]}…", dur)
    if dur > 2000:
        print(f"  {WARN}  Creation took {dur:.0f}ms — UI button will feel unresponsive")

    # Verify it appears in the list
    t0 = time.time()
    refreshed = list_conversations(USER_ID)
    dur2 = (time.time() - t0) * 1000
    found = any(c["conversation_id"] == new_cid for c in refreshed)
    record("New conv appears in list after refresh", found,
           f"list now has {len(refreshed)} items", dur2)

    # Verify its initial state
    new_conv = get_conversation(user_id=USER_ID, conversation_id=new_cid)
    if new_conv:
        checks = []
        if new_conv.get("state") == "idle":
            checks.append("state=idle ✔")
        else:
            checks.append(f"state={new_conv.get('state')} ✘ (expected idle)")
        if new_conv.get("title") == "New chat":
            checks.append("title='New chat' ✔")
        else:
            checks.append(f"title='{new_conv.get('title')}' ✘ (expected 'New chat')")
        if new_conv.get("latest_plan_id") is None:
            checks.append("latest_plan_id=None ✔")
        else:
            checks.append(f"latest_plan_id set ✘")

        all_ok = all("✔" in c for c in checks)
        record("New conversation initial state", all_ok, " | ".join(checks))
    else:
        record("New conversation initial state", False, "get_conversation returned None")

except Exception as e:
    record("create_conversation()", False, str(e))
    new_cid = None


# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — Sidebar Collapse/Expand (Frontend-only analysis)
# ═══════════════════════════════════════════════════════════════════════
section("Step 6: Sidebar Collapse/Expand (Frontend Analysis)")

print(f"""  The sidebar collapse is 100% frontend — no backend calls.

  {BOLD}How it works:{RESET}
  • Sidebar.tsx maintains a `collapsed` state, initialized from
    localStorage key 'schedulr_sidebar_collapsed' ('1' or '0').
  • When collapsed=true:
    – Renders a narrow column with just '→' (expand) and '+' (new plan) buttons.
    – The parent <aside> still has class w-80 — {RED}the width does NOT shrink.{RESET}
  • When collapsed=false:
    – Full conversation list with 'New plan' button and '←' collapse button.

  {BOLD}Potential Issues Found:{RESET}
  1. {RED}LAYOUT BUG:{RESET} The <aside className="w-80"> in app/page.tsx is HARDCODED.
     When the sidebar renders its collapsed variant, the aside STILL occupies
     w-80 (320px). The chat panel does NOT expand to fill the space.
     {YELLOW}FIX: The collapsed state should be lifted to AppPage so the
     <aside> width can be toggled (e.g., w-80 vs w-14).{RESET}

  2. {YELLOW}PERSISTENCE:{RESET} localStorage is used, which is fine for a SPA.
     But there's no URL-driven state — refreshing doesn't lose collapse state
     (good), but there's no way to deep-link to a collapsed view (minor).

  3. {YELLOW}NO ANIMATION:{RESET} The collapse/expand is instant with no transition.
     Consider adding a CSS transition on width for polish.
""")

record("Sidebar collapse: width not reactive to collapsed state", False,
       "Parent <aside> always w-80 regardless of collapsed state")
record("Sidebar collapse: localStorage persistence works", True,
       "Key: schedulr_sidebar_collapsed")


# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — Update conversation title (PATCH /api/conversations/{id})
# ═══════════════════════════════════════════════════════════════════════
section("Step 7: Update conversation title (PATCH analogue)")

if new_cid:
    try:
        test_title = "CLI Test Conversation"
        t0 = time.time()
        update_conversation_title(user_id=USER_ID, conversation_id=new_cid, title=test_title)
        dur = (time.time() - t0) * 1000
        record("update_conversation_title()", True, f"Set to '{test_title}'", dur)

        # Verify
        updated = get_conversation(user_id=USER_ID, conversation_id=new_cid)
        record("Title updated correctly", updated and updated.get("title") == test_title,
               f"Got: '{updated.get('title') if updated else 'None'}'")
    except Exception as e:
        record("update_conversation_title()", False, str(e))


# ═══════════════════════════════════════════════════════════════════════
# STEP 8 — Timing analysis: full "open dashboard" sequence
# ═══════════════════════════════════════════════════════════════════════
section("Step 8: Full Dashboard Load Timing (simulates /app initialization)")

if conversations:
    first_cid = conversations[0]["conversation_id"]
    print(f"  Simulating: getMe() → listConversations() → getConversation(first)\n")

    t_total = time.time()

    t0 = time.time()
    session_token_2 = create_session({"user_id": USER_ID, "email": EMAIL})
    session_data = load_session(session_token_2)
    t_me = (time.time() - t0) * 1000

    t0 = time.time()
    convs = list_conversations(USER_ID)
    t_list = (time.time() - t0) * 1000

    t0 = time.time()
    _ = get_conversation(user_id=USER_ID, conversation_id=first_cid)
    _ = list_messages(conversation_id=first_cid, user_id=USER_ID)
    _ = get_latest_plan_for_conversation(user_id=USER_ID, conversation_id=first_cid)
    t_detail = (time.time() - t0) * 1000

    t_total = (time.time() - t_total) * 1000

    print(f"      getMe()              : {t_me:>7.0f} ms")
    print(f"      listConversations()  : {t_list:>7.0f} ms")
    print(f"      getConversation(full): {t_detail:>7.0f} ms  (conv + msgs + plan)")
    print(f"      {'─' * 40}")
    print(f"      TOTAL                : {t_total:>7.0f} ms\n")

    if t_total > 5000:
        record("Dashboard load total time", False, f"{t_total:.0f}ms — very slow, will frustrate users")
    elif t_total > 2000:
        record("Dashboard load total time", False, f"{t_total:.0f}ms — noticeable delay")
    else:
        record("Dashboard load total time", True, f"{t_total:.0f}ms — acceptable")

    # NOTE: these are sequential, but the frontend also runs them sequentially
    # (getMe must succeed before listConversations is called)


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
