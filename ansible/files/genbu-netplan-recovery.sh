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
    # Check 1: any 90-nm-*.yaml file exists but is empty.
    # If no 90-nm-*.yaml files exist at all, this check passes (absence is valid;
    # wlan0 may be configured via a hand-crafted YAML instead).
    while IFS= read -r -d '' f; do
        if [[ ! -s "$f" ]]; then
            log "Corruption detected: $f is empty"
            return 0
        fi
    done < <(find "$NETPLAN_DIR" -maxdepth 1 -name '90-nm-*.yaml' -print0)

    # Check 2: at least one YAML file in /etc/netplan/ must reference wlan0.
    local yaml_files
    mapfile -t yaml_files < <(find "$NETPLAN_DIR" -maxdepth 1 -name '*.yaml' | sort)
    if [[ ${#yaml_files[@]} -eq 0 ]]; then
        log "Corruption detected: no YAML files found in $NETPLAN_DIR"
        return 0
    fi
    if ! grep -rl 'wlan0' "${yaml_files[@]}" 2>/dev/null | grep -q .; then
        log "Corruption detected: no YAML file in $NETPLAN_DIR references wlan0"
        return 0
    fi

    return 1
}

do_backup() {
    mkdir -p "$BACKUP_DIR"
    if ! tar -czf "$BACKUP_FILE" -C /etc netplan; then
        log "ERROR: Failed to create backup at $BACKUP_FILE"
        exit 1
    fi
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
    if ! tar -xzf "$BACKUP_FILE" -C /etc; then
        log "ERROR: Failed to extract backup from $BACKUP_FILE — system may be in a broken state"
        exit 1
    fi
    log "Restored $NETPLAN_DIR from $BACKUP_FILE"

    # Restart NetworkManager to apply the restored configuration
    if ! systemctl restart NetworkManager; then
        log "ERROR: Failed to restart NetworkManager — manual intervention required"
        exit 1
    fi
    log "NetworkManager restarted"
}

# --- Main ---

mkdir -p "$(dirname "$LOG_FILE")"

log "Starting Netplan health check"

if [[ ! -d "$NETPLAN_DIR" ]]; then
    log "WARNING: $NETPLAN_DIR does not exist — attempting restoration from backup"
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
