#!/usr/bin/env bash
# ==============================================================================
# EC2 Incident Testing & Resource Stress Generator
# Target: AWS EC2 Linux Instance (Ubuntu / Debian / Amazon Linux)
#
# Generates realistic high-load anomalies (CPU, RAM, Disk, Multi-Resource)
# to trigger anomaly detection, incident correlation, and LangGraph AI analysis.
# ==============================================================================

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# Default stress duration in seconds (3 minutes allows ~6-9 collection cycles at 20-30s intervals)
DEFAULT_DURATION=180
DISK_STRESS_FILE="/var/tmp/disk_stress.img"

# ------------------------------------------------------------------------------
# Auto-detect local Windows environment (Git Bash / MINGW / MSYS / Cygwin)
# If executed locally on Windows, auto-forward to trigger_stress.py over SSH
# ------------------------------------------------------------------------------
UNAME_OUT="$(uname -s 2>/dev/null || echo '')"
if [ -n "$MSYSTEM" ] || [ -n "$WINDIR" ] || [[ "$OSTYPE" == "msys"* ]] || [[ "$OSTYPE" == "cygwin"* ]] || [[ "$UNAME_OUT" == MINGW* ]] || [[ "$UNAME_OUT" == MSYS* ]] || [[ "$UNAME_OUT" == CYGWIN* ]]; then
    echo -e "${YELLOW}[!] Detected local Windows / Git Bash environment.${RESET}"
    echo -e "${CYAN}[*] Auto-forwarding stress scenario to remote EC2 instance via SSH...${RESET}\n"

    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -f "$SCRIPT_DIR/trigger_stress.py" ]; then
        cd "$SCRIPT_DIR" || true
    elif [ -f "$SCRIPT_DIR/../trigger_stress.py" ]; then
        cd "$SCRIPT_DIR/.." || true
    fi

    PYTHON_EXEC=""
    if [ -f "backend/venv/Scripts/python.exe" ]; then
        PYTHON_EXEC="backend/venv/Scripts/python.exe"
    elif [ -f "../backend/venv/Scripts/python.exe" ]; then
        PYTHON_EXEC="../backend/venv/Scripts/python.exe"
    elif command -v python >/dev/null 2>&1; then
        PYTHON_EXEC="python"
    elif command -v python3 >/dev/null 2>&1; then
        PYTHON_EXEC="python3"
    fi

    if [ -n "$PYTHON_EXEC" ]; then
        exec "$PYTHON_EXEC" "trigger_stress.py" "$@"
    else
        echo -e "${RED}[ERROR] Could not find Python environment.${RESET}"
        echo -e "Please run from cmd/powershell: .\\stress.bat $@"
        exit 1
    fi
fi



# ------------------------------------------------------------------------------
# Cleanup handler
# ------------------------------------------------------------------------------
cleanup() {
    echo -e "\n${YELLOW}[!] Cleaning up resources...${RESET}"
    pkill -9 -f stress-ng 2>/dev/null || true
    for f in "$DISK_STRESS_FILE" "/tmp/disk_stress.img" "/var/tmp/disk_stress.img"; do
        if [ -f "$f" ]; then
            echo -e "${YELLOW}[!] Removing temporary disk stress file: $f${RESET}"
            rm -f "$f" 2>/dev/null || true
        fi
    done
    echo -e "${GREEN}[OK] System restored to normal state.${RESET}"
}

# Trap signals for graceful cleanup on Ctrl+C or kill
trap cleanup SIGINT SIGTERM

