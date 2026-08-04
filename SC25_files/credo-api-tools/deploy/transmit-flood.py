#!/usr/bin/env python3
"""
Maximum bandwidth transmit flood - sends data from RC3 to Caltech pods
Generates continuous high-bandwidth traffic
"""
import os
import time
import subprocess
import json
import random
from datetime import datetime

NAMESPACE = os.environ.get('NAMESPACE', 'cblee-credo')
TARGET_POD = os.environ.get('TARGET_POD', '')
STREAM_ID = os.environ.get('STREAM_ID', '1')
TRANSMIT_INTERVAL = float(os.environ.get('TRANSMIT_INTERVAL', 0.5))
DATA_DIR = '/workspace/credo-data-rc3/detections'
RC3_POD = os.environ.get('RC3_POD', '')

if not TARGET_POD or not RC3_POD:
    print(f"Stream {STREAM_ID}: Missing TARGET_POD or RC3_POD, exiting")
    exit(0)

print(f'Stream {STREAM_ID}: Starting transmit flood to {TARGET_POD} (interval: {TRANSMIT_INTERVAL}s)')

# Find or generate data files
import glob
file_pattern = f'{DATA_DIR}/stream*/stream*_batch_*.json'

batch_count = 0
total_bytes = 0

while True:
    try:
        # Find files to send
        files = glob.glob(file_pattern)
        
        if not files:
            # Generate synthetic data file if none exist
            synth_file = f'{DATA_DIR}/synth_data_{STREAM_ID}_{int(time.time())}.json'
            data = {'detections': [{'id': i, 'data': 'x' * 10000} for i in range(1000)]}
            with open(synth_file, 'w') as f:
                json.dump(data, f)
            files = [synth_file]
        
        # Send multiple files in parallel
        files_to_send = random.sample(files, min(20, len(files))) if len(files) > 20 else files
        
        for file_path in files_to_send:
            try:
                # Get file size
                file_size = os.path.getsize(file_path)
                
                # Copy to target pod
                target_path = f'/tmp/tsunami_data/stream{STREAM_ID}_{os.path.basename(file_path)}'
                cmd = [
                    'kubectl', 'cp',
                    f'{NAMESPACE}/{RC3_POD}:{file_path}',
                    f'{NAMESPACE}/{TARGET_POD}:{target_path}'
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=30)
                
                if result.returncode == 0:
                    batch_count += 1
                    total_bytes += file_size
                    if batch_count % 50 == 0:
                        mb = total_bytes / (1024 * 1024)
                        print(f'Stream {STREAM_ID}: Transmitted {batch_count} files, {mb:.2f} MB to {TARGET_POD}')
            except Exception as e:
                pass  # Continue on errors
        
        time.sleep(TRANSMIT_INTERVAL)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        time.sleep(TRANSMIT_INTERVAL)

