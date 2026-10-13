#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$(uname -sm)" in 'Linux x86_64') ;; *) echo '需要 Linux x86_64；此包不支持其他平台。' >&2; exit 2;; esac
exec /usr/bin/env -i PATH=/usr/bin:/bin LANG=C.UTF-8 LC_ALL=C.UTF-8 HOME=/ \
  "$ROOT/python/bin/python3.12" -I -S -B "$ROOT/launch.py" "$@"
