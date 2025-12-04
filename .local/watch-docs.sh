#!/bin/bash
# Auto-restart MkDocs server when docs/overrides changes
# This works around the Click 8.3.x bug that breaks MkDocs watch functionality

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SERVER_PID=""

# Cleanup function
cleanup() {
  echo -e "\n${YELLOW}Shutting down server...${NC}"
  if [ ! -z "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null || true
  fi
  exit 0
}

# Set up trap for clean exit
trap cleanup SIGINT SIGTERM

# Function to start server
start_server() {
  echo -e "${GREEN}Starting MkDocs server...${NC}"
  poetry run mkdocs serve &
  SERVER_PID=$!
  echo -e "${GREEN}Server running at http://127.0.0.1:8000 (PID: $SERVER_PID)${NC}"
}

# Function to restart server
restart_server() {
  echo -e "${YELLOW}Changes detected in docs/overrides/, restarting server...${NC}"
  if [ ! -z "$SERVER_PID" ]; then
    kill $SERVER_PID 2>/dev/null || true
    sleep 1
  fi
  start_server
}

# Check if fswatch is installed
if ! command -v fswatch &> /dev/null; then
  echo -e "${YELLOW}fswatch is not installed. Installing via Homebrew...${NC}"
  brew install fswatch
fi

# Start initial server
start_server

# Watch for changes and restart
echo -e "${GREEN}Watching docs/overrides/ for changes...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

fswatch -o docs/overrides | while read; do
  restart_server
done
