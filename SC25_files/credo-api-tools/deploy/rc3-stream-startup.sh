#!/bin/bash
# Startup script to run inside RC3 pods
# This starts multiple high-bandwidth streams

pkill -f high-bandwidth-streamer || true
sleep 1

ES_PASSWORD="${ES_PASSWORD}"
NUM_STREAMS=5
BATCH_SIZE=2000
STREAM_INTERVAL=1

for i in $(seq 1 ${NUM_STREAMS}); do
    OUTPUT_DIR="/workspace/credo-data-rc3/detections/stream${i}"
    mkdir -p "${OUTPUT_DIR}"
    
    nohup env ES_HOST=credo-elasticsearch-service ES_INDEX=credo-detections \
         ES_USER=elastic ES_PASSWORD="${ES_PASSWORD}" \
         BATCH_SIZE=${BATCH_SIZE} STREAM_INTERVAL=${STREAM_INTERVAL} \
         STREAM_ID=${i} OUTPUT_DIR="${OUTPUT_DIR}" \
         python3 /tmp/high-bandwidth-streamer.py > /tmp/stream_${i}.log 2>&1 &
    
    echo $! > /tmp/stream_${i}.pid
    echo "Stream ${i} started (PID: $(cat /tmp/stream_${i}.pid))"
done

echo "All ${NUM_STREAMS} streams started"

