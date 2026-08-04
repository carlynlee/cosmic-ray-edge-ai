#!/usr/bin/env bash
# Launch the local FL demo: server (real data + CosmicWatch referee) + simulated
# phones driving it. Open the printed URL in a browser to watch the dashboard.
#   ./fldemo/run_demo.sh            # 5 sim phones on :8088
#   PHONES=8 PORT=9000 ./fldemo/run_demo.sh
set -e
cd "$(dirname "$0")/.."                      # -> cosmicphysicist/
DATA="$(pwd)/fldemo/data"
PORT="${PORT:-8088}"
export FL_MIN_CLIENTS="${FL_MIN_CLIENTS:-3}"
export FL_VAL_PATH="$DATA/real_val.json"
export FL_SEED_PATH="$DATA/real_train.json"
export FL_REFEREE_PATH="$DATA/referee_summary.json"

python3 -m fldemo.fl_server --port "$PORT" & SRV=$!
sleep 3
node fldemo/sim_phones.js "http://localhost:$PORT" "${PHONES:-5}" & SIM=$!
trap "kill $SRV $SIM 2>/dev/null" EXIT
echo ""
echo "  ==> Dashboard live at:  http://localhost:$PORT"
echo "      (Ctrl-C to stop)"
wait
