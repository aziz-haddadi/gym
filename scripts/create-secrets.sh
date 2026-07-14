#!/bin/sh
set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
secrets_dir="${project_dir}/secrets"
mkdir -p "${secrets_dir}"
chmod 700 "${secrets_dir}"
umask 077

create_secret() {
    destination="$1"
    if [ -s "${destination}" ]; then
        chmod 644 "${destination}"
        printf 'Keeping existing %s\n' "${destination}"
        return
    fi
    openssl rand -hex 32 > "${destination}"
    chmod 644 "${destination}"
    printf 'Created %s\n' "${destination}"
}

create_secret "${secrets_dir}/postgres_admin_password.txt"
create_secret "${secrets_dir}/postgres_app_password.txt"
create_secret "${secrets_dir}/admin_password.txt"

printf '\nSecrets are ready. They are ignored by Git; do not commit or send them.\n'
