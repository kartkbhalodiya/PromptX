#!/usr/bin/env bash

# ==============================================================================
# PromptX Backend Runner
# AI-Powered Prompt Engineering Platform
# ==============================================================================

set -euo pipefail
IFS=$'\n\t'

# ==============================================================================
# CONSTANTS & CONFIGURATION
# ==============================================================================

readonly SCRIPT_VERSION="3.0.0"
readonly SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
readonly LOG_DIR="${SCRIPT_DIR}/logs"
readonly LOG_FILE="${LOG_DIR}/promptx-${TIMESTAMP}.log"
readonly ACCESS_LOG="${LOG_DIR}/access.log"
readonly ERROR_LOG="${LOG_DIR}/error.log"
readonly RUNNER_PID_FILE="${SCRIPT_DIR}/.promptx.pid"
readonly SERVER_PID_FILE="${SCRIPT_DIR}/.promptx.gunicorn.pid"
readonly VENV_DIR="${SCRIPT_DIR}/venv"
readonly LOCK_FILE="${SCRIPT_DIR}/.promptx.lock"
readonly MIN_PYTHON_VERSION="3.8"
readonly MIN_PORT=1024
readonly MAX_PORT=65535
readonly MAX_WORKERS=32
readonly SERVER_START_TIMEOUT=30   # seconds to wait for server health check
readonly HEALTH_CHECK_INTERVAL=2   # seconds between health check retries

# ==============================================================================
# COLORS & STYLES
# ==============================================================================

readonly ESC='\033'
readonly RESET="${ESC}[0m"
readonly BOLD="${ESC}[1m"
readonly DIM="${ESC}[2m"
readonly ITALIC="${ESC}[3m"
readonly UNDERLINE="${ESC}[4m"
readonly BLINK="${ESC}[5m"
readonly REVERSE="${ESC}[7m"

# Standard colors
readonly BLACK="${ESC}[30m"
readonly RED="${ESC}[31m"
readonly GREEN="${ESC}[32m"
readonly YELLOW="${ESC}[33m"
readonly BLUE="${ESC}[34m"
readonly MAGENTA="${ESC}[35m"
readonly CYAN="${ESC}[36m"
readonly WHITE="${ESC}[37m"
readonly NC="${RESET}"

# Bright colors
readonly BRIGHT_RED="${ESC}[91m"
readonly BRIGHT_GREEN="${ESC}[92m"
readonly BRIGHT_YELLOW="${ESC}[93m"
readonly BRIGHT_BLUE="${ESC}[94m"
readonly BRIGHT_MAGENTA="${ESC}[95m"
readonly BRIGHT_CYAN="${ESC}[96m"
readonly BRIGHT_WHITE="${ESC}[97m"

# 256-color palette (purple spectrum)
readonly PURPLE="${ESC}[38;5;135m"
readonly LIGHT_PURPLE="${ESC}[38;5;99m"
readonly MEDIUM_PURPLE="${ESC}[38;5;63m"
readonly DEEP_PURPLE="${ESC}[38;5;57m"
readonly VIOLET="${ESC}[38;5;129m"
readonly INDIGO="${ESC}[38;5;69m"
readonly PINK="${ESC}[38;5;213m"
readonly ORANGE="${ESC}[38;5;214m"
readonly GOLD="${ESC}[38;5;220m"
readonly TEAL="${ESC}[38;5;43m"
readonly SKY="${ESC}[38;5;117m"

# Background colors
readonly BG_RED="${ESC}[41m"
readonly BG_GREEN="${ESC}[42m"
readonly BG_YELLOW="${ESC}[43m"
readonly BG_BLUE="${ESC}[44m"
readonly BG_MAGENTA="${ESC}[45m"
readonly BG_CYAN="${ESC}[46m"
readonly BG_WHITE="${ESC}[47m"
readonly BG_DARK="${ESC}[40m"
readonly BG_PURPLE="${ESC}[48;5;57m"

# ==============================================================================
# DEFAULT CONFIGURATION
# ==============================================================================

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-5000}"
WORKERS="${WORKERS:-4}"
ENVIRONMENT="${ENVIRONMENT:-production}"
LOG_LEVEL="${LOG_LEVEL:-info}"
TIMEOUT="${TIMEOUT:-120}"
KEEP_ALIVE="${KEEP_ALIVE:-2}"
MAX_REQUESTS="${MAX_REQUESTS:-1000}"
MAX_REQUESTS_JITTER="${MAX_REQUESTS_JITTER:-100}"
GRACEFUL_TIMEOUT="${GRACEFUL_TIMEOUT:-30}"

# Runtime flags
SKIP_DEPS=false
CHECK_ONLY=false
VERBOSE=false
NO_COLOR=false
NO_ANIMATION=false
FORCE_REINSTALL=false
WATCH_LOGS=false
HEALTH_CHECK=true
DETACH=false

# Internal state tracking
declare -A CHECK_RESULTS=()
STARTUP_TIME=""
SERVER_PID=""

# ==============================================================================
# ERROR CODES
# ==============================================================================

readonly ERR_GENERAL=1
readonly ERR_INTERRUPT=130
readonly ERR_TERM=143
readonly ERR_CLEAN_EXIT=3
readonly ERR_PREREQ=10
readonly ERR_VENV=11
readonly ERR_DEPS=12
readonly ERR_CONFIG=13
readonly ERR_PORT=14
readonly ERR_SERVER=15
readonly ERR_HEALTH=16
readonly ERR_LOCK=17
readonly ERR_PERMISSION=18

# ==============================================================================
# LOGGING SYSTEM
# ==============================================================================

# Initialize log directory
init_logging() {
    if ! mkdir -p "$LOG_DIR" 2>/dev/null; then
        echo "ERROR: Cannot create log directory: ${LOG_DIR}" >&2
        exit ${ERR_PERMISSION}
    fi

    # Rotate logs if too many (keep last 20)
    local log_count
    log_count=$(find "$LOG_DIR" -name "promptx-*.log" 2>/dev/null | wc -l)
    if (( log_count > 20 )); then
        find "$LOG_DIR" -name "promptx-*.log" | \
            sort | head -n $(( log_count - 20 )) | \
            xargs rm -f 2>/dev/null || true
    fi

    # Write log header
    cat >> "$LOG_FILE" << EOF
================================================================================
PromptX Backend Runner v${SCRIPT_VERSION}
Session: ${TIMESTAMP}
User: $(whoami 2>/dev/null || echo "unknown")
Host: $(hostname 2>/dev/null || echo "unknown")
OS: $(uname -s 2>/dev/null || echo "unknown")
================================================================================
EOF
}

# Core log function
_log() {
    local level="$1"
    local message="$2"
    local caller="${3:-}"
    local ts
    ts="$(date '+%Y-%m-%d %H:%M:%S.%3N' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S')"
    local clean_msg
    clean_msg="$(strip_ansi "${message}")"
    printf '[%s] [%-8s] %s%s\n' \
        "$ts" "$level" \
        "${caller:+[${caller}] }" \
        "$clean_msg" >> "$LOG_FILE"
}

# Strip ANSI escape codes for clean log files
strip_ansi() {
    echo -e "$1" | sed 's/\x1b\[[0-9;]*[mGKHF]//g; s/\x1b\[[0-9]*[ABCD]//g'
}

# Logging helpers
log_debug()   { _log "DEBUG"   "$1" "${FUNCNAME[1]:-}"; }
log_info()    { _log "INFO"    "$1" "${FUNCNAME[1]:-}"; }
log_warn()    { _log "WARN"    "$1" "${FUNCNAME[1]:-}"; }
log_error()   { _log "ERROR"   "$1" "${FUNCNAME[1]:-}"; }
log_success() { _log "SUCCESS" "$1" "${FUNCNAME[1]:-}"; }
log_fatal()   { _log "FATAL"   "$1" "${FUNCNAME[1]:-}"; }

# ==============================================================================
# TERMINAL OUTPUT FUNCTIONS
# ==============================================================================

supports_color() {
    [[ "$NO_COLOR" == false ]] &&
    [[ -t 1 ]] &&
    [[ "${TERM:-dumb}" != "dumb" ]] &&
    [[ "${COLORTERM:-}" != "none" ]]
}

supports_unicode() {
    [[ "${LANG:-}" =~ UTF ]] || [[ "${LC_ALL:-}" =~ UTF ]] || \
    [[ "${LC_CTYPE:-}" =~ UTF ]]
}

# Icon helper — falls back to ASCII if no unicode support
icon() {
    local unicode="$1"
    local fallback="${2:-*}"
    if supports_unicode; then
        echo -n "$unicode"
    else
        echo -n "$fallback"
    fi
}

# Conditional color wrapper
c() {
    if supports_color; then
        echo -en "$1"
    fi
}

