import os
from dotenv import load_dotenv

# Nạp toàn bộ biến môi trường từ file .env một lần duy nhất
load_dotenv()

# Cấu hình AI
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_HOST_URL = "https://ollama.com"
MODEL_NAME = "qwen3-coder:480b-cloud"

# Cấu hình Database
SQL_SERVER_NAME = r"LAPTOP-3MUGN234\TUNDUONN"
SQL_DATABASE_NAME = "ITviecMini"

from ollama import Client

# Một Ollama Client dùng chung toàn hệ thống (tránh tạo trùng ở nhiều file)
ollama_client = Client(
    host=OLLAMA_HOST_URL,
    headers={'Authorization': f'Bearer {OLLAMA_API_KEY}'}
)