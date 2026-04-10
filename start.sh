#!/bin/bash
# =============================================
#  ReviewInsight — Start Script
#  Starts backend, frontend, and ngrok tunnels
# =============================================

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}"
echo "╔═══════════════════════════════════════════╗"
echo "║       ReviewInsight — Starting Up         ║"
echo "╚═══════════════════════════════════════════╝"
echo -e "${NC}"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Shutting down services...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    kill $NGROK_PID 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ─── Check prerequisites ───────────────────────
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed.${NC}"
    # exit 1
fi
echo -e "  ${GREEN}✓${NC} Python3 found"

# Check Node.js
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed.${NC}"
    # exit 1
fi
echo -e "  ${GREEN}✓${NC} Node.js found"

# Check ngrok (optional)
NGROK_AVAILABLE=false
if command -v ngrok &> /dev/null; then
    NGROK_AVAILABLE=true
    echo -e "  ${GREEN}✓${NC} ngrok found"
else
    echo -e "  ${YELLOW}⚠${NC} ngrok not found — install with: brew install ngrok"
    echo -e "     (You can still run locally without ngrok)"
fi

# ─── Install backend dependencies ──────────────
echo -e "\n${YELLOW}Installing backend dependencies...${NC}"
cd "$SCRIPT_DIR/backend"

if [ ! -d "venv" ]; then
    echo -e "  Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt
echo -e "  ${GREEN}✓${NC} Backend dependencies installed"

# ─── Install frontend dependencies ─────────────
echo -e "\n${YELLOW}Checking frontend dependencies...${NC}"
cd "$SCRIPT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo -e "  Installing npm packages..."
    npm install
fi
echo -e "  ${GREEN}✓${NC} Frontend dependencies ready"

# ─── Start Backend ─────────────────────────────
echo -e "\n${YELLOW}Starting backend server on port 8000...${NC}"
cd "$SCRIPT_DIR/backend"
source venv/bin/activate
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
sleep 2
echo -e "  ${GREEN}✓${NC} Backend running (PID: $BACKEND_PID)"

# ─── Start Frontend ────────────────────────────
echo -e "${YELLOW}Starting frontend on port 3000...${NC}"
cd "$SCRIPT_DIR/frontend"
npm run dev -- --port 3000 &
FRONTEND_PID=$!
sleep 3
echo -e "  ${GREEN}✓${NC} Frontend running (PID: $FRONTEND_PID)"

# ─── Start ngrok ───────────────────────────────
if [ "$NGROK_AVAILABLE" = true ]; then
    echo -e "\n${YELLOW}Starting ngrok tunnels...${NC}"
    
    # Start ngrok for frontend
    ngrok http 3000 --log=stdout > /tmp/ngrok_frontend.log 2>&1 &
    NGROK_PID=$!
    sleep 3

    # Extract the public URL
    NGROK_URL=$(curl -s http://127.0.0.1:4040/api/tunnels 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for tunnel in data.get('tunnels', []):
        if 'https' in tunnel.get('public_url', ''):
            print(tunnel['public_url'])
            break
except:
    pass
" 2>/dev/null)

    if [ -n "$NGROK_URL" ]; then
        echo -e "\n${GREEN}${BOLD}═══════════════════════════════════════════════${NC}"
        echo -e "${GREEN}${BOLD}  🌐 Your PUBLIC URL: ${NGROK_URL}${NC}"
        echo -e "${GREEN}${BOLD}═══════════════════════════════════════════════${NC}"
    else
        echo -e "  ${YELLOW}⚠${NC} Could not extract ngrok URL. Check http://127.0.0.1:4040"
    fi
fi

echo -e "\n${BLUE}${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${BLUE}  📡 Local Backend:   http://localhost:8000${NC}"
echo -e "${BLUE}  🖥️  Local Frontend:  http://localhost:3000${NC}"
echo -e "${BLUE}  📚 API Docs:        http://localhost:8000/docs${NC}"
if [ "$NGROK_AVAILABLE" = true ] && [ -n "$NGROK_URL" ]; then
echo -e "${GREEN}  🌐 Public URL:      ${NGROK_URL}${NC}"
fi
echo -e "${BLUE}${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop all services.${NC}\n"

# Wait for processes
wait