# Print functions
info()    {
    local msg="$1"
    echo -e "$(c "${BRIGHT_CYAN}")  $(icon ℹ i)$(c "${NC}") ${msg}"
    log_info "$msg"
}

warn()    {
    local msg="$1"
    echo -e "$(c "${BRIGHT_YELLOW}")  $(icon ⚠ !)$(c "${NC}") $(c "${YELLOW}")${msg}$(c "${NC}")"
    log_warn "$msg"
}

error()   {
    local msg="$1"
    echo -e "$(c "${BRIGHT_RED}")  $(icon ✖ X)$(c "${NC}") $(c "${RED}")${msg}$(c "${NC}")" >&2
    log_error "$msg"
}

success() {
    local msg="$1"
    echo -e "$(c "${BRIGHT_GREEN}")  $(icon ✔ +)$(c "${NC}") $(c "${GREEN}")${msg}$(c "${NC}")"
    log_success "$msg"
}

debug_msg() {
    if [[ "$VERBOSE" == true ]]; then
        local msg="$1"
        echo -e "$(c "${DIM}")  $(icon ⚙ ~) [DBG] ${msg}$(c "${NC}")"
        log_debug "$msg"
    fi
}

# Fatal error — display + log + exit
fatal() {
    local msg="$1"
    local code="${2:-${ERR_GENERAL}}"
    echo >&2
    echo -e "$(c "${BG_RED}")$(c "${BRIGHT_WHITE}")$(c "${BOLD}") $(icon ✖ FATAL) FATAL ERROR $(c "${NC}")" >&2
    echo -e "$(c "${RED}")$(c "${BOLD}")  ${msg}$(c "${NC}")" >&2
    echo -e "$(c "${DIM}")  Exit code: ${code}$(c "${NC}")" >&2
    echo -e "$(c "${DIM}")  Log file:  ${LOG_FILE}$(c "${NC}")" >&2
    echo >&2
    log_fatal "${msg} (exit code: ${code})"
    exit "$code"
}

# ==============================================================================
# DIVIDERS & LAYOUT
# ==============================================================================

# Get terminal width safely
term_width() {
    local w
    w=$(tput cols 2>/dev/null || echo 80)
    # Clamp between 60 and 120
    (( w < 60 )) && w=60
    (( w > 120 )) && w=120
    echo "$w"
}

print_divider() {
    local style="${1:-single}"
    local width
    width=$(term_width)
    case "$style" in
        double) local char="═" ;;
        thick)  local char="━" ;;
        dashed) local char="─" ;;
        dotted) local char="·" ;;
        *)      local char="─" ;;
    esac
    if supports_color; then
        echo -e "${BLUE}$(printf "${char}%.0s" $(seq 1 "$width"))${NC}"
    else
        printf "${char}%.0s" $(seq 1 "$width"); echo
    fi
}

print_section() {
    local title="$1"
    local icon_char="${2:-▸}"
    echo
    print_divider "thick"
    echo -e "  $(c "${BOLD}")$(c "${BRIGHT_WHITE}") ${icon_char} ${title}$(c "${NC}")"
    print_divider "thick"
}

print_subsection() {
    local title="$1"
    echo
    echo -e "$(c "${DIM}")  ── $(c "${NC}")$(c "${CYAN}")${title}$(c "${NC}")$(c "${DIM}") ──$(c "${NC}")"
}

