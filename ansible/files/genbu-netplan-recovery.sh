#!/usr/bin/env bash
# genbu-netplan-recovery.sh
# Checks Netplan configuration health on boot.
# If healthy: backs up /etc/netplan/ to /var/lib/genbu/netplan-config.tar.gz.
# If corrupted/missing: restores from backup and restarts NetworkManager.
# Logs to /var/log/genbu-netplan-recovery.log and systemd journal.

set -euo pipefail

NETPLAN_DIR="/etc/netplan"
BACKUP_FILE="/var/lib/genbu/netplan-config.tar.gz"
BACKUP_DIR="/var/lib/genbu"
LOG_FILE="/var/log/genbu-netplan-recovery.log"
CORRUPTED_DIR="/etc/netplan.corrupted"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
    echo "$msg" | tee -a "$LOG_FILE"
    # Also send to systemd journal
    echo "$msg" | systemd-cat -t genbu-netplan-recovery -p info
}

is_corrupted() {
    # Check 1: any 90-nm-*.yaml file exists but is empty
    while IFS= read -r -d '' f; do
        if [[ ! -s "$f" ]]; then
            log "Corruption detected: $f is empty"
            return 0
        fi
    done < <(find "$NETPLAN_DIR" -maxdepth 1 -name '90-nm-*.yaml' -print0)

    # Check 2: no YAML file in /etc/netplan/ references wlan0
    local yaml_files
    mapfile -t yaml_files < <(find "$NETPLAN_DIR" -maxdepth 1 -name '*.yaml')
    if [[ ${#yaml_files[@]} -eq 0 ]] || ! grep -rl 'wlan0' "${yaml_files[@]}" &>/dev/null; then
        log "Corruption detected: no YAML file in $NETPLAN_DIR references wlan0"
        return 0
    fi

    return 1
}

do_backup() {
    mkdir -p "$BACKUP_DIR"
    tar -czf "$BACKUP_FILE" -C /etc netplan
    log "Backup written to $BACKUP_FILE"
}

do_restore() {
    if [[ ! -f "$BACKUP_FILE" ]]; then
        log "ERROR: No backup found at $BACKUP_FILE — cannot restore"
        exit 1
    fi

    # Preserve corrupted directory for forensics
    if [[ -d "$NETPLAN_DIR" ]]; then
        local ts
        ts="$(date '+%Y%m%d-%H%M%S')"
        local corrupted_dest="${CORRUPTED_DIR}.${ts}"
        mv "$NETPLAN_DIR" "$corrupted_dest"
        log "Corrupted config moved to $corrupted_dest"
    fi

    # Extract backup
    tar -xzf "$BACKUP_FILE" -C /etc
    log "Restored $NETPLAN_DIR from $BACKUP_FILE"

    # Restart NetworkManager to apply the restored configuration
    systemctl restart NetworkManager
    log "NetworkManager restarted"
}

# --- Main ---

mkdir -p "$(dirname "$LOG_FILE")"

log "Starting Netplan health check"

if [[ ! -d "$NETPLAN_DIR" ]]; then
    log "ERROR: $NETPLAN_DIR does not exist"
    do_restore
else
    if is_corrupted; then
        log "Netplan configuration is corrupted — restoring from backup"
        do_restore
    else
        log "Netplan configuration is healthy — creating backup"
        do_backup
    fi
fi

log "Done"
