import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # raiz del workspace importable
from sentinel_omega.infrastructure.pipeline.data_pipeline import GeodynamicPipeline
import time
start = time.time()
pipe = GeodynamicPipeline()
data = pipe.fetch_beta1_data()
elapsed = time.time() - start
print('Time:', elapsed)
print('Keys:', list(data.keys()))
for k, v in data.items():
    if hasattr(v, '__len__'):
        print(f'  {k}: len={len(v)}')
    else:
        print(f'  {k}: {v}')
