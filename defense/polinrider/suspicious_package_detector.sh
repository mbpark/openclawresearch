#!/bin/bash
# PolinRider Suspicious Package Detector
# Scans npm/Packagist/Go packages for malicious indicators

set -e

# Configuration
SCAN_DEPTH=3
ALERT_LOG="/Users/mitchparker/.openclaw/workspace/polinrider_alerts.log"
REPORT_DIR="/Users/mitchparker/.openclaw/workspace/reports/polinrider"
TIMEOUT=30

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Malicious indicators
declare -a MALICIOUS_INDICATORS=(
    "eval("
    "exec("
    "system("
    "require('net')"
    "require('child_process')"
    "dns.resolve("
    "wget "
    "curl "
    "nc -"
    "bash -i"
    "python -c"
    "chmod +x"
    "rm -rf"
    "sudo "
)

# Function to log alerts
log_alert() {
    local severity=$1
    local message=$2
    local timestamp=$(date -Iseconds)
    echo "[$timestamp] [$severity] $message" >> "$ALERT_LOG"
    
    case $severity in
        "CRITICAL") echo -e "${RED}[$severity]${NC} $message" ;;
        "HIGH") echo -e "${YELLOW}[$severity]${NC} $message" ;;
        "MEDIUM") echo -e "${GREEN}[$severity]${NC} $message" ;;
        *) echo "[$severity] $message" ;;
    esac
}

# Function to check package.json for suspicious scripts
check_package_json() {
    local package_path=$1
    local package_name=$(basename $package_path)
    
    if [[ -f "$package_path/package.json" ]]; then
        # Check for suspicious scripts
        if grep -q '"preinstall\|"postinstall\|"prepare"' "$package_path/package.json"; then
            # Extract scripts and check for malicious content
            while IFS= read -r line; do
                for indicator in "${MALICIOUS_INDICATORS[@]}"; do
                    if echo "$line" | grep -q "$indicator"; then
                        log_alert "CRITICAL" "Malicious script in $package_name: $indicator"
                        return 1
                    fi
                done
            done < <(grep -E '"(pre|post|prepare|install|build|test|start)"' "$package_path/package.json")
        fi
        
        # Check for suspicious dependencies
        if grep -q '"registry"' "$package_path/package.json"; then
            log_alert "HIGH" "Custom registry specified in $package_name"
        fi
        
        # Check for unusual package size
        local size=$(du -sb "$package_path" | cut -f1)
        if [[ $size -gt 100000000 ]]; then
            log_alert "MEDIUM" "Unusually large package: $package_name ($size bytes)"
        fi
        
        # Check for recent updates (potential new compromise)
        local last_modified=$(stat -f "%Sm" -t "%Y-%m-%d" "$package_path/package.json" 2>/dev/null || stat -c "%Y" "$package_path/package.json" 2>/dev/null)
        if [[ -n "$last_modified" ]]; then
            local days_old=$(($(date +%s) - $(date -d "$last_modified" +%s) / 86400))
            if [[ $days_old -lt 7 ]]; then
                log_alert "MEDIUM" "Recently modified package: $package_name ($days_old days old)"
            fi
        fi
    fi
}

# Function to scan npm packages
scan_npm_packages() {
    local scan_dir=$1
    log_alert "HIGH" "Scanning npm packages in $scan_dir"
    
    find "$scan_dir" -name "node_modules" -type d 2>/dev/null | while read node_modules; do
        find "$node_modules" -maxdepth $SCAN_DEPTH -name "package.json" -type f 2>/dev/null | while read pkg_json; do
            check_package_json "$(dirname $pkg_json)"
        done
    done
}

# Function to scan Go packages
scan_go_packages() {
    local scan_dir=$1
    log_alert "HIGH" "Scanning Go packages in $scan_dir"
    
    find "$scan_dir" -name "go.mod" -type f 2>/dev/null | while read go_mod; do
        local pkg_dir=$(dirname "$go_mod")
        log_alert "MEDIUM" "Checking Go module: $pkg_dir"
        
        # Check for suspicious imports
        if grep -r "os/exec" "$pkg_dir" 2>/dev/null | grep -v "test"; then
            log_alert "MEDIUM" "Suspicious exec import in $pkg_dir"
        fi
        
        if grep -r "runtime" "$pkg_dir" 2>/dev/null | grep -v "test"; then
            log_alert "MEDIUM" "Runtime package used in $pkg_dir"
        fi
    done
}

# Function to scan Packagist packages
scan_packagist_packages() {
    local scan_dir=$1
    log_alert "HIGH" "Scanning Packagist packages in $scan_dir"
    
    find "$scan_dir" -name "composer.json" -type f 2>/dev/null | while read composer_json; do
        local pkg_dir=$(dirname "$composer_json")
        log_alert "MEDIUM" "Checking Packagist package: $pkg_dir"
        
        # Check for suspicious scripts
        if grep -q '"script"' "$composer_json"; then
            if grep -E "system|exec|shell" "$composer_json"; then
                log_alert "CRITICAL" "Suspicious script in Packagist package: $pkg_dir"
            fi
        fi
    done
}

# Function to run npm audit
run_npm_audit() {
    local scan_dir=$1
    log_alert "HIGH" "Running npm audit in $scan_dir"
    
    npm audit --json 2>/dev/null | jq '.audit' > "${REPORT_DIR}/npm_audit_results.json"
    
    local vulnerability_count=$(jq '.vulnerabilities | length' "${REPORT_DIR}/npm_audit_results.json")
    log_alert "MEDIUM" "Found $vulnerability_count npm vulnerabilities"
}

# Function to run go mod verify
run_go_verify() {
    local scan_dir=$1
    log_alert "HIGH" "Running go mod verify in $scan_dir"
    
    go mod verify 2>/dev/null || log_alert "HIGH" "Go module verification failed"
}

# Function to generate report
generate_report() {
    local report_file="${REPORT_DIR}/scan_report_$(date +%Y%m%d_%H%M%S).json"
    
    cat > "$report_file" <<EOF
{
    "scan_timestamp": "$(date -Iseconds)",
    "scan_depth": $SCAN_DEPTH,
    "alerts_count": $(wc -l < "$ALERT_LOG" 2>/dev/null || echo 0),
    "report_generated": "$(date -Iseconds)",
    "status": "completed"
}
EOF
    
    log_alert "HIGH" "Scan report generated: $report_file"
}

# Main function
main() {
    local scan_dir="${1:-/Users/mitchparker/.openclaw/workspace}"
    
    # Create report directory
    mkdir -p "$REPORT_DIR"
    
    log_alert "HIGH" "Starting PolinRider package scan"
    log_alert "HIGH" "Scan directory: $scan_dir"
    
    # Perform scans
    scan_npm_packages "$scan_dir"
    scan_go_packages "$scan_dir"
    scan_packagist_packages "$scan_dir"
    
    # Run audit tools
    run_npm_audit "$scan_dir"
    run_go_verify "$scan_dir"
    
    # Generate report
    generate_report
    
    log_alert "HIGH" "PolinRider package scan completed"
}

# Run main function with provided arguments
main "$@"