# ------------------------------------------------------------------------------
# Pre-flight Check: Ensure stress-ng is installed
# ------------------------------------------------------------------------------
ensure_stress_ng() {
    if ! command -v stress-ng >/dev/null 2>&1; then
        echo -e "${YELLOW}[*] 'stress-ng' is not installed. Installing now...${RESET}"
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -qq && sudo apt-get install -y -qq stress-ng
        elif command -v yum >/dev/null 2>&1; then
            sudo yum install -y epel-release 2>/dev/null || true
            sudo yum install -y stress-ng
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y stress-ng
        else
            echo -e "${RED}[ERROR] Package manager not supported. Please install stress-ng manually.${RESET}"
            exit 1
        fi
        echo -e "${GREEN}[OK] stress-ng installed successfully.${RESET}\n"
    fi
}

# ------------------------------------------------------------------------------
# Pre-flight Check: Ensure swapfile exists so SSH doesn't drop during memory stress
# ------------------------------------------------------------------------------
ensure_swap() {
    local swap_total=$(free -m | awk '/^Swap:/ {print $2}')
    if [ "$swap_total" -eq 0 ]; then
        echo -e "${YELLOW}[*] No swap configured. Creating 1GB swapfile so SSH remains connected during memory stress...${RESET}"
        sudo fallocate -l 1G /swapfile 2>/dev/null || sudo dd if=/dev/zero of=/swapfile bs=1M count=1024 status=none
        sudo chmod 600 /swapfile
        sudo mkswap /swapfile >/dev/null 2>&1
        sudo swapon /swapfile >/dev/null 2>&1
        echo -e "${GREEN}[OK] 1GB swapfile active.${RESET}\n"
    fi
}

# ------------------------------------------------------------------------------
# System Overview
# ------------------------------------------------------------------------------
show_system_info() {
    local cpus=$(nproc)
    local mem_total=$(free -h | awk '/^Mem:/ {print $2}')
    local mem_used=$(free -h | awk '/^Mem:/ {print $3}')
    local disk_info=$(df -h / | awk 'NR==2 {print $3 "/" $2 " (" $5 ")"}')

    echo -e "${BOLD}${CYAN}======================================================${RESET}"
    echo -e "${BOLD}${CYAN}   EC2 INCIDENT TESTING & RESOURCE STRESS GENERATOR   ${RESET}"
    echo -e "${BOLD}${CYAN}======================================================${RESET}"
    echo -e " ${BOLD}Host:${RESET}       $(hostname) ($(uname -s) $(uname -r))"
    echo -e " ${BOLD}CPU Cores:${RESET}  $cpus"
    echo -e " ${BOLD}Memory:${RESET}     $mem_used / $mem_total"
    echo -e " ${BOLD}Root Disk:${RESET}  $disk_info"
    echo -e "${CYAN}------------------------------------------------------${RESET}"
}

# ------------------------------------------------------------------------------
# Scenario A: CPU Stress (97% Load)
# ------------------------------------------------------------------------------
run_cpu_stress() {
    local duration="${1:-$DEFAULT_DURATION}"
    local cores=$(nproc)
    ensure_stress_ng
    
    echo -e "\n${BOLD}${RED}>>> SCENARIO A: CPU Saturation (Target: 97%)${RESET}"
    echo -e "  • Sponsoring: ${cores} CPU cores at 97% load for ${duration}s"
    echo -e "  • Backend Anomaly: CPU_CRITICAL (>90% threshold)"
    echo -e "  • Dashboard Action: Watch Live CPU chart rise past 95%!\n"
    
    stress-ng --cpu "$cores" --cpu-load 97 --timeout "${duration}s" --metrics-brief
    echo -e "\n${GREEN}[OK] Scenario A completed.${RESET}"
}

# ------------------------------------------------------------------------------
# Scenario B: Memory / RAM Stress (95%+ Allocation)
# ------------------------------------------------------------------------------
run_ram_stress() {
    local duration="${1:-$DEFAULT_DURATION}"
    ensure_stress_ng
    ensure_swap
    
    echo -e "\n${BOLD}${RED}>>> SCENARIO B: Memory Saturation (Target: 95%+)${RESET}"
    echo -e "  • Allocating: ~95% physical RAM continuously held for ${duration}s"
    echo -e "  • Backend Anomaly: MEMORY_CRITICAL (>90% threshold)"
    echo -e "  • Dashboard Action: Watch Live Memory usage gauge rise to ~95%!\n"
    
    sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true
    stress-ng --vm 1 --vm-bytes 95% --vm-hang "$duration" --timeout "${duration}s" --metrics-brief
    echo -e "\n${GREEN}[OK] Scenario B completed.${RESET}"
}