# Center text in terminal
center_text() {
    local text="$1"
    local clean
    clean="$(strip_ansi "${text}")"
    local text_len=${#clean}
    local width
    width=$(term_width)
    local pad=$(( (width - text_len) / 2 ))
    printf "%${pad}s" ""
    echo -e "$text"
}

# ==============================================================================
# ANIMATION FUNCTIONS
# ==============================================================================

# Animated character-by-character text reveal
animated_text() {
    local text="$1"
    local color="${2:-${CYAN}}"
    local delay="${3:-0.025}"

    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        echo -e "${color}${text}${NC}"
        return 0
    fi

    for (( i=0; i<${#text}; i++ )); do
        printf "$(c "${color}")%s$(c "${NC}")" "${text:$i:1}"
        sleep "$delay"
    done
    echo
}

# Spinner while a background process runs
spinner() {
    local pid="$1"
    local message="${2:-Processing...}"
    local color="${3:-${CYAN}}"

    if [[ ! -t 1 ]] || [[ "$NO_ANIMATION" == true ]]; then
        while kill -0 "$pid" 2>/dev/null; do
            sleep 0.1
        done
        return 0
    fi

    # Braille spinner frames
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local i=0
    local delay=0.08

    tput civis 2>/dev/null || true   # hide cursor

    while kill -0 "$pid" 2>/dev/null; do
        printf "\r$(c "${color}")  %s$(c "${NC}") %s" \
            "${frames[$i]}" "${message}"
        sleep "$delay"
        i=$(( (i + 1) % ${#frames[@]} ))
    done

    tput cnorm 2>/dev/null || true   # restore cursor
    printf "\r\033[K"
    return 0
}

# Progress bar
progress_bar() {
    local current="$1"
    local total="$2"
    local label="${3:-}"
    local width=40

    if [[ ! -t 1 ]] || [[ "$NO_ANIMATION" == true ]]; then
        return 0
    fi

    local filled=$(( (current * width) / total ))
    local empty=$(( width - filled ))
    local pct=$(( (current * 100) / total ))

    local bar
    bar="$(printf '█%.0s' $(seq 1 "$filled"))$(printf '░%.0s' $(seq 1 "$empty"))"

    printf "\r  $(c "${CYAN}")%s$(c "${NC}") $(c "${DIM}")[$(c "${NC}")$(c "${BRIGHT_GREEN}")%s$(c "${NC}")$(c "${DIM}")] %3d%%$(c "${NC}") %s" \
        "$(icon "⟳" ">")" "$bar" "$pct" "$label"
}

# Flicker/shimmer effect for "server running" banner
flicker_effect() {
    local text="$1"
    local cycles="${2:-6}"
    local colors=("${BRIGHT_GREEN}" "${GREEN}" "${TEAL}" "${BRIGHT_CYAN}" "${CYAN}" "${GREEN}")

    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        echo -e "${BRIGHT_GREEN}${text}${NC}"
        return 0
    fi

    tput civis 2>/dev/null || true

    for (( c=0; c<cycles; c++ )); do
        local col="${colors[$(( c % ${#colors[@]} ))]}"
        printf "\r  %s%s%s" "$(c "${col}")" "${text}" "$(c "${NC}")"
        sleep 0.12
        printf "\r  %s%s%s" "$(c "${DIM}")" "${text}" "$(c "${NC}")"
        sleep 0.06
    done

    printf "\r  %s%s%s\n" "$(c "${BRIGHT_GREEN}")" "${text}" "$(c "${NC}")"
    tput cnorm 2>/dev/null || true
}

# Pulse animation for "live" indicator
pulse_text() {
    local text="$1"
    local count="${2:-4}"

    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        echo -e "  ${BRIGHT_GREEN}● ${text}${NC}"
        return 0
    fi

    tput civis 2>/dev/null || true

    for (( i=0; i<count; i++ )); do
        printf "\r  $(c "${BRIGHT_GREEN}")● $(c "${NC}")%s" "$text"
        sleep 0.5
        printf "\r  $(c "${DIM}")○ $(c "${NC}")%s" "$text"
        sleep 0.5
    done

    printf "\r  $(c "${BRIGHT_GREEN}")● $(c "${NC}")%s\n" "$text"
    tput cnorm 2>/dev/null || true
}

# Matrix-style rain effect (decorative, brief)
matrix_rain() {
    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        return 0
    fi

    local chars="01アイウエオカキクケコサシスセソ"
    local width
    width=$(term_width)
    local lines=4

    tput civis 2>/dev/null || true

    for (( l=0; l<lines; l++ )); do
        local line=""
        for (( w=0; w<width; w++ )); do
            local idx=$(( RANDOM % ${#chars} ))
            line+="${chars:$idx:1}"
        done
        echo -e "$(c "${DIM}")$(c "${GREEN}")${line}$(c "${NC}")"
        sleep 0.05
    done

    tput cnorm 2>/dev/null || true
    # Move cursor back up and clear
    tput cuu "$lines" 2>/dev/null || true
    for (( l=0; l<lines; l++ )); do
        tput el 2>/dev/null || true
        tput cud1 2>/dev/null || true
    done
    tput cuu "$lines" 2>/dev/null || true
}

# Countdown with animated spinner
countdown() {
    local seconds="${1:-3}"
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        echo -e "  $(icon "🚀" ">") Starting in ${seconds}s..."
        sleep "$seconds"
        return 0
    fi

    tput civis 2>/dev/null || true
    echo

    for (( i=seconds; i>0; i-- )); do
        for (( f=0; f<10; f++ )); do
            printf "\r  $(c "${CYAN}")%s$(c "${NC}") $(c "${YELLOW}")Starting in $(c "${NC}")$(c "${BOLD}")$(c "${BRIGHT_WHITE}")%d$(c "${NC}")" \
                "${frames[$f]}" "$i"
            sleep 0.1
        done
    done

    echo -e "\r  $(c "${BRIGHT_GREEN}")$(icon "🚀" ">") $(c "${BOLD}")Launching PromptX Backend!$(c "${NC}")                    "
    tput cnorm 2>/dev/null || true
    sleep 0.3
}

# ==============================================================================
# LOGO & BRANDING
# ==============================================================================

display_logo() {
    if [[ "$NO_ANIMATION" == true ]] || [[ ! -t 1 ]]; then
        echo
        echo "  PromptX Backend Runner v${SCRIPT_VERSION}"
        echo "  AI-Powered Prompt Engineering Platform"
        echo
        return 0
    fi

    # Brief matrix rain before logo (disabled by user request)
    # matrix_rain

    echo
    local logo_lines=(
        "        ${MEDIUM_PURPLE}██████╗ ██████╗  ██████╗ ███╗   ███╗██████╗ ████████╗██╗  ██╗${NC}"
        "        ${MEDIUM_PURPLE}██╔══██╗██╔══██╗██╔═══██╗████╗ ████║██╔══██╗╚══██╔══╝╚██╗██╔╝${NC}"
        "        ${CYAN}██████╔╝██████╔╝██║   ██║██╔████╔██║██████╔╝   ██║    ╚███╔╝${NC}"
        "        ${CYAN}██╔═══╝ ██╔══██╗██║   ██║██║╚██╔╝██║██╔═══╝    ██║    ██╔██╗${NC}"
        "        ${LIGHT_PURPLE}██║     ██║  ██║╚██████╔╝██║ ╚═╝ ██║██║        ██║   ██╔╝ ██╗${NC}"
        "        ${DEEP_PURPLE}╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝     ╚═╝╚═╝        ╚═╝   ╚═╝  ╚═╝${NC}"
    )

    for line in "${logo_lines[@]}"; do
        echo -e "$line"
        sleep 0.07
    done

    echo
    # Animate subtitle
    local subtitle="  $(icon "🚀" ">") PromptX  •  AI-Powered Prompt Engineering Platform  •  v${SCRIPT_VERSION}"
    animated_text "$subtitle" "${PURPLE}" 0.015

    local tech_line="  $(icon ⚡ ~) Flask  •  Gemini  •  NVIDIA  •  HuggingFace  •  Gunicorn"
    animated_text "$tech_line" "${DIM}" 0.012
    echo
}

# ==============================================================================
# SERVER RUNNING BANNER (with flicker effect)
# ==============================================================================

display_server_banner() {
    local host="$1"
    local port="$2"
    local env="$3"
    local workers="$4"
    local lan_ip="$5"

    echo
    print_divider "double"

    # Flicker the "SERVER RUNNING" text
    flicker_effect "$(icon "⚡" ">") SERVER IS RUNNING $(icon "⚡" "<")"
    echo

    # Server info box
    local width
    width=$(term_width)
    local inner_w=$(( width - 4 ))

    echo -e "$(c "${PURPLE}")  ╔$(printf '═%.0s' $(seq 1 $((inner_w))))╗$(c "${NC}")"

    local items=(
        "$(icon "🌐" ">") Local      │ http://localhost:${port}"
        "$(icon "🔗" ">") Network    │ http://${lan_ip}:${port}"
        "$(icon "⚙" ">") Workers    │ ${workers} processes"
        "$(icon "🌍" ">") Env        │ ${env}"
        "$(icon "📁" ">") Logs       │ ${LOG_DIR}/"
        "$(icon "🔑" ">") PID        │ $$"
    )

    for item in "${items[@]}"; do
        local clean_item
        clean_item="$(strip_ansi "${item}")"
        local pad=$(( inner_w - ${#clean_item} - 2 ))
        printf "$(c "${PURPLE}")  ║$(c "${NC}") $(c "${BRIGHT_WHITE}")$(c "${BOLD}")%-*s$(c "${NC}") $(c "${PURPLE}")║$(c "${NC}")\n" \
            "$((inner_w - 1))" "  ${item}"
    done

    echo -e "$(c "${PURPLE}")  ╚$(printf '═%.0s' $(seq 1 $((inner_w))))╝$(c "${NC}")"

    print_divider "double"

    # Pulse "live" indicator
    echo
    pulse_text "$(c "${BOLD}")PromptX Backend is live and accepting connections$(c "${NC}")" 3

    echo
    echo -e "  $(c "${DIM}")Press $(c "${NC}")$(c "${BOLD}")$(c "${YELLOW}")Ctrl+C$(c "${NC}") $(c "${DIM}")to stop the server gracefully$(c "${NC}")"
    echo
}

# ==============================================================================
# VALIDATION
# ==============================================================================

validate_port() {
    local port="$1"
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        fatal "Invalid port '${port}': must be a number." "$ERR_CONFIG"
    fi
    if (( port < MIN_PORT || port > MAX_PORT )); then
        fatal "Port ${port} out of range [${MIN_PORT}–${MAX_PORT}]." "$ERR_CONFIG"
    fi
    debug_msg "Port ${port} validated"
}

validate_workers() {
    local workers="$1"
    if ! [[ "$workers" =~ ^[0-9]+$ ]]; then
        fatal "Invalid workers '${workers}': must be a positive integer." "$ERR_CONFIG"
    fi
    if (( workers < 1 || workers > MAX_WORKERS )); then
        fatal "Workers ${workers} out of range [1–${MAX_WORKERS}]." "$ERR_CONFIG"
    fi
    debug_msg "Worker count ${workers} validated"
}

validate_host() {
    local host="$1"
    if ! [[ "$host" =~ ^[a-zA-Z0-9._:-]+$ ]]; then
        fatal "Invalid host '${host}'." "$ERR_CONFIG"
    fi
    debug_msg "Host ${host} validated"
}

validate_environment() {
    local env="$1"
    case "$env" in
        production|development|staging|testing) ;;
        *) fatal "Invalid environment '${env}'. Valid: production, development, staging, testing." "$ERR_CONFIG" ;;
    esac
}

validate_log_level() {
    local level="$1"
    case "$level" in
        debug|info|warning|error|critical) ;;
        *) fatal "Invalid log level '${level}'. Valid: debug, info, warning, error, critical." "$ERR_CONFIG" ;;
    esac
}

validate_timeout() {
    local t="$1"
    if ! [[ "$t" =~ ^[0-9]+$ ]] || (( t < 1 || t > 3600 )); then
        fatal "Invalid timeout '${t}'. Must be 1–3600 seconds." "$ERR_CONFIG"
    fi
}

validate_all_config() {
    debug_msg "Validating all configuration parameters..."
    validate_port        "$PORT"
    validate_workers     "$WORKERS"
    validate_host        "$HOST"
    validate_environment "$ENVIRONMENT"
    validate_log_level   "$LOG_LEVEL"
    validate_timeout     "$TIMEOUT"
    debug_msg "All config parameters validated"
}

# ==============================================================================
# VERSION COMPARISON
# ==============================================================================

version_gte() {
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

version_lt() {
    ! version_gte "$1" "$2"
}

# ==============================================================================
# SYSTEM CHECKS
# ==============================================================================

# Check if a command exists
cmd_exists() {
    command -v "$1" &>/dev/null
}

# Get the process using a port
port_process() {
    local port="$1"
    if cmd_exists ss; then
        ss -tlnp 2>/dev/null | grep ":${port} " | \
            grep -oP 'pid=\K[0-9]+' | head -1 || true
    elif cmd_exists lsof; then
        lsof -ti ":${port}" 2>/dev/null | head -1 || true
    fi
}

check_port_available() {
    local port="$1"
    debug_msg "Checking if port ${port} is available..."

    local pid
    pid=$(port_process "$port")

    if [[ -n "$pid" ]]; then
        local proc_name
        proc_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
        warn "Port ${port} is in use by PID ${pid} (${proc_name})"
        log_warn "Port ${port} conflict: PID=${pid} PROC=${proc_name}"

        echo -e "$(c "${YELLOW}")  Options:$(c "${NC}")"
        echo -e "  $(c "${DIM}")(1) Kill the process: $(c "${NC}")$(c "${WHITE}")kill ${pid}$(c "${NC}")"
        echo -e "  $(c "${DIM}")(2) Use a different port: $(c "${NC}")$(c "${WHITE}")--port XXXX$(c "${NC}")"
        echo

        if [[ -t 0 ]]; then
            read -r -t 10 -p "$(echo -e "  ${YELLOW}Continue anyway? [y/N]:${NC} ")" response || response="n"
            if [[ ! "${response,,}" =~ ^y ]]; then
                fatal "Port ${port} is occupied. Aborting." "$ERR_PORT"
            fi
        else
            fatal "Port ${port} is occupied. Aborting." "$ERR_PORT"
        fi
    else
        debug_msg "Port ${port} is available"
    fi
}

check_disk_space() {
    local min_mb=100
    local available_kb
    available_kb=$(df -k "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
    local available_mb=$(( available_kb / 1024 ))

    if (( available_mb < min_mb )); then
        warn "Low disk space: ${available_mb}MB available (recommend >${min_mb}MB)"
        log_warn "Disk space warning: ${available_mb}MB available"
    else
        debug_msg "Disk space OK: ${available_mb}MB available"
    fi
}

check_memory() {
    local min_mb=256
    local available_mb=9999  # safe default if we can't read

    if [[ -f /proc/meminfo ]]; then
        local avail_kb
        avail_kb=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
        available_mb=$(( avail_kb / 1024 ))
    elif cmd_exists vm_stat; then
        # macOS
        local pages_free
        pages_free=$(vm_stat 2>/dev/null | awk '/Pages free/ {gsub(/\./,""); print $3}' || echo "0")
        available_mb=$(( pages_free * 4096 / 1024 / 1024 ))
    fi

    if (( available_mb < min_mb )); then
        warn "Low memory: ${available_mb}MB available (recommend >${min_mb}MB)"
        log_warn "Memory warning: ${available_mb}MB available"
    else
        debug_msg "Memory OK: ${available_mb}MB available"
    fi
}

# ==============================================================================
# PREREQUISITES CHECK (with detailed status table)
# ==============================================================================

check_prerequisites() {
    print_section "Prerequisites & Environment" "$(icon "🔍" "[CHECK]")"

    local all_ok=true
    local check_count=0
    local pass_count=0
    local warn_count=0
    local fail_count=0

    # Helper: print check result row
    check_row() {
        local label="$1"
        local status="$2"   # "pass" | "warn" | "fail"
        local detail="$3"
        local icon_ok icon_warn icon_fail

        icon_ok="$(icon "✔" "[OK]")"
        icon_warn="$(icon "⚠" "[WARN]")"
        icon_fail="$(icon "✖" "[FAIL]")"

        (( check_count += 1 ))

        case "$status" in
            pass)
                (( pass_count += 1 ))
                printf "  $(c "${BRIGHT_GREEN}")%s$(c "${NC}") $(c "${WHITE}")%-28s$(c "${NC}") $(c "${GREEN}")%s$(c "${NC}")\n" \
                    "$icon_ok" "$label" "$detail"
                log_info "CHECK PASS: ${label} — ${detail}"
                CHECK_RESULTS["$label"]="PASS"
                ;;
            warn)
                (( warn_count += 1 ))
                printf "  $(c "${YELLOW}")%s$(c "${NC}") $(c "${WHITE}")%-28s$(c "${NC}") $(c "${YELLOW}")%s$(c "${NC}")\n" \
                    "$icon_warn" "$label" "$detail"
                log_warn "CHECK WARN: ${label} — ${detail}"
                CHECK_RESULTS["$label"]="WARN"
                ;;
            fail)
                (( fail_count += 1 ))
                printf "  $(c "${BRIGHT_RED}")%s$(c "${NC}") $(c "${WHITE}")%-28s$(c "${NC}") $(c "${RED}")%s$(c "${NC}")\n" \
                    "$icon_fail" "$label" "$detail"
                log_error "CHECK FAIL: ${label} — ${detail}"
                CHECK_RESULTS["$label"]="FAIL"
                all_ok=false
                ;;
        esac
    }

    print_subsection "System & Runtime"

    # ── Python version ─────────────────────────────────────────────────────
    if cmd_exists python3; then
        local py_ver
        py_ver="$(python3 --version 2>&1 | awk '{print $2}')"
        if version_gte "$py_ver" "$MIN_PYTHON_VERSION"; then
            check_row "Python 3" "pass" "${py_ver}"
        else
            check_row "Python 3" "fail" \
                "${py_ver} found — need >= ${MIN_PYTHON_VERSION}"
        fi
    else
        check_row "Python 3" "fail" "python3 not found in PATH"
    fi

    # ── pip ───────────────────────────────────────────────────────────────
    if cmd_exists pip3; then
        local pip_ver
        pip_ver="$(pip3 --version 2>&1 | awk '{print $2}')"
        check_row "pip3" "pass" "${pip_ver}"
    else
        check_row "pip3" "fail" "pip3 not found in PATH"
    fi

    # ── curl / wget (for health checks) ──────────────────────────────────
    if cmd_exists curl; then
        local curl_ver
        curl_ver="$(curl --version 2>&1 | head -1 | awk '{print $2}')"
        check_row "curl" "pass" "${curl_ver}"
    elif cmd_exists wget; then
        check_row "curl" "warn" "curl not found — wget available (fallback)"
    else
        check_row "curl" "warn" "Neither curl nor wget found — health check disabled"
        HEALTH_CHECK=false
    fi

    # ── Git (optional) ────────────────────────────────────────────────────
    if cmd_exists git; then
        local git_ver
        git_ver="$(git --version 2>&1 | awk '{print $3}')"
        check_row "Git" "pass" "${git_ver}"
    else
        check_row "Git" "warn" "Not installed (optional)"
    fi

    print_subsection "Application Files"

    # ── backend/app.py ────────────────────────────────────────────────────
    if [[ -f "${SCRIPT_DIR}/backend/app.py" ]]; then
        local app_size
        app_size="$(wc -l < "${SCRIPT_DIR}/backend/app.py" 2>/dev/null || echo '?')"
        check_row "backend/app.py" "pass" "${app_size} lines"
    else
        check_row "backend/app.py" "fail" "Not found in ${SCRIPT_DIR}/backend/"
    fi

    # ── requirements.txt ──────────────────────────────────────────────────
    if [[ -f "${SCRIPT_DIR}/backend/requirements.txt" ]]; then
        local req_count
        req_count="$(grep -cE '^[^#[:space:]]' \
            "${SCRIPT_DIR}/backend/requirements.txt" 2>/dev/null || echo '?')"
        check_row "requirements.txt" "pass" "${req_count} packages listed"
    else
        check_row "requirements.txt" "fail" "Not found"
    fi

    # ── .env file ─────────────────────────────────────────────────────────
    if [[ -f "${SCRIPT_DIR}/.env" ]]; then
        local empty_count=0
        local empty_keys
        empty_keys=$(grep -E '^[A-Z_]+=\s*$' "${SCRIPT_DIR}/.env" 2>/dev/null | \
            cut -d= -f1 || true)
        [[ -n "$empty_keys" ]] && empty_count=$(echo "$empty_keys" | wc -l)

        if (( empty_count > 0 )); then
            check_row ".env" "warn" \
                "Found — ${empty_count} empty key(s): $(echo "$empty_keys" | tr '\n' ' ')"
        else
            check_row ".env" "pass" "Found — all keys populated"
        fi
    elif [[ -f "${SCRIPT_DIR}/.env.example" ]]; then
        warn "  Copying .env.example → .env"
        if cp "${SCRIPT_DIR}/.env.example" "${SCRIPT_DIR}/.env" 2>/dev/null; then
            check_row ".env" "warn" "Created from .env.example — update API keys!"
        else
            check_row ".env" "fail" "Failed to copy .env.example"
        fi
    else
        check_row ".env" "fail" "Neither .env nor .env.example found"
    fi

    # ── Virtual environment ────────────────────────────────────────────────
    if [[ -d "$VENV_DIR" ]] && [[ -f "${VENV_DIR}/bin/activate" ]]; then
        local venv_py_ver=""
        venv_py_ver="$("${VENV_DIR}/bin/python3" --version 2>&1 | awk '{print $2}' || echo '?')"
        check_row "Virtual Environment" "pass" "Exists — Python ${venv_py_ver}"
    else
        check_row "Virtual Environment" "warn" \
            "Not found — will be created during install"
    fi

    # ── Gunicorn (production only) ─────────────────────────────────────────
    if [[ "$ENVIRONMENT" != "development" ]]; then
        if [[ -f "${VENV_DIR}/bin/gunicorn" ]]; then
            local guni_ver
            guni_ver="$("${VENV_DIR}/bin/gunicorn" --version 2>&1 | awk '{print $NF}')"
            check_row "Gunicorn" "pass" "${guni_ver} (venv)"
        elif cmd_exists gunicorn; then
            local guni_ver
            guni_ver="$(gunicorn --version 2>&1 | awk '{print $NF}')"
            check_row "Gunicorn" "warn" "${guni_ver} (system, prefer venv)"
        else
            check_row "Gunicorn" "warn" "Not found — will install with deps"
        fi
    fi

    print_subsection "System Resources"

    # ── Disk space ────────────────────────────────────────────────────────
    local avail_kb
    avail_kb=$(df -k "$SCRIPT_DIR" 2>/dev/null | awk 'NR==2{print $4}' || echo "0")
    local avail_mb=$(( avail_kb / 1024 ))
    if (( avail_mb >= 500 )); then
        check_row "Disk Space" "pass" "${avail_mb}MB available"
    elif (( avail_mb >= 100 )); then
        check_row "Disk Space" "warn" "${avail_mb}MB available (low)"
    else
        check_row "Disk Space" "fail" "${avail_mb}MB available (critically low)"
    fi

    # ── Memory ────────────────────────────────────────────────────────────
    local mem_mb=0
    if [[ -f /proc/meminfo ]]; then
        local mem_kb
        mem_kb=$(grep MemAvailable /proc/meminfo 2>/dev/null | awk '{print $2}' || echo "0")
        mem_mb=$(( mem_kb / 1024 ))
    elif cmd_exists vm_stat; then
        local pages
        pages=$(vm_stat 2>/dev/null | awk '/Pages free/{gsub(/\./,"");print $3}' || echo "0")
        mem_mb=$(( pages * 4096 / 1024 / 1024 ))
    fi

    if (( mem_mb > 0 )); then
        if (( mem_mb >= 512 )); then
            check_row "Available Memory" "pass" "${mem_mb}MB"
        elif (( mem_mb >= 256 )); then
            check_row "Available Memory" "warn" "${mem_mb}MB (low)"
        else
            check_row "Available Memory" "fail" "${mem_mb}MB (critically low)"
        fi
    else
        check_row "Available Memory" "warn" "Could not determine"
    fi

    # ── Port availability ─────────────────────────────────────────────────
    local port_pid
    port_pid=$(port_process "$PORT")
    if [[ -z "$port_pid" ]]; then
        check_row "Port ${PORT}" "pass" "Available"
    else
        local proc_name
        proc_name=$(ps -p "$port_pid" -o comm= 2>/dev/null || echo "unknown")
        check_row "Port ${PORT}" "warn" "In use by PID ${port_pid} (${proc_name})"
    fi

    # ── Log directory writable ────────────────────────────────────────────
    if [[ -w "$LOG_DIR" ]]; then
        check_row "Log Directory" "pass" "${LOG_DIR}"
    else
        check_row "Log Directory" "fail" "Not writable: ${LOG_DIR}"
    fi

    # ── Stale PID file ────────────────────────────────────────────────────
    if [[ -f "$RUNNER_PID_FILE" ]]; then
        local stale_pid
        stale_pid=$(cat "$RUNNER_PID_FILE" 2>/dev/null || echo "0")
        if kill -0 "$stale_pid" 2>/dev/null; then
            check_row "PID File" "warn" \
                "Server already running? PID ${stale_pid}"
        else
            check_row "PID File" "warn" \
                "Stale PID file found — will clean up"
            rm -f "$RUNNER_PID_FILE"
        fi
    else
        check_row "PID File" "pass" "Clean"
    fi

    # ── Summary table ─────────────────────────────────────────────────────
    echo
    print_divider "dashed"
    printf "  $(c "${BOLD}")Checks: %d total$(c "${NC}") — " "$check_count"
    printf "$(c "${BRIGHT_GREEN}")%d passed$(c "${NC}") / " "$pass_count"
    printf "$(c "${YELLOW}")%d warnings$(c "${NC}") / " "$warn_count"
    printf "$(c "${BRIGHT_RED}")%d failed$(c "${NC}")\n" "$fail_count"
    print_divider "dashed"

    if [[ "$all_ok" != true ]]; then
        echo
        fatal \
            "Prerequisites failed (${fail_count} error(s)). Fix above issues and retry." \
            "$ERR_PREREQ"
    fi

    if (( warn_count > 0 )); then
        echo
        warn "There are ${warn_count} warning(s) — server may still start."
    fi

    echo
    success "All required prerequisites satisfied"
    log_success "Prerequisites: ${pass_count} pass, ${warn_count} warn, ${fail_count} fail"
}

# ==============================================================================
# DEPENDENCY INSTALLATION
# ==============================================================================

install_dependencies() {
    print_section "Installing Dependencies" "$(icon 📦 [DEPS])"

    # ── Create venv ────────────────────────────────────────────────────────
    if [[ ! -d "$VENV_DIR" ]] || [[ "$FORCE_REINSTALL" == true ]]; then
        [[ "$FORCE_REINSTALL" == true && -d "$VENV_DIR" ]] && {
            info "Removing existing virtual environment (--force-reinstall)..."
            rm -rf "$VENV_DIR"
        }
        echo -ne "  $(c "${CYAN}")$(icon "⠋" ">") Creating virtual environment...$(c "${NC}")"
        if python3 -m venv "$VENV_DIR" >> "$LOG_FILE" 2>&1; then
            printf "\r  $(c "${BRIGHT_GREEN}")$(icon ✔ +)$(c "${NC}") $(c "${GREEN}")Virtual environment created$(c "${NC}") — %s\n" \
                "$VENV_DIR"
        else
            printf "\r  $(c "${RED}")$(icon ✖ X) Failed to create virtual environment$(c "${NC}")\n"
            fatal "venv creation failed. See: ${LOG_FILE}" "$ERR_VENV"
        fi
    else
        info "Virtual environment already exists at ${VENV_DIR}"
    fi

    # ── Activate venv ──────────────────────────────────────────────────────
    # shellcheck source=/dev/null
    source "${VENV_DIR}/bin/activate" || \
        fatal "Cannot activate virtual environment at ${VENV_DIR}" "$ERR_VENV"
    debug_msg "Virtualenv activated: ${VIRTUAL_ENV:-$VENV_DIR}"

    # ── Upgrade pip in background (with spinner) ───────────────────────────
    echo -ne "  $(c "${CYAN}")Upgrading pip...$(c "${NC}")"
    (pip install --upgrade pip --quiet >> "$LOG_FILE" 2>&1) &
    local pip_pid=$!
    spinner "$pip_pid" "Upgrading pip..."
    if wait "$pip_pid"; then
        local new_pip
        new_pip="$(pip --version 2>&1 | awk '{print $2}')"
        printf "\r  $(c "${BRIGHT_GREEN}")$(icon ✔ +)$(c "${NC}") $(c "${GREEN}")pip upgraded to %s$(c "${NC}")\n" "$new_pip"
    else
        printf "\r  $(c "${YELLOW}")$(icon ⚠ !)$(c "${NC}") pip upgrade failed (continuing)\n"
        log_warn "pip upgrade failed"
    fi

    # ── Wheel & setuptools ─────────────────────────────────────────────────
    echo -ne "  $(c "${CYAN}")Updating build tools...$(c "${NC}")"
    (pip install --upgrade wheel setuptools --quiet >> "$LOG_FILE" 2>&1) &
    local bt_pid=$!
    spinner "$bt_pid" "Updating build tools..."
    if wait "$bt_pid"; then
        printf "\r  $(c "${BRIGHT_GREEN}")$(icon ✔ +)$(c "${NC}") $(c "${GREEN}")Build tools updated$(c "${NC}")\n"
    else
        printf "\r  $(c "${YELLOW}")$(icon ⚠ !)$(c "${NC}") Build tools update failed (continuing)\n"
    fi

    # ── Count packages for progress display ────────────────────────────────
    local req_file="${SCRIPT_DIR}/backend/requirements.txt"
    local total_pkgs
    total_pkgs=$(grep -cE '^[^#[:space:]]' "$req_file" 2>/dev/null || echo "1")

    # ── Install packages ───────────────────────────────────────────────────
    echo
    info "Installing ${total_pkgs} package(s) from requirements.txt..."
    echo

    local install_log="${LOG_DIR}/install-${TIMESTAMP}.log"
    local pip_exit=0
    : > "$install_log"

    # Stream progress by parsing pip's output
    if [[ "$VERBOSE" == true ]] || [[ ! -t 1 ]]; then
        if pip install -r "$req_file" \
            --no-warn-script-location 2>&1 | tee -a "$LOG_FILE" "$install_log"; then
            pip_exit=0
        else
            pip_exit="${PIPESTATUS[0]}"
        fi
    else
        # Show progress bar (approximate based on package count)
        local installed=0
        local pip_status_file
        pip_status_file="$(mktemp "${TMPDIR:-/tmp}/promptx-pip-status.XXXXXX")"
        while IFS= read -r line; do
            printf '%s\n' "$line" >> "$LOG_FILE"
            printf '%s\n' "$line" >> "$install_log"
            if [[ "$line" =~ ^(Collecting|Downloading|Installing) ]]; then
                (( installed += 1 )) || true
                progress_bar "$installed" "$total_pkgs" \
                    "$(printf '%.40s' "$line")..."
            fi
        done < <(
            set +e
            pip install -r "$req_file" \
                --no-warn-script-location 2>&1
            printf '%s\n' "$?" > "$pip_status_file"
        )
        pip_exit="$(cat "$pip_status_file" 2>/dev/null || echo 1)"
        rm -f "$pip_status_file"
        echo  # newline after progress bar
    fi

    if [[ "${pip_exit:-0}" -ne 0 ]]; then
        echo
        error "Package installation failed"
        echo -e "  $(c "${DIM}")See install log: ${install_log}$(c "${NC}")"
        fatal "Failed to install dependencies." "$ERR_DEPS"
    fi

    echo
    success "All packages installed successfully"

    # ── Verify critical packages ───────────────────────────────────────────
    print_subsection "Verifying critical packages"

    local critical_pkgs=("flask" "gunicorn")
    local verify_failed=()

    for pkg in "${critical_pkgs[@]}"; do
        if pip show "$pkg" &>/dev/null; then
            local pkg_ver
            pkg_ver="$(pip show "$pkg" 2>/dev/null | awk '/^Version:/{print $2}')"
            printf "  $(c "${BRIGHT_GREEN}")$(icon ✔ +)$(c "${NC}") $(c "${WHITE}")%-20s$(c "${NC}") $(c "${DIM}")%s$(c "${NC}")\n" \
                "$pkg" "$pkg_ver"
            log_info "Verified: ${pkg} ${pkg_ver}"
        else
            printf "  $(c "${BRIGHT_RED}")$(icon ✖ X)$(c "${NC}") $(c "${WHITE}")%-20s$(c "${NC}") $(c "${RED}")MISSING$(c "${NC}")\n" \
                "$pkg"
            verify_failed+=("$pkg")
        fi
    done

    # List optional packages
    local optional_pkgs=("google-generativeai" "transformers" "torch" "openai")
    for pkg in "${optional_pkgs[@]}"; do
        if pip show "$pkg" &>/dev/null; then
            local pkg_ver
            pkg_ver="$(pip show "$pkg" 2>/dev/null | awk '/^Version:/{print $2}')"
            printf "  $(c "${BRIGHT_GREEN}")$(icon ✔ +)$(c "${NC}") $(c "${DIM}")%-20s %s$(c "${NC}")\n" \
                "$pkg" "$pkg_ver"
        else
            printf "  $(c "${DIM}")$(icon · -)$(c "${NC}") $(c "${DIM}")%-20s not installed$(c "${NC}")\n" \
                "$pkg"
        fi
    done

    if [[ ${#verify_failed[@]} -gt 0 ]]; then
        echo
        fatal "Critical packages missing after install: ${verify_failed[*]}" "$ERR_DEPS"
    fi

    echo
    log_success "Dependency installation complete"
}

# ==============================================================================
# DJANGO SETUP & MIGRATE
# ==============================================================================

setup_django() {
    local backend_dir="${SCRIPT_DIR}/backend"

    if [[ ! -f "${backend_dir}/manage.py" ]]; then
        return 0
    fi

    echo
    print_subsection "Django Setup"

    cd "$backend_dir"

    # Run Django migrations
    echo -e "  $(c "${CYAN}")Running Django migrations...$(c "${NC}")"
    if python manage.py migrate --noinput >> "$LOG_FILE" 2>&1; then
        echo -e "  $(c "${BRIGHT_GREEN}")$(icon OK)$(c "${NC}") Database migrated successfully"
    else
        echo -e "  $(c "${BRIGHT_YELLOW}")$(icon WAIT)$(c "${NC}") Migration skipped or failed (check DB connection)"
    fi

    log_info "Django setup complete"
}

# ==============================================================================
# HEALTH CHECK
# ==============================================================================

wait_for_server() {
    local host="$1"
    local port="$2"
    local max_wait="$3"
    local check_url="http://${host}:${port}/health"

    # Use 127.0.0.1 for localhost health check even if binding to 0.0.0.0
    [[ "$host" == "0.0.0.0" ]] && check_url="http://127.0.0.1:${port}/health"

    if [[ "$HEALTH_CHECK" == false ]]; then
        debug_msg "Health check disabled (no curl/wget)"
        return 0
    fi

    info "Waiting for server to become ready (max ${max_wait}s)..."

    local elapsed=0
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local fi=0

    tput civis 2>/dev/null || true

    while (( elapsed < max_wait )); do
        local http_code=0

        if cmd_exists curl; then
            http_code=$(curl -s -o /dev/null -w "%{http_code}" \
                --connect-timeout 2 --max-time 3 \
                "$check_url" 2>/dev/null || echo "0")
        elif cmd_exists wget; then
            wget -q --timeout=3 -O /dev/null "$check_url" 2>/dev/null && \
                http_code=200 || http_code=0
        fi

        if (( http_code >= 200 && http_code < 500 )); then
            tput cnorm 2>/dev/null || true
            printf "\r\033[K"
            success "Server responded with HTTP ${http_code} after ${elapsed}s"
            log_success "Health check passed: HTTP ${http_code} in ${elapsed}s"
            return 0
        fi

        if [[ -t 1 ]] && [[ "$NO_ANIMATION" == false ]]; then
            printf "\r  $(c "${CYAN}")%s$(c "${NC}") Health check... elapsed=%ds url=%s" \
                "${frames[$fi]}" "$elapsed" "$check_url"
            fi=$(( (fi + 1) % ${#frames[@]} ))
        fi

        sleep "$HEALTH_CHECK_INTERVAL"
        (( elapsed += HEALTH_CHECK_INTERVAL ))
    done

    tput cnorm 2>/dev/null || true
    printf "\r\033[K"
    warn "Server health check timed out after ${max_wait}s — server may still be starting"
    log_warn "Health check timeout: ${max_wait}s"
    return 1
}

# ==============================================================================
# CONFIGURATION DISPLAY
# ==============================================================================

display_config() {
    print_section "Server Configuration" "$(icon ⚙ [CONFIG])"

    local env_color
    case "$ENVIRONMENT" in
        production)  env_color="${BRIGHT_RED}"    ;;
        development) env_color="${BRIGHT_GREEN}"  ;;
        staging)     env_color="${BRIGHT_YELLOW}" ;;
        testing)     env_color="${BRIGHT_CYAN}"   ;;
        *)           env_color="${WHITE}"          ;;
    esac

    local env_badge
    case "$ENVIRONMENT" in
        production)  env_badge="$(c "${BG_RED}")$(c "${WHITE}") PRODUCTION $(c "${NC}")"   ;;
        development) env_badge="$(c "${BG_GREEN}")$(c "${BLACK}") DEVELOPMENT $(c "${NC}")" ;;
        staging)     env_badge="$(c "${BG_YELLOW}")$(c "${BLACK}") STAGING $(c "${NC}")"   ;;
        testing)     env_badge="$(c "${BG_CYAN}")$(c "${BLACK}") TESTING $(c "${NC}")"     ;;
        *)           env_badge="${ENVIRONMENT}" ;;
    esac

    echo -e "  $(c "${BOLD}")$(c "${WHITE}")Runtime Settings$(c "${NC}")"
    print_divider "dashed"

    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%s$(c "${NC}")\n"       "Host"        "${HOST}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%s$(c "${NC}")\n"       "Port"        "${PORT}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%s$(c "${NC}")\n"       "Workers"     "${WORKERS}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") %s\n"                                  "Environment" "${env_badge}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%s$(c "${NC}")\n"       "Log Level"   "${LOG_LEVEL}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%ss$(c "${NC}")\n"      "Timeout"     "${TIMEOUT}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${WHITE}")%ss$(c "${NC}")\n"      "Keep-Alive"  "${KEEP_ALIVE}"
    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${DIM}")%s$(c "${NC}")\n"         "Log File"    "${LOG_FILE}"

    print_divider "dashed"
    echo

    # Access URLs
    echo -e "  $(c "${BOLD}")$(c "${WHITE}")Access URLs$(c "${NC}")"
    print_divider "dashed"

    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${BRIGHT_WHITE}")$(c "${UNDERLINE}")http://localhost:%s$(c "${NC}")\n" \
        "Local" "${PORT}"

    if [[ "$HOST" == "0.0.0.0" ]]; then
        local lan_ip=""
        lan_ip=$(hostname -I 2>/dev/null | awk '{print $1}') || \
        lan_ip=$(ipconfig getifaddr en0 2>/dev/null) || \
        lan_ip="your-ip"
        printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${BRIGHT_WHITE}")$(c "${UNDERLINE}")http://%s:%s$(c "${NC}")\n" \
            "Network" "${lan_ip}" "${PORT}"
    fi

    printf "  $(c "${CYAN}")%-16s$(c "${NC}") $(c "${BRIGHT_WHITE}")$(c "${UNDERLINE}")http://%s:%s/health$(c "${NC}")\n" \
        "Health Check" "localhost" "${PORT}"

    print_divider "dashed"
    echo
}

# ==============================================================================
# LOCK FILE MANAGEMENT
# ==============================================================================

acquire_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "0")
        if kill -0 "$lock_pid" 2>/dev/null; then
            fatal \
                "Another instance is already running (PID: ${lock_pid}). Lock: ${LOCK_FILE}" \
                "$ERR_LOCK"
        else
            debug_msg "Removing stale lock file (PID ${lock_pid} no longer exists)"
            rm -f "$LOCK_FILE"
        fi
    fi
    echo $$ > "$LOCK_FILE"
    debug_msg "Lock acquired: ${LOCK_FILE} (PID $$)"
}

release_lock() {
    if [[ -f "$LOCK_FILE" ]]; then
        local lock_pid
        lock_pid=$(cat "$LOCK_FILE" 2>/dev/null || echo "0")
        if [[ "$lock_pid" == "$$" ]]; then
            rm -f "$LOCK_FILE"
            debug_msg "Lock released"
        fi
    fi
}

# ==============================================================================
# PID MANAGEMENT
# ==============================================================================

write_pid() {
    echo $$ > "$RUNNER_PID_FILE"
    debug_msg "PID $$ written to ${RUNNER_PID_FILE}"
}

remove_pid() {
    if [[ -f "$RUNNER_PID_FILE" ]]; then
        local pid
        pid=$(cat "$RUNNER_PID_FILE" 2>/dev/null || echo "0")
        if [[ "$pid" == "$$" ]] || [[ "$pid" == "${SERVER_PID}" ]]; then
            rm -f "$RUNNER_PID_FILE"
            debug_msg "Runner PID file removed"
        fi
    fi

    if [[ -f "$SERVER_PID_FILE" ]]; then
        local server_pid
        server_pid=$(cat "$SERVER_PID_FILE" 2>/dev/null || echo "0")
        if ! kill -0 "$server_pid" 2>/dev/null; then
            rm -f "$SERVER_PID_FILE"
            debug_msg "Server PID file removed"
        elif [[ "$DETACH" != true ]] && [[ "$server_pid" == "${SERVER_PID}" ]]; then
            rm -f "$SERVER_PID_FILE"
            debug_msg "Server PID file removed"
        fi
    fi
}

# ==============================================================================
# CLEANUP & SIGNAL HANDLING
# ==============================================================================

cleanup() {
    local exit_code=$?

    # Restore cursor always
    tput cnorm 2>/dev/null || true

    local clean_exits=( "$ERR_CLEAN_EXIT" "$ERR_INTERRUPT" "$ERR_TERM" 0 )
    local is_clean=false
    for c in "${clean_exits[@]}"; do
        [[ "$exit_code" -eq "$c" ]] && is_clean=true && break
    done

    if [[ "$is_clean" == true ]]; then
        if [[ "$NO_ANIMATION" == false ]] && [[ -t 1 ]]; then
            echo
            print_divider "thick"
            local bye="  $(icon "🛑" ">") Shutting down PromptX Backend gracefully..."
            animated_text "$bye" "${PURPLE}" 0.018
            echo -e "  $(c "${BRIGHT_GREEN}")$(icon "✔" ">") Server terminated safely.$(c "${NC}") Goodbye! $(icon 👋 o/)"
            print_divider "thick"
            echo
        fi
    else
        if (( exit_code != 0 )); then
            echo >&2
            echo -e "$(c "${RED}")$(c "${BOLD}")  $(icon ✖ X) Unexpected exit (code: ${exit_code})$(c "${NC}")" >&2
            echo -e "$(c "${DIM}")  Log: ${LOG_FILE}$(c "${NC}")" >&2
            log_error "Unexpected exit with code: ${exit_code}"
        fi
    fi

    release_lock
    remove_pid
    log_info "Session ended (exit code: ${exit_code})"
}

trap cleanup EXIT

handle_sigint() {
    echo
    log_info "Received SIGINT (Ctrl+C)"
    echo -e "\n$(c "${YELLOW}")  $(icon ⚠ !) Interrupted by user$(c "${NC}")"
    exit "$ERR_INTERRUPT"
}

handle_sigterm() {
    echo
    log_info "Received SIGTERM"
    echo -e "\n$(c "${YELLOW}")  $(icon ⚠ !) Received termination signal$(c "${NC}")"
    exit "$ERR_TERM"
}

handle_sigusr1() {
    # Reload signal — useful for config reloads
    log_info "Received SIGUSR1 — reloading..."
    info "Reload signal received (SIGUSR1)"
}

trap handle_sigint  INT
trap handle_sigterm TERM
trap handle_sigusr1 USR1

# ==============================================================================
# SERVER STARTUP
# ==============================================================================

start_server() {
    # shellcheck source=/dev/null
    if [[ -f "${VENV_DIR}/bin/activate" ]]; then
        source "${VENV_DIR}/bin/activate" || \
            fatal "Cannot activate venv" "$ERR_VENV"
    fi

    export PYTHONPATH="${SCRIPT_DIR}/backend:${PYTHONPATH:-}"
    export PYTHONDONTWRITEBYTECODE=1
    export PYTHONUNBUFFERED=1

    check_port_available "$PORT"
    display_config

    write_pid

    if [[ "$NO_ANIMATION" == false ]] && [[ -t 1 ]]; then
        countdown 3
    fi

    print_divider "double"
    echo

    # Compute LAN IP for banner
    local lan_ip=""
    lan_ip=$(hostname -I 2>/dev/null | awk '{print $1}') || \
    lan_ip=$(ipconfig getifaddr en0 2>/dev/null) || \
    lan_ip="your-ip"

    STARTUP_TIME="$(date '+%Y-%m-%d %H:%M:%S')"
    log_info "Starting server — env=${ENVIRONMENT} host=${HOST} port=${PORT} workers=${WORKERS}"

    # Check if Django manage.py exists
    local use_django=false
    if [[ -f "${SCRIPT_DIR}/backend/manage.py" ]]; then
        use_django=true
    fi

    case "$ENVIRONMENT" in
        # ── Development ──────────────────────────────────────────────────
        development)
            if [[ "$use_django" == true ]]; then
                echo -e "  $(c "${BRIGHT_YELLOW}")$(c "${BOLD}") $(icon 🛠 [DEV]) Development Mode$(c "${NC}")"
                echo -e "  $(c "${DIM}")Django dev server with auto-reload enabled$(c "${NC}")"
                echo
                print_divider

                display_server_banner "$HOST" "$PORT" "$ENVIRONMENT" "1 (Django)" "$lan_ip"

                log_info "Django dev server starting on ${HOST}:${PORT}"

                cd "${SCRIPT_DIR}/backend"
                python manage.py runserver "$HOST:$PORT" &
                SERVER_PID=$!
                log_info "Django PID: ${SERVER_PID}"
            else
                export FLASK_ENV="$ENVIRONMENT"
                export FLASK_APP="backend/app.py"
                export FLASK_DEBUG
                FLASK_DEBUG=$([ "$ENVIRONMENT" = "development" ] && echo "1" || echo "0")

                echo -e "  $(c "${BRIGHT_YELLOW}")$(c "${BOLD}") $(icon 🛠 [DEV]) Development Mode$(c "${NC}")"
                echo -e "  $(c "${DIM}")Flask dev server with auto-reload enabled$(c "${NC}")"
                echo
                print_divider

                display_server_banner "$HOST" "$PORT" "$ENVIRONMENT" "1 (Flask)" "$lan_ip"

                log_info "Flask dev server starting on ${HOST}:${PORT}"

                python3 backend/app.py &
                SERVER_PID=$!
                log_info "Flask PID: ${SERVER_PID}"
            fi

            if ! wait_for_server "$HOST" "$PORT" "$SERVER_START_TIMEOUT"; then
                log_warn "Server health check failed or timed out; continuing to wait on server process"
            fi

            if [[ "$DETACH" == true ]]; then
                success "Server detached in background (PID ${SERVER_PID})"
                info "Use 'tail -f ${ERROR_LOG}' to watch logs."
                return 0
            fi

            info "Server is running in the foreground. Use --detach if you want the shell back immediately."

            # Block until server exits
            wait "$SERVER_PID" || true
            ;;
    esac
}

