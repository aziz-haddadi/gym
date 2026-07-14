#!/bin/sh
set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "${project_dir}"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

database="${GYM_DB_NAME:-gym}"
admin_user="${GYM_DB_ADMIN_USER:-gym_admin}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="backups/gym-${timestamp}.dump"

mkdir -p backups
docker compose exec -T db pg_dump \
    --username "${admin_user}" \
    --dbname "${database}" \
    --format custom \
    --compress 9 > "${destination}"
chmod 600 "${destination}"

# Local retention is 30 days. Also copy backups off this VPS.
find backups -type f -name 'gym-*.dump' -mtime +30 -delete
printf 'Backup created: %s\n' "${destination}"
