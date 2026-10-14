#!/bin/sh
set -eu

if [ -z "${VIRTUAL_ENV:-}" ] || [ ! -x "$VIRTUAL_ENV/bin/python" ]; then
    echo 'Активируйте виртуальное окружение с установленными зависимостями.' >&2
    exit 2
fi

cd "$(dirname "$0")"
exec "$VIRTUAL_ENV/bin/python" -m potion_lab
