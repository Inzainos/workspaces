#!/bin/bash
# Baja el procesado Schumann de Sierra Nevada (UGR) y no se deja engañar
# por el codigo de salida: la condicion de exito es el TAMANO.
#
# Por que existe: la primera corrida salio con exit 0 y HTTP 200 con solo
# 1,08 de 3,58 GB --- el servidor cerro la conexion y curl no lo delato.
# Un exit 0 no es un archivo completo (bitacora 2026-10-09). El «HTTP 403»
# que se habia reportado era bloqueo de bots: con User-Agent propio entra.
#
# Destino: sentinel_omega/data/schumann_granada/ (gitignored, regla 3).
# Verificacion posterior: docs/SCHUMANN_FUENTES.md y la ingesta con
# sentinel_omega.infrastructure.api.schumann_granada.
set -u
D="$(cd "$(dirname "$0")/.." && pwd)/sentinel_omega/data/schumann_granada"
mkdir -p "$D"
F="$D/Npz.zip"
ESPERADO=3579685616
U="https://digibug.ugr.es/bitstream/handle/10481/71563/Npz.zip?sequence=1&isAllowed=y"
UA="Mozilla/5.0 (X11; Linux x86_64) SentinelOmega-research/1.0"
for i in $(seq 1 60); do
  S=$(stat -c%s "$F" 2>/dev/null || echo 0)
  if [ "$S" -ge "$ESPERADO" ]; then echo "COMPLETO: $S bytes en $i intentos"; exit 0; fi
  echo "intento $i: $((S/1048576)) MB de $((ESPERADO/1048576)) MB ($((100*S/ESPERADO))%)"
  curl -s -L -C - -A "$UA" --speed-time 90 --speed-limit 5000 \
       --retry 3 --retry-delay 5 -o "$F" "$U"
  sleep 3
done
S=$(stat -c%s "$F" 2>/dev/null || echo 0)
echo "AGOTADO tras 60 intentos: $S de $ESPERADO bytes"; exit 1