# ------------------------------------------------------------------------------
# Scenario C: Disk Storage Stress (90%+ Root Partition)
# ------------------------------------------------------------------------------
run_disk_stress() {
    local duration="${1:-$DEFAULT_DURATION}"
    echo -e "\n${BOLD}${RED}>>> SCENARIO C: Disk Storage Saturation (Target: >90%)${RESET}"
    echo -e "  • Root filesystem: /"
    echo -e "  • Backend Anomaly: DISK_WARNING (>80%) or DISK_CRITICAL (>90%)\n"

    # Inspect current disk statistics in KB
    local total_kb=$(df -k / | awk 'NR==2 {print $2}')
    local used_kb=$(df -k / | awk 'NR==2 {print $3}')
    local avail_kb=$(df -k / | awk 'NR==2 {print $4}')

    # Target 92% usage
    local target_used_kb=$(( total_kb * 92 / 100 ))
    local needed_kb=$(( target_used_kb - used_kb ))

    # Keep a safety buffer of at least 250 MB so OS services won't crash
    local safety_buffer_kb=$(( 250 * 1024 ))
    local max_alloc_kb=$(( avail_kb - safety_buffer_kb ))

    if [ "$needed_kb" -le 0 ]; then
        echo -e "${YELLOW}[!] Disk is already at or above 92% capacity (${used_kb}KB used / ${total_kb}KB total).${RESET}"
    else
        if [ "$needed_kb" -gt "$max_alloc_kb" ]; then
            needed_kb=$max_alloc_kb
        fi

        local needed_mb=$(( needed_kb / 1024 ))
        if [ "$needed_mb" -lt 50 ]; then
            needed_mb=50
        fi

        echo -e "${YELLOW}[*] Creating temporary file ${DISK_STRESS_FILE} (${needed_mb} MB) to push disk past 90%...${RESET}"
        if command -v fallocate >/dev/null 2>&1; then
            fallocate -l "${needed_mb}M" "$DISK_STRESS_FILE" 2>/dev/null || dd if=/dev/zero of="$DISK_STRESS_FILE" bs=1M count="$needed_mb" status=none
        else
            dd if=/dev/zero of="$DISK_STRESS_FILE" bs=1M count="$needed_mb" status=none
        fi

        echo -e "${GREEN}[OK] Disk capacity updated:${RESET}"
        df -h /

        echo -e "\n${CYAN}Holding disk saturation for ${duration}s... (Press Ctrl+C to clean up early)${RESET}"
        for ((i=duration; i>0; i--)); do
            echo -ne "\r${YELLOW}Time remaining: ${i}s (Incident will persist after consecutive samples)...${RESET} "
            sleep 1
        done
        echo ""
    fi

    # Cleanup disk file
    if [ -f "$DISK_STRESS_FILE" ]; then
        echo -e "${YELLOW}[*] Removing temporary disk file...${RESET}"
        rm -f "$DISK_STRESS_FILE"
        echo -e "${GREEN}[OK] Free space restored:${RESET}"
        df -h /
    fi
    echo -e "${GREEN}[OK] Scenario C completed.${RESET}"
}

