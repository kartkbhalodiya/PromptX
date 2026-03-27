#!/usr/bin/env bash

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
WHITE='\033[1;37m'
NC='\033[0m'

P1='\033[38;5;135m'
P2='\033[38;5;99m'
P3='\033[38;5;63m'

clear

# exact bot image path
BOT_IMAGE="/mnt/data/Pasted image.png"
APP_URL="http://127.0.0.1:5000"

print_divider() {
    echo -e "${P2}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

spinner() {
    local pid=$1
    local delay=0.08
    local spinstr='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    while ps -p "$pid" > /dev/null 2>&1; do
        local first="${spinstr:0:1}"
        spinstr="${spinstr:1}${first}"
        printf " ${CYAN}%s${NC}" "$first"
        sleep "$delay"
        printf "\b\b\b"
    done
    printf "   \b\b\b"
}

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
    echo -e "            ${P1}AI Workspace • Flask • Gemini • NVIDIA • HuggingFace${NC}"
    echo ""
}

print_divider
echo -e "${WHITE}  PromptX System Boot${NC}"
print_divider
echo

display_logo

print_divider
echo -e "${BLUE}▶ Initializing PromptX System...${NC}"

echo -n -e "${YELLOW}Checking environment configuration...${NC}"
(sleep 0.8) &
spinner $!

if [ ! -f .env ]; then
    echo -e "\r${RED}✖ Environment check failed${NC}"
    echo -e "${RED}Error:${NC} .env file not found."
    exit 1
fi
echo -e "\r${GREEN}✔ Environment ready${NC}"
echo

echo -n -e "${YELLOW}Checking Python installation...${NC}"
(sleep 0.6) &
spinner $!

if ! command -v python3 >/dev/null 2>&1; then
    echo -e "\r${RED}✖ Python not found${NC}"
    exit 1
fi
echo -e "\r${GREEN}✔ Python detected${NC}"
echo

echo -n -e "${YELLOW}Installing and verifying dependencies...${NC}"
(pip install -r requirements.txt -q >/dev/null 2>&1) &
spinner $!
echo -e "\r${GREEN}✔ Dependencies verified${NC}"
echo

print_divider
echo -e "${CYAN}🚀 Launching Flask Server...${NC}"
echo -e "${WHITE}   URL:${NC} ${APP_URL}"
print_divider
echo

gunicorn -w 4 -b 0.0.0.0:5000 app:app