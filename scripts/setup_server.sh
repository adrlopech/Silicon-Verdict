#!/usr/bin/env bash
# ==============================================================================
# Setup & Provisioning Script for Ubuntu VPS
# Prepares Docker, Docker Compose, directories and scheduled automation (Cron)
# ==============================================================================

set -euo pipefail

# Ensure script is run with root/sudo privileges
if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Error: This script must be run as root or with sudo." >&2
    exit 1
fi

echo "[*] Step 1: Updating Ubuntu packages..."
apt-get update && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg lsb-release cron

echo "[*] Step 2: Installing Docker Engine & Docker Compose Plugin if absent..."
if ! command -v docker &> /dev/null; then
    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg --yes

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "[+] Docker successfully installed."
else
    echo "[+] Docker is already installed."
fi

# Ensure cron service is active
systemctl enable cron
systemctl start cron

# Determine project deployment path
PROJECT_DIR="${1:-/opt/yt-automation}"
echo "[*] Step 3: Setting up project directory at: ${PROJECT_DIR}"
mkdir -p "${PROJECT_DIR}/tokens"
mkdir -p "${PROJECT_DIR}/logs"

# Ensure topics.txt exists with sample ideas if missing
if [ ! -f "${PROJECT_DIR}/topics.txt" ]; then
    cat << 'EOF' > "${PROJECT_DIR}/topics.txt"
Cómo la Inteligencia Artificial está transformando la Ciberseguridad en 2026
El futuro de la Computación Cuántica y sus riesgos globales
5 Avances Tecnológicos que cambiarán nuestras vidas esta década
EOF
    echo "[+] Created default topics.txt"
fi

echo "[*] Step 4: Configuring Cron Job for automated scheduled runs..."
# Schedule: Every Tuesday and Thursday at 11:00 UTC (0 11 * * 2,4)
CRON_SCHEDULE="0 11 * * 2,4"
CRON_COMMAND="cd ${PROJECT_DIR} && docker compose run --rm yt-runner >> ${PROJECT_DIR}/logs/cron_run.log 2>&1"

# Check if cron job already exists to avoid duplication
CRON_TEMP_FILE=$(mktemp)
crontab -l 2>/dev/null > "$CRON_TEMP_FILE" || true

if grep -Fq "${PROJECT_DIR}" "$CRON_TEMP_FILE"; then
    echo "[+] Cron job already registered."
else
    echo "# Automated YouTube pipeline execution" >> "$CRON_TEMP_FILE"
    echo "${CRON_SCHEDULE} ${CRON_COMMAND}" >> "$CRON_TEMP_FILE"
    crontab "$CRON_TEMP_FILE"
    echo "[+] Successfully added Cron job: [${CRON_SCHEDULE}]"
fi
rm -f "$CRON_TEMP_FILE"

echo "=================================================================="
echo " [✓] Server provisioning completed successfully!"
echo " Project Directory: ${PROJECT_DIR}"
echo " Cron Schedule:     ${CRON_SCHEDULE} (Tue & Thu at 11:00 UTC)"
echo " Remember to place .env and tokens/token.json into ${PROJECT_DIR}"
echo "=================================================================="
