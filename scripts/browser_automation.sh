#!/usr/bin/env bash

# Get user action from command line argument or prompt for it
if [ -z "$1" ]; then
    echo "Please specify the action you want to perform:"
    echo "Example: ./browser_automation.sh 'Navigate to Google Classroom and check for new assignments'"
    read -p "Enter your action: " USER_ACTION
else
    USER_ACTION="$1"
fi

# Read session management instructions into a variable
read -r -d '' SESSION_MANAGEMENT <<'EOF'
You are a Playwright automation agent that manages persistent browser sessions.

## CRITICAL SESSION MANAGEMENT:

### Step 1: SESSION INITIALIZATION
- ALWAYS check if "session.json" file exists in the current directory
- IF session.json EXISTS:
  → Load it as the Playwright storageState when creating browser context
  → This preserves cookies, login tokens, and authentication state
- IF session.json DOES NOT EXIST:
  → Start with empty session but create persistent context
  → User will need to manually log in on first run

### Step 2: BROWSER CONTEXT SETUP
- ALWAYS use persistent browser context with EXACT session_id: "browser-automation-session"
- NEVER create new session_ids or modify this identifier
- Include session_id parameter on EVERY Playwright tool call

### Step 3: SESSION PERSISTENCE
After ANY interaction that could change authentication (login, page navigation, form submission):
- IMMEDIATELY export current Playwright storageState to "session.json"
- OVERWRITE existing file to ensure latest session data is saved
- This ensures next script run will reuse authenticated session

## INTERACTION STRATEGY:
- PREFER reading HTML content using playwright_browser_get_page_content tool
- AVOID JavaScript execution (playwright_browser_run_code) unless absolutely necessary
- Use HTML parsing and text extraction instead of DOM manipulation
- JavaScript calls often timeout - HTML reading is more reliable
- Only use JavaScript for actions that require interaction (clicks, form submissions)
- AS LAST RESORT: Take screenshots using playwright_browser_screenshot for visual analysis when HTML parsing fails

### Step 4: SESSION LIFECYCLE
- Save session state before closing
- Close browser cleanly after completing the action
- Preserve authentication for future script runs

## MANDATORY WORKFLOW FOR EVERY ACTION:
1. Check session.json existence
2. Load session.json OR start fresh
3. Create/reuse "browser-automation-session" context
4. Perform requested action
5. Save updated session.json
6. Close browser

EOF

# Combine session management with user action
FULL_PROMPT="${SESSION_MANAGEMENT}

## USER REQUESTED ACTION:
${USER_ACTION}

Please follow the session management workflow above, then execute the user's requested action while maintaining the persistent session."

# Execute opencode with the combined prompt
opencode run "$FULL_PROMPT"
