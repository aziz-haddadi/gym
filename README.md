# FORGE — Gym Pulgaa

A private, self-hosted workout tracker for `gym.pulgaa.xyz`. It records machines,
workout days, a date-driven calendar agenda, regular and drop sets, fractional
weights, reps, RPE, notes, volume, personal records, and daily streaks. Reusable
workouts define an exercise order once; each dated session records that day's actual
exercise choices and performance. Rotating workout programs keep the next workout or
rest step due without forcing a weekday schedule.

## Architecture

The code is separated into HTTP routes, validation schemas, application services,
repositories, SQLAlchemy models, and a dependency-free browser interface. Database
changes are versioned with Alembic; the web process never creates tables implicitly.

```text
Browser
  │ HTTPS + Caddy Basic Auth (pulgaa)
  ▼
Caddy ── 127.0.0.1:8013 ── app container
                                  │
                         gym-pulgaa-backend
                                  │
                            PostgreSQL 17
                                  │
                      gym-pulgaa-postgres-data
```

There are two Docker networks:

- `gym-pulgaa-frontend` lets the app publish port `8013` only on VPS loopback.
- `gym-pulgaa-backend` is marked `internal`; PostgreSQL, migrations, and the app use
  it. PostgreSQL has no `ports` entry and is not reachable from the internet.

Caddy performs the browser password challenge and injects the authenticated username
over the localhost-only upstream. The app maps that name to the `pulgaa` account, so
there is no second login screen in the browser interface. Backend session
authentication remains available for automated tests and API development by setting
`GYM_TRUST_PROXY_AUTH=false`.

## Request and data workflow

1. A browser requests `https://gym.pulgaa.xyz`; public DNS resolves it to the VPS.
2. Caddy terminates HTTPS and validates the `pulgaa` Basic Auth credentials.
3. Caddy removes the `Authorization` header and proxies to `127.0.0.1:8013`, sending
   only the trusted `X-Gym-User: pulgaa` identity header.
4. FastAPI maps that identity to the bootstrapped account and serves the static web
   interface. The app port cannot be reached remotely because it is bound to loopback.
5. Browser JavaScript calls same-origin `/api` endpoints for reusable workouts,
   date-filtered sessions, machines, programs, the due cycle step, and statistics.
   There are no third-party browser APIs or CDN dependencies.
6. API routes validate transport data, services enforce ownership and business rules,
   repositories isolate persistence queries, and SQLAlchemy writes to PostgreSQL.
7. A reusable workout stores only its ordered exercises and optional notes. Logging it
   creates a dated session snapshot with that day's actual exercises, regular/drop
   sets, weights, reps, and RPE. The write is transactional: failed validation does
   not leave a partial session.
8. Statistics aggregate the saved workout graph into volume, total sets/reps, weekly
   trends, machine personal records, and current/longest calendar-day streaks.
9. PostgreSQL accepts connections only from the internal Docker network. Its files
   persist in `gym-pulgaa-postgres-data`; compressed logical backups are created by
   `scripts/backup.sh`.

Container startup is ordered: PostgreSQL must pass `pg_isready`, the one-shot Alembic
migration service must exit successfully, and only then does the web application
start. Rebuilding the application does not recreate or delete the named data volume.

Historical session cards still include a repeat action. It copies the historical
session, including its recorded sets, into today while leaving the original unchanged.

## Reusable workouts and dated sessions

The Workouts page has two deliberately separate layers:

- **Saved workouts** contain a name and ordered exercise list only. They never contain
  weights, reps, RPE, or drop-set values.
- **Logged sessions** belong to an Agenda date and store exactly what happened that
  day, including fractional weights such as `27.5`, sets, reps, RPE, and drop sets.

Choosing Log session or a day in Agenda first offers the saved workout library. Its
exercise list is copied into the session form with blank performance fields. Before
saving, any exercise can be replaced, removed, reordered, or supplemented for that
one day. Those edits affect only the dated snapshot; the saved workout remains
unchanged. Editing the saved workout separately affects future copies only and never
rewrites history. Archived saved workouts remain available as historical provenance
but cannot be used to start new sessions.

The Agenda is a monthly calendar backed directly by logged sessions—there is no second
calendar copy of session data. Each session appears automatically on its saved date;
month navigation requests only that month's date range. Selecting a workout opens it
for editing, and selecting a day's plus action opens a new workout with that date
prefilled. On small screens the month becomes a readable vertical day agenda. Machine
sections are grouped by muscle and collapse by default on small screens for faster
navigation.

## Workout programs

A program is an arbitrary ordered cycle of workout and rest steps. It can model a
weekly-looking split such as Arms → Chest + Back → Rest → Legs → Pull → Push → Rest,
but it is not tied to weekdays and can contain any number or order of steps.

- The active program stores the exact due step ID, not only its numeric position.
  Reordering or inserting other steps therefore does not silently change what is due.
- A workout step waits indefinitely until a workout is actually logged. Vacations and
  missed training days never move the pointer.
- Each program has a chosen start date. Before that date its first step is shown as
  scheduled and logging unrelated sessions cannot advance it. Activating or changing
  the start date resets the selected program to step one.
- A workout step can optionally link to a reusable workout. Opening that due step
  copies the linked exercises directly into the session form; they may still be
  changed for that day.
- Logging a session advances the due workout step in the same database transaction as
  the new session. By default any session advances; strict mode requires the linked
  reusable workout identity when present, otherwise every selected muscle group.
