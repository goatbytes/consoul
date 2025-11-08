#!/bin/bash
# Gira TUI Refresh Hook - Automatically refresh TUI when tickets are moved
#
# This hook is triggered whenever a ticket is moved between statuses.
# It creates a flag file that the TUI will detect and use to trigger a refresh.

# Check if TUI is running by looking for PID file
TUI_PID_FILE="/tmp/gira-tui.pid"
TUI_REFRESH_FLAG="/tmp/gira-tui-refresh.flag"

if [ -f "$TUI_PID_FILE" ]; then
    TUI_PID=$(cat "$TUI_PID_FILE" 2>/dev/null)

    # Verify the process is actually running and is gira tui
    if [ -n "$TUI_PID" ] && kill -0 "$TUI_PID" 2>/dev/null; then
        # Check if it's actually a gira tui process (optional safety check)
        if ps -p "$TUI_PID" -o command= | grep -q "gira.*tui" 2>/dev/null; then
            # Create refresh flag file with timestamp and ticket info
            echo "$(date +%s):$GIRA_TICKET_ID:$GIRA_OLD_STATUS:$GIRA_NEW_STATUS" > "$TUI_REFRESH_FLAG"

            # Log the refresh (optional, can be removed for silent operation)
            if [ "${GIRA_HOOK_VERBOSE:-}" = "true" ]; then
                echo "TUI refresh flag created for ticket $GIRA_TICKET_ID ($GIRA_OLD_STATUS → $GIRA_NEW_STATUS)"
            fi
        else
            # Clean up stale PID file
            rm -f "$TUI_PID_FILE" 2>/dev/null
        fi
    else
        # Clean up stale PID file
        rm -f "$TUI_PID_FILE" 2>/dev/null
    fi
fi

# Exit successfully (hook should not fail even if TUI is not running)
exit 0
