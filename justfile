# DepositDuck - local development tooling
#
# dotenv defaults to `.env`. For testing run as `just dotenv=.env.test <recipe>`
#
# Some targets check the `CI` variable to modify behaviour
# if being run in a GitHub Actions pipeline.
#
# (c) 2024 Alberto Morón Hernández

dotenv := '.env'

VENV_DIR := ".venv"
REQS_DIR := "requirements"

default:
  @just --list

# create a virtual environment at '.venv/'
venv:
  @test -d {{VENV_DIR}} || uv venv

# Dependency management
# inspiration: https://hynek.me/til/pip-tools-and-pyproject-toml/

# sync project dependencies to virtualenv
install-deps: venv
  @uv pip sync {{REQS_DIR}}/base.txt

install-deps-dev: venv
  @uv pip sync {{REQS_DIR}}/dev.txt

install-deps-test: venv
  @uv pip sync {{REQS_DIR}}/test.txt

# generate requirements files with pinned dependencies
pin-deps:
  @just pin-deps-base
  @just pin-deps-dev
  @just pin-deps-test

pin-deps-base:
  @uv pip compile  {{REQS_DIR}}/base.in -o {{REQS_DIR}}/base.txt

pin-deps-dev:
  @uv pip compile  {{REQS_DIR}}/dev.in -o {{REQS_DIR}}/dev.txt

pin-deps-test:
  @uv pip compile  {{REQS_DIR}}/test.in -o {{REQS_DIR}}/test.txt

# bump dependency versions in line with constraints in requirements/*.in files
update-deps:
  @just update-deps-base
  @just update-deps-dev
  @just update-deps-test
  @just update-pre-commit

update-deps-base:
  @uv pip compile {{REQS_DIR}}/base.in --upgrade -o {{REQS_DIR}}/base.txt

update-deps-dev:
  @uv pip compile {{REQS_DIR}}/dev.in --upgrade -o {{REQS_DIR}}/dev.txt

update-deps-test:
  @uv pip compile {{REQS_DIR}}/test.in --upgrade -o {{REQS_DIR}}/test.txt

update-pre-commit:
  @pre-commit autoupdate

# start a Dockerised instance of PostgreSQL on :5432
_start_db:
  #!/usr/bin/env bash
  set -euo pipefail
  # do not run in pipelines, only locally. handled by service container in CI.
  if [ -z ${CI:-} ]; then
    . ./local/read_dotenv.sh {{dotenv}}
    ./local/database/run_postgres.sh
    # TODO: remove/improve
    sleep 1
  fi

# follow the database logs
db_logs:
  docker logs --follow depositduck_db

# start a Dockerised instance of PostgreSQL on :5432
db: _start_db
  @just db_logs

_wipe_db: _start_db
  #!/usr/bin/env bash
  set -euo pipefail
  # do not run in pipelines, only locally. handled by service container in CI.
  if [ -z ${CI:-} ]; then
    . ./local/read_dotenv.sh {{dotenv}}
    CONN_STR="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"
    SQL_CMD="select format('DROP TABLE IF EXISTS %I CASCADE;', tablename) from pg_tables where schemaname='public'\gexec"
    PSQL_CMD="echo \\\"$SQL_CMD\\\" | psql -t $CONN_STR"
    CMD="docker exec depositduck_db bash -c \"$PSQL_CMD\""
    eval "$CMD"
  fi

# create an Alembic migration
migration msg: venv
  #!/usr/bin/env bash
  set -euo pipefail
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  python -m alembic revision --autogenerate -m {{msg}}

# upgrade migrations to a revision - latest if one is not specified
migrate up="head": venv
  #!/usr/bin/env bash
  set -euo pipefail
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  python -m alembic upgrade {{up}}

# downgrade to a given alembic revision - previous one if not specified
downgrade down="-1": venv
  #!/usr/bin/env bash
  set -euo pipefail
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  python -m alembic downgrade {{down}}

# stop anything already running on :1025
_stop_mailhog:
  docker stop mailhog || true

# local mailserver to catch outgoing mail
mailhog: _stop_mailhog
  @docker run \
    --rm \
    --log-driver=none \
    --publish 8025:8025 \
    --publish 1025:1025 \
    --name mailhog \
    mailhog/mailhog:v1.0.1

# run the embeddings service in a container https://github.com/albertomh/draLLaM
drallam:
  @docker run \
    --rm \
    --publish 11434:11434 \
    --name drallam \
    drallam:0.1.0

# stop anything already running on :8000
_stop_server:
  @lsof -t -i :8000 | xargs -I {} kill -9 {}

# run the application locally, with the database in the background
run: stop && stop
  #!/usr/bin/env bash
  set -euo pipefail
  just db &
  just dotenv={{dotenv}} migrate &
  just dotenv={{dotenv}} mailhog &
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  uvicorn depositduck.main:webapp --reload


# Setting env vars from a dotenv in GitHub Actions is handled in a step of the action
# separate from the one that invokes the recipe. This is because environment variables are
# only available in steps following the one that sets them. Similarly, a separate step
# installs test dependencies.

# run unit & integration tests
# !must run as `just dotenv=.env.test test`
test: venv
  #!/usr/bin/env bash
  set -euo pipefail
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  uv pip sync {{REQS_DIR}}/test.txt
  if [ -z ${CI:-} ]; then
    python -m pytest tests/unit/ -s -vvv -W always --pdb
  else
    python -m pytest tests/unit/ -s -vvv -W always
  fi
  just dotenv={{dotenv}} coverage


# report on unit test coverage
coverage: venv
    . {{VENV_DIR}}/bin/activate
    if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
    uv pip sync {{REQS_DIR}}/test.txt
    python -m pytest --cov=depositduck tests/unit/

# run e2e Playwright tests
# !must run as `just dotenv=.env.e2e e2e`
e2e: venv _wipe_db && stop
  #!/usr/bin/env bash
  set -euo pipefail
  just dotenv={{dotenv}} mailhog &
  just dotenv={{dotenv}} run &
  . {{VENV_DIR}}/bin/activate
  if [ -z ${CI:-} ]; then . ./local/read_dotenv.sh {{dotenv}}; fi
  uv pip sync {{REQS_DIR}}/test.txt
  python -m playwright install --with-deps
  # TODO: remove/improve
  sleep 1
  python -m pytest tests/e2e/ -s -vvv -W always

# stop all running services
stop:
  docker stop depositduck_db || true
  docker stop drallam || true
  just dotenv={{dotenv}} _stop_mailhog
  just dotenv={{dotenv}} _stop_server

# cut a release and raise a pull request for it
release semver:
  ./local/cut_release.sh {{semver}}