- A rest step becomes due immediately and advances only after a calendar day has
  elapsed in the user's timezone. Consecutive elapsed rest steps resolve lazily when
  the due state is read, so no cron job or background worker is required.
- Skip moves to the next step, while Jump here realigns the active cycle to any chosen
  step. Activating a saved program asks for confirmation and resets that program to
  step one.
- Archiving never deletes a program, its steps, or its saved cycle state. Only one
  non-archived program can be active per user, enforced by PostgreSQL as well as the
  service transaction.

The Overview shows the current plan, and Agenda shows it on today or on the configured
future start date. A fresh custom session preselects the first available planned
muscle group without locking the selector. The Programs editor supports linked saved
workouts, drag reordering on desktop, and arrow controls on touch screens.

## VPS deployment

### 1. DNS

Create an `A` record:

```text
gym.pulgaa.xyz  ->  YOUR_VPS_IPV4
```

Add an `AAAA` record only if the VPS has correctly configured public IPv6.

### 2. Prepare the project

```bash
git clone YOUR_PRIVATE_REPOSITORY_URL gym-pulgaa
cd gym-pulgaa
cp .env.example .env
chmod +x scripts/*.sh docker/postgres/init-app-user.sh
./scripts/create-secrets.sh
```

The generated files in `secrets/` are automatically ignored by Git. The initial app
password is deliberately random because Caddy is the production login boundary.
Never commit `.env`, `secrets/`, or database dumps.

The `secrets/` directory is mode `700`, while its files are mode `644` so the
non-root users inside the application and PostgreSQL containers can read their
individual Docker-mounted secrets.

### 3. Start PostgreSQL and the application

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
curl --fail http://127.0.0.1:8013/readyz
```

On the first start, PostgreSQL initializes the database volume and creates a
non-superuser `gym_app` role. The one-shot `migrate` service then applies Alembic
migrations. Only after both succeed does the app start.

Inspect the isolation if desired:

```bash
docker network inspect gym-pulgaa-backend
docker compose exec db psql -U gym_admin -d gym
```

Do **not** add `5432:5432` to Compose. Administration should be performed with
`docker compose exec db ...` or through an SSH tunnel, never by opening PostgreSQL to
the public internet.

### 4. Install the Caddy configuration

The local `deploy/Caddyfile` contains every site block supplied for the VPS plus the
new `gym.pulgaa.xyz` block. It is intentionally ignored by Git because it contains
your real Basic Auth hash. The Git-safe
[`deploy/gym.Caddyfile.example`](deploy/gym.Caddyfile.example) contains only the new
sanitized gym block. The local full configuration uses:

```text
username: pulgaa
password hash: copied exactly from moyenne.pulgaa.xyz
```

On the VPS, merge the block from `deploy/gym.Caddyfile.example` into the existing live
Caddyfile and replace `REPLACE_WITH_CADDY_HASH` with the hash already used by
`moyenne.pulgaa.xyz`. Do not replace your entire VPS configuration with the sanitized
template. Validate before reloading. For a systemd Caddy installation this is typically:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

If Caddy runs in Docker, copy the file to its mounted configuration directory and run
the equivalent validation/reload inside that deployment. Do not reload if validation
fails.

To use a different Basic Auth password later, run `caddy hash-password`, replace only
the hash beside `pulgaa`, validate, and reload Caddy. Never store the plaintext password
in the Caddyfile or Git.

## Backups and restore

Create a compressed PostgreSQL dump:

```bash
./scripts/backup.sh
```

Automate it with the VPS user's crontab, for example at 03:15 UTC:

```cron
15 3 * * * cd /absolute/path/to/gym-pulgaa && ./scripts/backup.sh >> /var/log/gym-backup.log 2>&1
```

The script keeps 30 days locally. A local Docker volume and a dump on the same VPS are
not sufficient disaster recovery: copy encrypted dumps to another machine or object
storage and periodically test restoration.

Restore interactively:

```bash
./scripts/restore.sh backups/gym-YYYYMMDDTHHMMSSZ.dump
```

The restore script stops the app, restores the dump, reapplies migrations, and starts
the app again.

## Operations

```bash
# Logs
docker compose logs -f app db

# Apply a new pulled version
docker compose up -d --build

# Run migrations explicitly
docker compose run --rm migrate

# See database volume and networks
docker volume inspect gym-pulgaa-postgres-data
docker network inspect gym-pulgaa-backend

# Stop without deleting data
docker compose down
```

Never run `docker compose down -v` unless you intentionally want to delete the live
database volume and have verified backups.

Normal upgrades automatically run pending Alembic migrations before the application
starts. They preserve the named PostgreSQL volume; do not delete the volume to deploy
new features.

## Local development and tests

The production configuration expects PostgreSQL and Caddy. Local development supports
Python 3.12 and 3.13; tests use an isolated in-memory SQLite database:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements-test.txt
pytest
ruff check .
```

Or run the same suite in the pinned Python 3.12 container used for production:

```bash
docker build --target test -t gym-pulgaa:test .
docker run --rm gym-pulgaa:test
```

## Streak definition

A workout contributes once per calendar date in the account timezone (`Africa/Tunis`
by default). Consecutive dates build a streak. Yesterday's streak remains current
until today ends, giving you the whole day to train. Multiple workouts on one date do
not inflate the streak.
