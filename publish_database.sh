#!/usr/bin/env bash
# Publishes the local database to the read only server (compose.prod.yaml).
#
#   ./publish_database.sh [user@host]
#
# Makes a copy of the database for the read only server with `flask publish_db`, in the local backend
# container (so the local stack has to be running), and saves it to published/database.db. Given a server, it
# then copies it there and swaps it in. The server reads the new copy straight away, without a restart.
#
# Settings, as environment variables:
#   PUBLISH_HOST  The server to publish to, as user@host. Can be given as the argument instead. Without one,
#                 the copy is only saved locally.
#   PUBLISH_DIR   The folder on the server with compose.prod.yaml. Defaults to curling-stone-tracker in the
#                 home folder.
#   PUBLISH_ARGS  Extra options for flask publish_db, e.g. --all-runs to keep the runs that didn't complete.
set -euo pipefail

cd "$(dirname "$0")"
host="${1:-${PUBLISH_HOST:-}}"
remote_dir="${PUBLISH_DIR:-curling-stone-tracker}"
container_path=/tmp/published_database.db

mkdir -p published
# shellcheck disable=SC2086 # PUBLISH_ARGS can be several options
docker compose exec -T curling-tracker-backend flask publish_db ${PUBLISH_ARGS:-} "$container_path"
docker compose cp "curling-tracker-backend:$container_path" published/database.db.tmp
docker compose exec -T curling-tracker-backend rm -f "$container_path"
mv -f published/database.db.tmp published/database.db

if [ -z "$host" ]; then
    echo "Saved published/database.db. Give a server (user@host) to upload it."
    exit 0
fi

ssh "$host" "mkdir -p '$remote_dir/published'"
scp published/database.db "$host:$remote_dir/published/database.db.tmp"
# A rename is atomic, so the server's requests read either the old copy or the new one
ssh "$host" "mv -f '$remote_dir/published/database.db.tmp' '$remote_dir/published/database.db'"
echo "Published to $host:$remote_dir/published/database.db"
