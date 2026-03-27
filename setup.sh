#!/bin/bash

# ═══════════════════════════════════════════════════════════════
#  PromptX — Interactive Setup Utility
# ═══════════════════════════════════════════════════════════════

set -uo pipefail

# ─── Terminal Colors ──────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

# ─── Gradient Colors for Logo ────────────────────────────────
C1='\033[38;5;51m'
C2='\033[38;5;45m'
C3='\033[38;5;39m'
P1='\033[38;5;135m'
P2='\033[38;5;99m'
P3='\033[38;5;63m'

# ─── Cleanup Trap ────────────────────────────────────────────
cleanup() {
    tput cnorm 2>/dev/null
    echo -e "\n\n  ${YELLOW}⚠  Setup interrupted...${NC}\n"
    jobs -p 2>/dev/null | xargs -r kill 2>/dev/null
    exit 1
}
trap cleanup SIGINT SIGTERM

clear

# ─── Display Logo ────────────────────────────────────────────
display_logo() {
    echo ""
    echo -e "                    ${P1}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${NC}"
    echo -e "               ${P1}▄▄██${P2}████████████████████████${P1}██▄▄${NC}"
    echo -e "            ${P1}▄██${P2}██████████████████████████████${P1}██▄${NC}"
    echo -e "          ${P1}▄██${P2}██████████████████████████████████${P1}██▄${NC}"
    echo -e "        ${P1}▄██${P2}████████${CYAN}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${P2}████████${P1}██▄${NC}"
    echo -e "       ${P1}██${P2}██████${CYAN}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${P2}██████${P1}██${NC}"
    echo -e "      ${P1}██${P2}█████${CYAN}▄▄▄▄▄▄${YELLOW}██████${CYAN}▄▄▄▄${YELLOW}██${CYAN}▄▄▄▄${YELLOW}██████${CYAN}▄▄▄▄▄▄${P2}█████${P1}██${NC}"
    echo -e "     ${P1}██${P2}████${CYAN}▄▄▄▄▄▄▄${YELLOW}██████${CYAN}▄▄▄▄▄▄▄▄▄▄${YELLOW}██████${CYAN}▄▄▄▄▄▄▄${P2}████${P1}██${NC}"
    echo -e "     ${P1}██${P2}████${CYAN}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${P2}████${P1}██${NC}"
    echo -e "     ${P1}██${P2}████${CYAN}▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄${P2}████${P1}██${NC}"
    echo -e "      ${P1}██${P2}████████████████████████████████████████${P1}██${NC}"
    echo -e "       ${P1}██▄${P2}████████████████████████████████████${P1}▄██${NC}"
    echo -e "         ${P1}▀██▄▄${P2}████████████████████████████${P1}▄▄██▀${NC}"
    echo -e "            ${P3}▀▀████████████████████████████▀▀${NC}"
    echo -e "                 ${P3}▀▀██████████████████▀▀${NC}"
    echo -e "                    ${BLUE}███${P2}▄▄▄▄▄▄▄▄${BLUE}███${NC}"
    echo -e "                    ${BLUE}██${P2}██████████${BLUE}██${NC}"
    echo -e "                    ${BLUE}██${P2}██████████${BLUE}██${NC}"
    echo -e "                    ${P2}▀▀${BLUE}██${P3}██████${BLUE}██${P2}▀▀${NC}"
    echo -e "                      ${P3}██${YELLOW}██████${P3}██${NC}"
    echo -e "                     ${P3}██${YELLOW}████████${P3}██${NC}"
    echo -e "                    ${P3}██${YELLOW}██████████${P3}██${NC}"
    echo -e "                   ${P3}██${YELLOW}████${BLUE}██${YELLOW}████${P3}██${NC}"
    echo -e "                  ${P3}██${YELLOW}████${BLUE}██${YELLOW}██████${P3}██${NC}"
    echo -e "                 ${P2}██▀${P3}██${YELLOW}██████████${P3}██${P2}▀██${NC}"
    echo -e "               ${P2}▄██▀${P3}▄██${YELLOW}████████${P3}██▄${P2}▀██▄${NC}"
    echo -e "             ${P2}▄██▀${P3}▄██▀${YELLOW}██████████${P3}▀██▄${P2}▀██▄${NC}"
    echo -e "            ${P2}▀▀${P3}▄██▀${YELLOW}████${BLUE}██${YELLOW}██████${P3}▀██▄${P2}▀▀${NC}"
    echo ""
    echo -e "             ${CYAN}██████╗ ██████╗  ██████╗ ███╗   ███╗██████╗ ████████╗██╗  ██╗${NC}"
    echo -e "             ${CYAN}██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝╚██╗██╔╝${NC}"
    echo -e "             ${BLUE}██████╔╝██████╔╝██║   ██║██╔████╔██║██████╔╝   ██║    ╚███╔╝${NC}"
    echo -e "             ${BLUE}██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔═══╝    ██║    ██╔██╗${NC}"
    echo -e "             ${P2}██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║        ██║   ██╔╝ ██╗${NC}"
    echo -e "             ${P3}╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝${NC}"
    echo ""
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "    ${BOLD}${P1}AI-Powered Prompt Engine Setup${NC}  ${DIM}│${NC}  ${DIM}v1.0.0${NC}  ${DIM}│${NC}  ${DIM}$(date '+%Y-%m-%d %H:%M:%S')${NC}"
    echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# ─── Animated Spinner ────────────────────────────────────────
spinner() {
    local pid=$1
    local msg="${2:-Loading...}"
    local delay=0.08
    local frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
    local i=0

    tput civis
    while ps -p "$pid" > /dev/null 2>&1; do
        printf "\r  ${CYAN}%s${NC}  ${YELLOW}%s${NC}" "${frames[$i]}" "$msg"
        i=$(( (i + 1) % ${#frames[@]} ))
        sleep "$delay"
    done
    printf "   \b\b\b"
    tput cnorm
}

# ─── Step Display Helpers ────────────────────────────────────
step_pass() {
    printf "\r  ${GREEN}✔${NC}  %-52s ${GREEN}[PASS]${NC}\n" "$1"
}

step_fail() {
    printf "\r  ${RED}✘${NC}  %-52s ${RED}[FAIL]${NC}\n" "$1"
}

step_warn() {
    printf "\r  ${YELLOW}⚠${NC}  %-52s ${YELLOW}[WARN]${NC}\n" "$1"
}

step_info() {
    printf "     ${DIM}↳ %s${NC}\n" "$1"
}

# ═══════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════

display_logo
echo -e "  ${BOLD}${BLUE}▶ Starting PromptX Setup Routine...${NC}\n"

# ─── Check Python ────────────────────────────────────────────
(sleep 0.5) &
spinner $! "Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    step_pass "Python ${PYTHON_VERSION} found"
else
    step_fail "Python 3 is not installed"
    exit 1
fi

# ─── Virtual Environment ─────────────────────────────────────
(
    if [ ! -d "venv" ]; then
        python3 -m venv venv
    fi
) &
VPID=$!
spinner $VPID "Configuring virtual environment..."
wait $VPID
if [ -d "venv" ]; then
    step_pass "Virtual environment configured (venv/)"
else
    step_fail "Failed to create virtual environment"
    exit 1
fi

# ─── Dependencies ────────────────────────────────────────────
(
    source venv/bin/activate
    pip install -q --upgrade pip
    pip install -q -r requirements.txt
) &
DPID=$!
spinner $DPID "Installing dependencies (this may take a minute)..."
wait $DPID
if [ $? -eq 0 ]; then
    step_pass "Dependencies installed successfully"
else
    step_fail "Failed to install dependencies"
    exit 1
fi

# ─── Environment Variables ───────────────────────────────────
(sleep 0.4) &
spinner $! "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        step_warn ".env created from template. PLEASE ADD API KEYS."
    else
        touch .env
        step_warn ".env created. PLEASE ADD API KEYS."
    fi
else
    step_pass ".env file already exists"
fi

# ─── Test Fallback ───────────────────────────────────────────
(
    source venv/bin/activate
    python3 test_fallback.py > /dev/null 2>&1
) &
TPID=$!
spinner $TPID "Testing API fallback architecture..."
wait $TPID
TRES=$?
if [ $TRES -eq 0 ]; then
    step_pass "Fallback architecture validated"
else
    step_warn "Fallback test failed. Verify API keys in .env"
fi

# ─── Completion ──────────────────────────────────────────────
echo ""
echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}${GREEN}✅ PromptX Setup Complete!${NC}"
echo ""
echo -e "  ${BOLD}${CYAN}🚀 Next Steps:${NC}"
echo -e "  ${DIM}───────────────────────────────────────${NC}"
echo -e "  ${GREEN}1.${NC}  Open the ${BOLD}.env${NC} file and verify your API keys."
echo -e "  ${GREEN}2.${NC}  Run ${BOLD}./start.sh${NC} to spin up the local AI server."
echo -e "  ${GREEN}3.${NC}  Have fun prompt engineering! 🎨"
echo ""
echo -e "  ${DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
