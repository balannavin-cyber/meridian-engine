#!/bin/bash
# ==============================================================================
# setup_marketview_aws_host.sh
#
# One-shot bootstrap for the Marketview dashboard on MERDIAN AWS EC2.
# Run via SSM Session Manager on i-0878c118835386ec2 (eu-north-1).
#
# What it does:
#   1. Installs nginx + Node.js 20 + git (idempotent).
#   2. Clones the Marketview repo (operator provides URL via env var).
#   3. Runs npm install + npm run build.
#   4. Installs the nginx server block for marketview at :8080.
#   5. Creates the redeploy script at /home/ssm-user/redeploy_marketview.sh.
#   6. Enables + restarts nginx.
#
# The script does NOT modify the SecurityGroup — that's an AWS console / CLI
# step from your workstation (snippet at the bottom of this file for copy/paste).
#
# Usage (on MERDIAN AWS, via SSM):
#   export MARKETVIEW_REPO_URL="https://github.com/<owner>/<repo>.git"
#   export MARKETVIEW_REPO_BRANCH="main"   # optional, defaults to main
#   bash setup_marketview_aws_host.sh
#
# Per ADR-006 derived-stage convention and Rule 1 (Edit only in Local; AWS
# receives code via git pull, never direct edits).
# ==============================================================================

set -euo pipefail

# --- configurable ------------------------------------------------------------

REPO_URL="${MARKETVIEW_REPO_URL:-}"
REPO_BRANCH="${MARKETVIEW_REPO_BRANCH:-main}"
DEPLOY_DIR="/var/www/marketview"
SRC_DIR="/home/ssm-user/merdian-marketview"
NGINX_SITE="/etc/nginx/sites-available/marketview"
NGINX_LINK="/etc/nginx/sites-enabled/marketview"
LISTEN_PORT="8080"

if [[ -z "${REPO_URL}" ]]; then
    echo "ERROR: MARKETVIEW_REPO_URL env var is required."
    echo "       export MARKETVIEW_REPO_URL=\"https://github.com/<owner>/<repo>.git\""
    exit 1
fi

echo "================================================================"
echo "MERDIAN Marketview — AWS host bootstrap"
echo "  repo:   ${REPO_URL}"
echo "  branch: ${REPO_BRANCH}"
echo "  src:    ${SRC_DIR}"
echo "  deploy: ${DEPLOY_DIR}"
echo "  port:   ${LISTEN_PORT}"
echo "================================================================"

# --- 1. apt deps -------------------------------------------------------------

echo "[1/6] Installing nginx + git + curl ..."
sudo apt-get update -y
sudo apt-get install -y nginx git curl ca-certificates

if ! command -v node >/dev/null 2>&1 || [[ "$(node -v | sed 's/v//' | cut -d. -f1)" -lt 20 ]]; then
    echo "      Installing Node.js 20 via NodeSource ..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "      node version: $(node -v)"
echo "      npm version:  $(npm -v)"
echo "      nginx version: $(nginx -v 2>&1)"

# --- 2. clone or update repo -------------------------------------------------

echo "[2/6] Cloning / updating Marketview repo ..."
if [[ -d "${SRC_DIR}/.git" ]]; then
    cd "${SRC_DIR}"
    git fetch origin
    git checkout "${REPO_BRANCH}"
    git pull --ff-only origin "${REPO_BRANCH}"
else
    rm -rf "${SRC_DIR}"
    git clone --branch "${REPO_BRANCH}" "${REPO_URL}" "${SRC_DIR}"
    cd "${SRC_DIR}"
fi
echo "      head: $(git rev-parse --short HEAD) ($(git log -1 --pretty=%s))"

# --- 3. build ----------------------------------------------------------------

echo "[3/6] Running npm install + build (may take 2-5 minutes) ..."
cd "${SRC_DIR}"
npm install --no-audit --no-fund
npm run build

# Auto-detect build output dir (Vite = dist, CRA = build)
BUILD_OUTPUT=""
for candidate in dist build out; do
    if [[ -d "${SRC_DIR}/${candidate}" ]]; then
        BUILD_OUTPUT="${SRC_DIR}/${candidate}"
        break
    fi
done
if [[ -z "${BUILD_OUTPUT}" ]]; then
    echo "ERROR: could not find build output (looked for dist/, build/, out/)"
    exit 1
fi
echo "      build output: ${BUILD_OUTPUT}"

# --- 4. publish to deploy dir ------------------------------------------------

echo "[4/6] Publishing to ${DEPLOY_DIR} ..."
sudo mkdir -p "${DEPLOY_DIR}"
sudo rsync -a --delete "${BUILD_OUTPUT}/" "${DEPLOY_DIR}/"
sudo chown -R www-data:www-data "${DEPLOY_DIR}"

# --- 5. nginx site -----------------------------------------------------------

echo "[5/6] Installing nginx site ..."

sudo tee "${NGINX_SITE}" >/dev/null <<NGINX_EOF
# MERDIAN Marketview — static SPA served on :${LISTEN_PORT}
# Installed by setup_marketview_aws_host.sh (S39 / ENH-110 Phase 1)

