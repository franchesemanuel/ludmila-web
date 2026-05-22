#!/bin/bash
# Script de monitoreo para rediseño en curso
# Ejecutar desde: /Users/francosalcedo/ludmila-web

cd /Users/francosalcedo/ludmila-web
VENV=".venv/bin/python"
ERRORS=0
WARNINGS=0

log_ok()  { echo "  [OK]  $1"; }
log_err() { echo "  [ERR] $1"; ERRORS=$((ERRORS+1)); }
log_warn(){ echo "  [WARN] $1"; WARNINGS=$((WARNINGS+1)); }

echo ""
echo "===== MONITOR LUDMILA-WEB $(date '+%Y-%m-%d %H:%M:%S') ====="

# 1. Django system check
echo ""
echo "-- 1. Django system check --"
DJANGO_OUT=$($VENV manage.py check 2>&1)
DJANGO_ERRORS=$(echo "$DJANGO_OUT" | grep -c "^blog\.\|^reservas\.\|^users\.\|^core\." 2>/dev/null || echo 0)
if echo "$DJANGO_OUT" | grep -q "^System check identified no issues"; then
  log_ok "Sin problemas"
elif echo "$DJANGO_OUT" | grep -q "^System check identified.*0 errors"; then
  log_ok "Sin errores (solo warnings W042 esperados)"
else
  CRITICAL=$(echo "$DJANGO_OUT" | grep "ERROR\|CRITICAL" | wc -l | tr -d ' ')
  if [ "$CRITICAL" -gt "0" ]; then
    log_err "Errores criticos en Django check:"
    echo "$DJANGO_OUT" | grep "ERROR\|CRITICAL"
  else
    log_ok "Solo warnings conocidos (W042)"
  fi
fi

# 2. CSRF en todos los formularios POST
echo ""
echo "-- 2. CSRF en formularios POST --"
FORM_FILES=$(find . -name "*.html" -not -path "*/.venv/*" | xargs grep -l 'method="post"\|method='"'"'post'"'" 2>/dev/null)
for f in $FORM_FILES; do
  if grep -q "csrf_token" "$f"; then
    log_ok "$f"
  else
    log_err "CSRF FALTANTE en $f"
  fi
done

# 3. Herencia de templates (todos deben extender base.html)
echo ""
echo "-- 3. Herencia de templates --"
ALL_TEMPLATES=$(find . -name "*.html" -not -path "*/.venv/*" -not -name "base.html")
for f in $ALL_TEMPLATES; do
  if grep -q "{% extends" "$f"; then
    BASE=$(grep "{% extends" "$f" | head -1)
    log_ok "$f -> $BASE"
  else
    log_warn "$f no extiende ningún template (puede ser parcial o fragmento)"
  fi
done

# 4. Verificar URL names en templates
echo ""
echo "-- 4. URL names críticos --"
EXPECTED_URLS="home reservar blog:index blog:detail dashboard login logout register"
for url in $EXPECTED_URLS; do
  COUNT=$(grep -r "url '$url'\|url \"$url\"" templates/ --include="*.html" 2>/dev/null | wc -l | tr -d ' ')
  if [ "$COUNT" -gt "0" ]; then
    log_ok "url '$url' encontrado ($COUNT usos)"
  else
    log_warn "url '$url' no encontrado en /templates/ (puede estar en templates de app)"
  fi
done

# 5. Middleware de seguridad intacto
echo ""
echo "-- 5. Middleware de seguridad --"
SETTINGS="config/settings.py"
for MW in "CsrfViewMiddleware" "SecurityMiddleware" "AuthenticationMiddleware" "XFrameOptionsMiddleware"; do
  if grep -q "$MW" "$SETTINGS"; then
    log_ok "$MW presente"
  else
    log_err "$MW ELIMINADO de MIDDLEWARE"
  fi
done

# 6. SECRET_KEY y DEBUG
echo ""
echo "-- 6. Settings de seguridad --"
if grep -q "SECRET_KEY" "$SETTINGS"; then
  log_ok "SECRET_KEY presente"
else
  log_err "SECRET_KEY NO encontrada"
fi
if grep -q "DEBUG = True" "$SETTINGS"; then
  log_warn "DEBUG = True (ok en desarrollo)"
fi

# 7. Sintaxis Python en views y models
echo ""
echo "-- 7. Sintaxis Python --"
for pyfile in core/views.py blog/views.py reservas/views.py users/views.py reservas/models.py blog/models.py; do
  if [ -f "$pyfile" ]; then
    SYNTAX_ERR=$($VENV -m py_compile "$pyfile" 2>&1)
    if [ -z "$SYNTAX_ERR" ]; then
      log_ok "$pyfile OK"
    else
      log_err "ERROR SINTAXIS en $pyfile: $SYNTAX_ERR"
    fi
  fi
done

# 8. Archivos CSS/JS estáticos
echo ""
echo "-- 8. Archivos estáticos --"
for f in "static/css/styles.css"; do
  if [ -f "$f" ]; then
    SIZE=$(wc -c < "$f")
    log_ok "$f existe ($SIZE bytes)"
  else
    log_err "$f NO ENCONTRADO"
  fi
done

# === RESUMEN ===
echo ""
echo "===== RESUMEN ====="
echo "  Errores:    $ERRORS"
echo "  Advertencias: $WARNINGS"
if [ "$ERRORS" -eq "0" ]; then
  echo "  ESTADO: OK"
else
  echo "  ESTADO: REQUIERE ATENCION"
fi
echo ""
