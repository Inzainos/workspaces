#!/bin/bash
# Baja el crudo Schumann de Eskdalemuir (BGS, 128 Hz, bobinas de inducción,
# 2025: ene-may + oct-dic) y no se deja engañar por códigos de salida.
#
# Item NGDC 192216 · DOI 10.5285/c80cd579-c647-4800-88f7-012ea304b22b
# «2025 High frequency magnetic field induction coil data from Eskdalemuir
#  Observatory, UK» · accessRestriction: unrestricted (Open File) ·
# Licencia: Open Government Licence --- atribución requerida:
#     «Contains data supplied by UKRI.»
#
# La condición de éxito es el TAMAÑO (21.314.692.275 bytes), no el exit code:
# la lección de la UGR (bitácora 2026-10-09) es que un exit 0 con HTTP 200
# no es un archivo completo. El server soporta Range (verificado: HTTP 206),
# así que cada intento reanuda donde quedó. Velocidad medida: ~180 KB/s por
# conexión (el paralelismo no ayuda: 4 conexiones dieron 256 KB/s agregados)
# --- ETA ~30 h; el servicio de usuario que corre esto lo relanza tras caídas
# y tras reinicios (enabled).
#
# Destino: sentinel_omega/data/schumann_eskdalemuir/ (gitignored).
set -u
D="$(cd "$(dirname "$0")/.." && pwd)/sentinel_omega/data/schumann_eskdalemuir"
mkdir -p "$D"
F="$D/2025.zip"
ESPERADO=21314692275
U="https://webservices.bgs.ac.uk/accessions/download/192216?fileName=2025.zip"
UA="Mozilla/5.0 (X11; Linux x86_64) SentinelOmega-research/1.0"

for i in $(seq 1 400); do
  S=$(stat -c%s "$F" 2>/dev/null || echo 0)
  if [ "$S" -ge "$ESPERADO" ]; then
    echo "COMPLETO: $S bytes tras $i intentos --- $(date -u +%FT%TZ)"
    # El tamaño puede coincidir por casualidad; el directorio central del zip
    # es la prueba real de integridad (lectura barata, no descomprime).
    if unzip -l "$F" >/dev/null 2>&1; then
      echo "ZIP INTEGRO: unzip -l OK"
      exit 0
    fi
    echo "ZIP CORRUPTO pese al tamaño: se re-descarga desde cero"
    mv "$F" "$F.corrupto_$(date +%s)"
  fi
  echo "intento $i: $((S/1048576)) MB de $((ESPERADO/1048576)) MB ($((100*S/ESPERADO))%) --- $(date -u +%FT%TZ)"
  # --speed-time/--speed-limit: si el server cae a <10 KB/s por 2 min, aborta
  # el intento y reanuda en el siguiente ciclo (el exit code no decide nada).
  curl -s -L -C - -A "$UA" \
       --speed-time 120 --speed-limit 10000 \
       --retry 3 --retry-delay 5 \
       -o "$F" "$U"
  sleep 5
done
S=$(stat -c%s "$F" 2>/dev/null || echo 0)
echo "AGOTADOS los intentos de esta invocacion: $S de $ESPERADO bytes"
exit 1