# ------------------------------------------------------------------------------
# Scenario D: Multi-Resource Assessment Incident (CPU 96% + RAM 95%+)
# ------------------------------------------------------------------------------
run_multi_stress() {
    local duration="${1:-$DEFAULT_DURATION}"
    local cores=$(nproc)
    ensure_stress_ng
    ensure_swap
    
    echo -e "\n${BOLD}${MAGENTA}========================================================================${RESET}"
    echo -e "${BOLD}${MAGENTA}  >>> SCENARIO D: ASSESSMENT MULTI-RESOURCE SATURATION (CPU + RAM)  <<<  ${RESET}"
    echo -e "${BOLD}${MAGENTA}========================================================================${RESET}"
    echo -e "  • Sponsoring: ${cores} CPU cores at 96% load + 95%+ RAM concurrently"
    echo -e "  • Duration:   ${duration}s"
    echo -e "  • Pipeline Impact:"
    echo -e "     1. Metric Collector captures concurrent CPU & Memory spikes"
    echo -e "     2. Anomaly Detector flags CPU_CRITICAL & MEMORY_CRITICAL"
    echo -e "     3. Correlation Engine merges them into a Single Multi-Resource Incident"
    echo -e "     4. 8-Node LangGraph AI Workflow with Groq triggers root-cause analysis"
    echo -e "     5. Frontend Dashboard displays AI Diagnosis & Remediation Cards!"
    echo -e "${MAGENTA}------------------------------------------------------------------------${RESET}\n"
    
    sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true
    stress-ng --cpu "$cores" --cpu-load 96 --vm 1 --vm-bytes 95% --vm-hang "$duration" --timeout "${duration}s" --metrics-brief
    echo -e "\n${GREEN}[OK] Scenario D completed! Check frontend dashboard for generated Incident & AI report.${RESET}"
}

# ------------------------------------------------------------------------------
# Scenario E: Triple Saturation (CPU 96% + RAM 95%+ + Disk 90%)
# ------------------------------------------------------------------------------
run_all_stress() {
    local duration="${1:-$DEFAULT_DURATION}"
    local cores=$(nproc)
    ensure_stress_ng
    ensure_swap

    echo -e "\n${BOLD}${RED}>>> SCENARIO E: Triple Saturation (CPU + RAM + Disk Storage)${RESET}\n"
    
    # Temporarily allocate disk space on root filesystem
    local total_kb=$(df -k / | awk 'NR==2 {print $2}')
    local used_kb=$(df -k / | awk 'NR==2 {print $3}')
    local avail_kb=$(df -k / | awk 'NR==2 {print $4}')
    local target_used_kb=$(( total_kb * 92 / 100 ))
    local needed_kb=$(( target_used_kb - used_kb ))
    local safety_buffer_kb=$(( 250 * 1024 ))
    local max_alloc_kb=$(( avail_kb - safety_buffer_kb ))
    
    if [ "$needed_kb" -gt 0 ]; then
        [ "$needed_kb" -gt "$max_alloc_kb" ] && needed_kb=$max_alloc_kb
        local needed_mb=$(( needed_kb / 1024 ))
        if [ "$needed_mb" -gt 50 ]; then
            echo -e "${YELLOW}[*] Allocating ${needed_mb}MB disk file in /var/tmp to saturate root partition past 90%...${RESET}"
            fallocate -l "${needed_mb}M" "$DISK_STRESS_FILE" 2>/dev/null || dd if=/dev/zero of="$DISK_STRESS_FILE" bs=1M count="$needed_mb" status=none
            echo -e "${GREEN}[OK] Disk capacity updated:${RESET}"
            df -h /
        fi
    fi

    # Drop caches for maximum RAM saturation
    sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true

    # Run combined stress-ng (CPU + RAM)
    stress-ng --cpu "$cores" --cpu-load 96 --vm 1 --vm-bytes 95% --vm-hang "$duration" --timeout "${duration}s" --metrics-brief
    
    # Clean up disk
    rm -f "$DISK_STRESS_FILE" 2>/dev/null || true
    echo -e "${GREEN}[OK] Disk space restored:${RESET}"
    df -h /
    echo -e "\n${GREEN}[OK] Scenario E completed.${RESET}"
}



