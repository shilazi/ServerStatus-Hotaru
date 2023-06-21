#!/bin/bash

set -e
set -o pipefail

run_server() {
    PORT=${PORT:-35601}
    LOG_FILE="/var/log/nginx/sergate.log"

    nginx
    nohup /svrstat/sergate --web-dir=/svrstat/html --config=config.json \
        --port=${PORT} &> ${LOG_FILE} &
    exec tail -F ${LOG_FILE}
}

run_client() {
    exec python3 -u /svrstat/status-client.py
}

help() {
    echo "Usage:"
    echo "    docker run ... server           # start nginx and sergate"
    echo "    docker run ... client           # start status-client.py"
    echo "    "
}

if test -z "$1"; then
    help
    exit 0
fi

case "$1" in
    server)
        run_server
        ;;
    client)
        run_client
        ;;
    *)
        exec "$@"
        ;;
esac