# ==============================================================================
# HELP
# ==============================================================================

show_help() {
    echo
    echo -e "$(c "${BOLD}")$(c "${BRIGHT_WHITE}")PromptX Backend Runner$(c "${NC}") $(c "${DIM}")v${SCRIPT_VERSION}$(c "${NC}")"
    echo -e "$(c "${DIM}")AI-Powered Prompt Engineering Platform$(c "${NC}")"
    echo
    print_divider "dashed"

    echo -e "\n$(c "${CYAN}")$(c "${BOLD}")Usage:$(c "${NC}")"
    echo -e "  ${SCRIPT_NAME} [OPTIONS]\n"

    echo -e "$(c "${CYAN}")$(c "${BOLD}")Server Options:$(c "${NC}")"
    _help_row "-d, --development"       "Run Flask dev server (hot reload)"
    _help_row "-p, --port PORT"         "Bind port [${MIN_PORT}–${MAX_PORT}] (default: 5000)"
    _help_row "-w, --workers N"         "Gunicorn workers [1–${MAX_WORKERS}] (default: 4)"
    _help_row "--host HOST"             "Bind address (default: 0.0.0.0)"
    _help_row "--timeout SECS"          "Worker timeout (default: 120)"
    _help_row "--log-level LEVEL"       "debug|info|warning|error|critical"
    _help_row "--environment ENV"       "production|development|staging|testing"

    echo -e "\n$(c "${CYAN}")$(c "${BOLD}")Installation Options:$(c "${NC}")"
    _help_row "--skip-deps"             "Skip dependency installation"
    _help_row "--force-reinstall"       "Remove venv and reinstall everything"

    echo -e "\n$(c "${CYAN}")$(c "${BOLD}")Output Options:$(c "${NC}")"
    _help_row "--check-only"            "Run prerequisites check then exit"
    _help_row "--detach"                "Start server and return shell after health check"
    _help_row "--no-color"              "Disable all ANSI color codes"
    _help_row "--no-animation"          "Disable animations (CI/CD friendly)"
    _help_row "--watch-logs"            "Tail server logs after startup"
    _help_row "-v, --verbose"           "Enable debug output"
    _help_row "-h, --help"              "Show this help message"
    _help_row "--version"               "Print version and exit"

    echo -e "\n$(c "${CYAN}")$(c "${BOLD}")Environment Variables:$(c "${NC}")"
    _env_row "HOST"          "Bind host"
    _env_row "PORT"          "Bind port"
    _env_row "WORKERS"       "Gunicorn worker count"
    _env_row "ENVIRONMENT"   "Runtime environment"
    _env_row "LOG_LEVEL"     "Logging verbosity"
    _env_row "TIMEOUT"       "Worker timeout seconds"

    echo -e "\n$(c "${CYAN}")$(c "${BOLD}")Examples:$(c "${NC}")"
    echo -e "  $(c "${DIM}")# Production (default)$(c "${NC}")"
    echo -e "  $(c "${WHITE}")${SCRIPT_NAME}$(c "${NC}")"
    echo
    echo -e "  $(c "${DIM}")# Development mode$(c "${NC}")"
    echo -e "  $(c "${WHITE}")${SCRIPT_NAME} -d$(c "${NC}")"
    echo
    echo -e "  $(c "${DIM}")# Custom port, 8 workers$(c "${NC}")"
    echo -e "  $(c "${WHITE}")${SCRIPT_NAME} -p 8080 -w 8$(c "${NC}")"
    echo
    echo -e "  $(c "${DIM}")# CI/CD pipeline$(c "${NC}")"
    echo -e "  $(c "${WHITE}")${SCRIPT_NAME} --no-color --no-animation --skip-deps$(c "${NC}")"
    echo
    echo -e "  $(c "${DIM}")# Check only$(c "${NC}")"
    echo -e "  $(c "${WHITE}")${SCRIPT_NAME} --check-only -v$(c "${NC}")"
    echo
    print_divider "dashed"
    echo
}

