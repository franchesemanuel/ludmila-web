#!/bin/bash
# Watcher de rediseño – corre en background y detecta cambios
# Guarda resultado en .monitor/last_check.log

cd /Users/francosalcedo/ludmila-web
LAST_HASH=""

while true; do
  CURRENT_HASH=$(git diff HEAD --name-only 2>/dev/null | md5 2>/dev/null || echo "")
  STAGED=$(git diff --cached --name-only 2>/dev/null | md5 2>/dev/null || echo "")
  COMBINED="$CURRENT_HASH-$STAGED"

  if [ "$COMBINED" != "$LAST_HASH" ]; then
    LAST_HASH="$COMBINED"
    bash .monitor/check.sh > .monitor/last_check.log 2>&1
    ERRORS=$(grep "\[ERR\]" .monitor/last_check.log | wc -l | tr -d ' ')
    TIMESTAMP=$(date '+%H:%M:%S')
    if [ "$ERRORS" -gt "0" ]; then
      echo "[$TIMESTAMP] CAMBIOS DETECTADOS - $ERRORS ERRORES:" >> .monitor/history.log
      grep "\[ERR\]" .monitor/last_check.log >> .monitor/history.log
    else
      echo "[$TIMESTAMP] Cambios detectados - Estado OK" >> .monitor/history.log
    fi
  fi

  sleep 10
done
