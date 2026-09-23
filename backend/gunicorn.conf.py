"""Configuração do gunicorn para produção.

Padrão pensado para o SPECTER2 (embeddings) carregado em memória uma única vez:
`--preload` importa a aplicação no processo master (carrega o modelo) antes de
forkar; os workers herdam o modelo via copy-on-write.

Atenção: com mais de um worker, o cancelamento de requisições (django cache)
só funciona se REDIS_URL estiver definido no settings — LocMemCache é por
processo. Com 1 worker + threads, cada requisição roda em sua thread e o
cancelamento funciona sem Redis.
"""

import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("GUNICORN_WORKERS", "1"))
threads = int(os.getenv("GUNICORN_THREADS", "8"))
worker_class = "gthread"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "900"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
preload_app = True
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "2000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
accesslog = "-"
errorlog = "-"
capture_output = True