_help_row() {
    printf "  $(c "${WHITE}")$(c "${BOLD}")%-32s$(c "${NC}") $(c "${DIM}")%s$(c "${NC}")\n" "$1" "$2"
}

_env_row() {
    printf "  $(c "${YELLOW}")%-20s$(c "${NC}") $(c "${DIM}")%s$(c "${NC}")\n" "$1" "$2"
}

# ==============================================================================
# ARGUMENT PARSING
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                show_help; exit 0 ;;
            --version)
                echo "PromptX Runner v${SCRIPT_VERSION}"; exit 0 ;;
            -d|--development)
                ENVIRONMENT="development"; shift ;;
            -p|--port)
                [[ -z "${2:-}" ]] && fatal "--port requires a value" "$ERR_CONFIG"
                PORT="$2"; shift 2 ;;
            -w|--workers)
                [[ -z "${2:-}" ]] && fatal "--workers requires a value" "$ERR_CONFIG"
                WORKERS="$2"; shift 2 ;;
            --host)
                [[ -z "${2:-}" ]] && fatal "--host requires a value" "$ERR_CONFIG"
                HOST="$2"; shift 2 ;;
            --timeout)
                [[ -z "${2:-}" ]] && fatal "--timeout requires a value" "$ERR_CONFIG"
                TIMEOUT="$2"; shift 2 ;;
            --log-level)
                [[ -z "${2:-}" ]] && fatal "--log-level requires a value" "$ERR_CONFIG"
                LOG_LEVEL="$2"; shift 2 ;;
            --environment)
                [[ -z "${2:-}" ]] && fatal "--environment requires a value" "$ERR_CONFIG"
                ENVIRONMENT="$2"; shift 2 ;;
            --skip-deps)
                SKIP_DEPS=true; shift ;;
            --force-reinstall)
                FORCE_REINSTALL=true; shift ;;
            --check-only)
                CHECK_ONLY=true; shift ;;
            --detach)
                DETACH=true; shift ;;
            --no-color)
                NO_COLOR=true; shift ;;
            --no-animation)
                NO_ANIMATION=true; shift ;;
            --watch-logs)
                WATCH_LOGS=true; shift ;;
            -v|--verbose)
                VERBOSE=true; shift ;;
            --)
                shift; break ;;
            -*)
                error "Unknown option: $1"
                echo -e "  $(c "${DIM}")Run '${SCRIPT_NAME} --help' for usage.$(c "${NC}")"
                exit "$ERR_GENERAL" ;;
            *)
                error "Unexpected argument: $1"
                echo -e "  $(c "${DIM}")Run '${SCRIPT_NAME} --help' for usage.$(c "${NC}")"
                exit "$ERR_GENERAL" ;;
        esac
    done
}