# ------------------------------------------------------------------------------
# Interactive Menu
# ------------------------------------------------------------------------------
show_menu() {
    show_system_info
    echo -e "${BOLD}Select a stress scenario to generate incidents:${RESET}\n"
    echo -e "  ${BOLD}[1]${RESET} ${YELLOW}Scenario A:${RESET} Stress CPU to 97%              (Triggers CPU_CRITICAL)"
    echo -e "  ${BOLD}[2]${RESET} ${YELLOW}Scenario B:${RESET} Stress Memory (RAM) to 92%+    (Triggers MEMORY_CRITICAL)"
    echo -e "  ${BOLD}[3]${RESET} ${YELLOW}Scenario C:${RESET} Stress Root Disk to >90%       (Triggers DISK_CRITICAL)"
    echo -e "  ${BOLD}[4]${RESET} ${MAGENTA}Scenario D:${RESET} Assessment Multi-Resource     (CPU 96% + RAM 91% -> LangGraph AI)"
    echo -e "  ${BOLD}[5]${RESET} ${RED}Scenario E:${RESET} Extreme Triple Saturation      (CPU + RAM + Disk)"
    echo -e "  ${BOLD}[6]${RESET} ${GREEN}Stop Stress:${RESET} Kill stress-ng & clean disk files"
    echo -e "  ${BOLD}[0]${RESET} Exit\n"

    read -rp "Enter choice [0-6] (Default: 4): " choice
    choice=${choice:-4}

    case "$choice" in
        1)
            read -rp "Enter duration in seconds (Default: 180): " dur
            run_cpu_stress "${dur:-$DEFAULT_DURATION}"
            ;;
        2)
            read -rp "Enter duration in seconds (Default: 180): " dur
            run_ram_stress "${dur:-$DEFAULT_DURATION}"
            ;;
        3)
            read -rp "Enter duration in seconds (Default: 180): " dur
            run_disk_stress "${dur:-$DEFAULT_DURATION}"
            ;;
        4)
            read -rp "Enter duration in seconds (Default: 180): " dur
            run_multi_stress "${dur:-$DEFAULT_DURATION}"
            ;;
        5)
            read -rp "Enter duration in seconds (Default: 180): " dur
            run_all_stress "${dur:-$DEFAULT_DURATION}"
            ;;
        6)
            cleanup
            ;;
        0)
            echo "Exiting."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice.${RESET}"
            exit 1
            ;;
    esac
}

# ------------------------------------------------------------------------------
# Command Line Argument Dispatcher
# ------------------------------------------------------------------------------
case "${1:-}" in
    cpu|--cpu|-a)
        run_cpu_stress "${2:-$DEFAULT_DURATION}"
        ;;
    ram|memory|--ram|--memory|-b)
        run_ram_stress "${2:-$DEFAULT_DURATION}"
        ;;
    disk|--disk|-c)
        run_disk_stress "${2:-$DEFAULT_DURATION}"
        ;;
    multi|assessment|--multi|-d)
        run_multi_stress "${2:-$DEFAULT_DURATION}"
        ;;
    all|triple|--all|-e)
        run_all_stress "${2:-$DEFAULT_DURATION}"
        ;;
    stop|clean|cleanup|--stop)
        cleanup
        ;;
    help|--help|-h)
        echo "Usage: $0 [scenario] [duration_seconds]"
        echo ""
        echo "Scenarios:"
        echo "  cpu       Saturate CPU at 97% load"
        echo "  ram       Saturate RAM at 92%+"
        echo "  disk      Saturate Root Disk partition past 90%"
        echo "  multi     Assessment Scenario: CPU 96% + RAM 91% (Triggers AI workflow)"
        echo "  all       Triple saturation: CPU + RAM + Disk"
        echo "  stop      Kill all stress-ng processes and clean up temporary disk files"
        echo ""
        echo "If run without arguments, launches interactive menu."
        ;;
    *)
        show_menu
        ;;
esac
