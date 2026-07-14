#!/bin/sh
set -eu

app_password="$(cat "${GYM_DB_PASSWORD_FILE}")"

psql --set=ON_ERROR_STOP=1 \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --set=app_user="${GYM_DB_USER}" \
  --set=app_password="${app_password}" <<-'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = :'app_user') \gexec

GRANT CONNECT ON DATABASE :"DBNAME" TO :"app_user";
GRANT USAGE, CREATE ON SCHEMA public TO :"app_user";
SQL

