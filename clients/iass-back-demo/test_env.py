# clients/iass-back-demo/test_env.py
# test_env.py (colócalo en la misma carpeta que .env)

import os
from dotenv import load_dotenv

# Cargar .env manualmente
load_dotenv(".env")

# Imprimir variables
print(f"LABEL_DEMO: {os.getenv('LABEL_DEMO')}")
print(f"SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
