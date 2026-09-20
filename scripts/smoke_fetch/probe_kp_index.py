import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # raiz del workspace importable
from sentinel_omega.infrastructure.pipeline.data_pipeline import fetch_kp_index
import time
start = time.time()
result = fetch_kp_index()
elapsed = time.time() - start
print('Time:', elapsed)
print('Result:', result)