server {
    listen ${LISTEN_PORT} default_server;
    listen [::]:${LISTEN_PORT} default_server;

    server_name _;

    root ${DEPLOY_DIR};
    index index.html;

    # SPA fallback: all unknown paths rewrite to index.html so React Router
    # owns the URL space.
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Long-cache hashed asset bundles (Vite + CRA emit content-hashed names).
    location ~* \\.(?:js|css|woff2?|ttf|svg|png|jpg|jpeg|gif|ico)\$ {
        try_files \$uri =404;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # index.html itself never caches — always fetched fresh so new deploys
    # take effect immediately on next browser reload.
    location = /index.html {
        add_header Cache-Control "no-cache, no-store, must-revalidate";
        expires off;
    }

    # Lightweight health endpoint for the AWS-side smoke probe (separate
    # from Supabase surface probes — confirms nginx is serving and the
    # build is on disk).
    location = /_health {
        default_type application/json;
        return 200 '{"status":"ok","service":"marketview-nginx"}';
    }

    access_log /var/log/nginx/marketview.access.log;
    error_log  /var/log/nginx/marketview.error.log;
}
NGINX_EOF

# Disable Ubuntu default site if it's still listening on :80 — we don't use
# :80 ourselves, but a default-server collision on :8080 would block us.
sudo rm -f /etc/nginx/sites-enabled/default

sudo ln -sf "${NGINX_SITE}" "${NGINX_LINK}"

sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

echo "      nginx reload OK"

# --- 6. redeploy script ------------------------------------------------------

echo "[6/6] Installing redeploy script at /home/ssm-user/redeploy_marketview.sh ..."

cat > /home/ssm-user/redeploy_marketview.sh <<REDEPLOY_EOF
#!/bin/bash
# Rebuild Marketview from current GitHub head and refresh the nginx-served
# directory. Run after every Lovable → GitHub push to take changes live.
set -euo pipefail

SRC_DIR="${SRC_DIR}"
DEPLOY_DIR="${DEPLOY_DIR}"
BRANCH="${REPO_BRANCH}"

cd "\${SRC_DIR}"
git fetch origin
git checkout "\${BRANCH}"
git pull --ff-only origin "\${BRANCH}"

npm install --no-audit --no-fund
npm run build

BUILD_OUTPUT=""
for c in dist build out; do
    if [[ -d "\${SRC_DIR}/\${c}" ]]; then
        BUILD_OUTPUT="\${SRC_DIR}/\${c}"
        break
    fi
done
if [[ -z "\${BUILD_OUTPUT}" ]]; then
    echo "ERROR: no build output found"
    exit 1
fi

sudo rsync -a --delete "\${BUILD_OUTPUT}/" "\${DEPLOY_DIR}/"
sudo chown -R www-data:www-data "\${DEPLOY_DIR}"

# nginx serves static files; no reload required for content changes.
# Index.html cache header is no-cache, so next browser reload picks up the
# new bundle hashes.

echo "Marketview redeployed at \$(date -Is) — head \$(git rev-parse --short HEAD)"
REDEPLOY_EOF

chmod +x /home/ssm-user/redeploy_marketview.sh

echo
echo "================================================================"
echo "BOOTSTRAP COMPLETE"
echo "================================================================"
echo "Marketview is now serving at:"
echo "  http://13.63.27.85:${LISTEN_PORT}/"
echo "  (or whatever Elastic IP is currently attached to this instance)"
echo
echo "Health probe:"
echo "  curl http://13.63.27.85:${LISTEN_PORT}/_health"
echo
echo "Next steps:"
echo "  1. Open SG inbound for TCP ${LISTEN_PORT} (see snippet below)."
echo "  2. Run the smoke probe from your workstation to confirm Supabase"
echo "     RLS triplets are intact:"
echo "       python smoke_probe_marketview_surfaces.py"
echo "  3. After each Lovable → GitHub push, redeploy via:"
echo "       bash /home/ssm-user/redeploy_marketview.sh"
echo
echo "----------------------------------------------------------------"
echo "SECURITY GROUP UPDATE (run from your workstation, AWS CLI):"
echo "----------------------------------------------------------------"
echo "  # Find the SG ID for the MERDIAN instance"
echo "  aws ec2 describe-instances --instance-ids i-0878c118835386ec2 \\"
echo "      --region eu-north-1 \\"
echo "      --query 'Reservations[].Instances[].SecurityGroups[].GroupId' \\"
echo "      --output text"
echo
echo "  # Then authorize inbound TCP 8080:"
echo "  aws ec2 authorize-security-group-ingress \\"
echo "      --group-id <SG_ID> \\"
echo "      --region eu-north-1 \\"
echo "      --protocol tcp --port ${LISTEN_PORT} --cidr 0.0.0.0/0"
echo
echo "  # If you prefer to restrict to your operator IPs only, swap 0.0.0.0/0"
echo "  # for your home WAN /32 (BBNL + Airtel both — multi-rule)."
echo "================================================================"
