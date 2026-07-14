#!/bin/sh
set -eu

if [ "$#" -ne 1 ] || [ ! -f "$1" ]; then
    printf 'Usage: %s path/to/gym-backup.dump\n' "$0" >&2
    exit 2
fi

backup_file="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
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

printf 'This replaces the current %s database. Type RESTORE to continue: ' "${database}"
read -r confirmation
[ "${confirmation}" = "RESTORE" ] || { printf 'Cancelled.\n'; exit 1; }

docker compose stop app
trap 'docker compose start app >/dev/null 2>&1 || true' EXIT INT TERM
docker compose exec -T db pg_restore \
    --username "${admin_user}" \
    --dbname "${database}" \
    --clean \
    --if-exists \
    --no-owner < "${backup_file}"
docker compose run --rm migrate
docker compose start app
trap - EXIT INT TERM
printf 'Restore completed from %s\n' "${backup_file}"
