import sqlite3
import pandas as pd

DB = '/home/deamon/workspaces/sentinel_omega/data/SENTINEL_OMEGA_PRO.db'
conn = sqlite3.connect(DB)

df = pd.read_sql('SELECT timestamp_blk, bz_promedio FROM tbl_clima_espacial_raw ORDER BY timestamp_blk', conn)
df['bz_derivada'] = df['bz_promedio'].diff().fillna(0.0)

cursor = conn.cursor()
cursor.execute('BEGIN TRANSACTION')
n = 0
for _, row in df.iterrows():
    cursor.execute('UPDATE tbl_clima_espacial_raw SET bz_derivada = ? WHERE timestamp_blk = ?', (row['bz_derivada'], row['timestamp_blk']))
    n += 1
cursor.execute('COMMIT')
print(f'Updated {n} rows with bz_derivada.')