# ==============================================================================
# MAIN
# ==============================================================================

main() {
    # Always init logging first
    init_logging

    parse_args "$@"

    # Validate all config after parsing
    validate_all_config

    log_info "PromptX Runner v${SCRIPT_VERSION} starting"
    log_info "Args: $*"
    log_info "Config: host=${HOST} port=${PORT} workers=${WORKERS} env=${ENVIRONMENT}"

    # Acquire instance lock (prevent double-start)
    acquire_lock

    # Clear screen and show branding
    if [[ "$NO_COLOR" == false ]] && [[ -t 1 ]]; then
        if ! clear 2>/dev/null; then
            log_warn "clear failed; continuing without screen reset"
        fi
    fi

    print_divider "double"
    display_logo
    print_divider "double"

    if [[ "$NO_ANIMATION" == false ]] && [[ -t 1 ]]; then
        animated_text \
            "  $(icon "⟳" ">") Initializing PromptX Backend Services..." \
            "${PURPLE}" 0.018
        sleep 0.2
    fi

    # Prerequisites
    check_prerequisites

    # Check-only mode
    if [[ "$CHECK_ONLY" == true ]]; then
        echo
        success "Check-only mode complete — all prerequisites satisfied."
        log_success "check-only run completed"
        exit 0
    fi

    # Dependencies
    if [[ "$SKIP_DEPS" == false ]]; then
        install_dependencies
    else
        warn "Skipping dependency installation (--skip-deps)"
        log_warn "Dependency installation skipped"
        if [[ -f "${VENV_DIR}/bin/activate" ]]; then
            # shellcheck source=/dev/null
            source "${VENV_DIR}/bin/activate"
            debug_msg "Activated existing venv"
        else
            warn "No virtual environment found — using system Python"
        fi
    fi

    # Django setup (migrate)
    setup_django

    # Start server
    start_server

    # Optional: tail logs after server exits (non-exec path)
    if [[ "$WATCH_LOGS" == true ]] && [[ -f "$ACCESS_LOG" ]]; then
        echo
        info "Watching access log (Ctrl+C to stop):"
        tail -f "$ACCESS_LOG"
    fi
}

main "$@"
