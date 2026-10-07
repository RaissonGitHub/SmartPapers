# SmartPapers

SmartPapers é um assistente para pesquisa acadêmica que combina busca por artigos científicos com um agente de chat baseado em IA. O sistema indexa artigos do [OpenAlex](https://openalex.org/) em PostgreSQL com vetores (pgvector) e permite conversar com um agente para encontrar, analisar e sintetizar literatura científica.

## Visão geral

- **Backend**: Django + Django REST Framework, com PostgreSQL + pgvector para busca semântica.
- **Frontend**: React 19 + Vite 8 + Tailwind CSS 4.
- **IA**: Google Gemini (via `google-genai`) para o agente conversacional.
- **Coleta de dados**: script para importar artigos do OpenAlex com embeddings vetoriais.
- **Deploy**: Docker Compose (desenvolvimento e produção), Nginx como proxy reverso, hospedado em [https://raiss.top](https://raiss.top).
- **Streaming**: respostas do chat em NDJSON (Newline Delimited JSON), exibidas em tempo real.

## Tecnologias

### Backend
- Python 3.12
- Django 5.2.7
- Django REST Framework 3.16.1
- PostgreSQL 16 + pgvector 0.8.1
- Gunicorn 23.0.0
- `google-genai` 2.24.0
- `pgvector-python` 0.4.1
- NumPy 2.3.3

### Frontend
- React 19.2.8
- Vite 8.3.0
- Tailwind CSS 4.3.3
- MUI (Material UI)
- React Markdown
- Axios
- ESLint + Prettier

### Infraestrutura
- Docker + Docker Compose
- Nginx (proxy reverso + SPA)
- Cloudflare Tunnel (produção)

## Estrutura do projeto

```text
SmartPapers/
├── backend/
│   ├── artigos/                  # Modelos, serializers, serviços e views de artigos
│   ├── autenticacao/             # Autenticação, usuários e permissões
│   ├── backend/                  # Configurações Django e URLs do projeto
│   ├── chat/                     # Agente de chat, modelos, serviços e fluxos
│   ├── manage.py                 # Entrypoint do Django
│   └── requirements.txt          # Dependências do backend
├── frontend/
│   ├── src/
│   │   ├── components/           # Componentes React
│   │   ├── hooks/                # Hooks customizados
│   │   ├── pages/                # Páginas da aplicação
│   │   ├── services/             # Chamadas à API e streaming
│   │   └── utils/                # Utilitários gerais
│   ├── Dockerfile               # Imagem do frontend
│   ├── Dockerfile.dev           # Ambiente de desenvolvimento
│   ├── nginx.conf               # Configuração do Nginx em produção
│   └── package.json             # Dependências e scripts do frontend
├── scripts/
│   └── init_db.sql             # Script de inicialização do banco
├── Dockerfile                  # Imagem do backend principal
├── docker-compose.yml          # Ambiente de desenvolvimento
├── docker-compose.prod.yml      # Ambiente de produção
├── LICENSE                     # Licença do projeto
├── README.md                   # Documentação do projeto
├── requirements.txt            # Dependências gerais do projeto
└── .gitignore
```

## Ambientes

### Desenvolvimento
- Projeto Compose: `smartpapers_dev`
- Containers: `smartpapers_db`, `smartpapers_backend`, `smartpapers_frontend`
- Volume: `smartpapers_dev_pgdata`
- Bind mounts: código do backend e do frontend sincronizado para hot-reload

### Produção
- Projeto Compose: `smartpapers_prod`
- Containers: `smartpapers_prod_db`, `smartpapers_prod_backend`, `smartpapers_prod_frontend`
- Volume: `smartpapers_prod_pgdata`
- Zero bind mounts de código — usa `COPY` nos Dockerfiles (imagens imutáveis)

## Pré-requisitos

- Docker e Docker Compose
- PostgreSQL com extensão `pgvector` (via imagem oficial `pgvector/pgvector:pg16`)
- Chave de API do Google Gemini ([Google AI Studio](https://aistudio.google.com/apikey))

## Configuração

### 1. Backend (.env)

Crie `backend/.env` (exemplo abaixo). **Nunca commitar segredos**.

```env
# Banco de dados
DATABASE_URL=postgresql://smartpapers:senha@db:5432/smartpapers
POSTGRES_DB=smartpapers
POSTGRES_USER=smartpapers
POSTGRES_PASSWORD=senha

# Django
SECRET_KEY=sua-chave-secreta
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,raiss.top
CORS_ALLOWED_ORIGINS=https://raiss.top,http://localhost:5173,http://localhost:3000
CSRF_TRUSTED_ORIGINS=https://raiss.top,http://localhost:5173

# URL do admin customizada (produção)
DJANGO_ADMIN_URL=gestao-admina-smartpapers/

# Google Gemini
GEMINI_API_KEY=sua-chave-gemini
GEMINI_MODEL=gemini-2.5-flash

# Coleta (OpenAlex)
EMAIL_COLETA=seu-email@exemplo.com
EMBED_BATCH=32

# Tunnel (produção - Cloudflare)
TUNNEL_TOKEN=seu-token-cloudflared
```

### 2. Frontend (.env)

Crie `frontend/.env` para desenvolvimento:

```env
VITE_API_URL=http://localhost:8000
```

Em produção, o Nginx faz proxy reverso da API na mesma origem (`/`), então o frontend usa `BASE_URL="/"`.

## Desenvolvimento

Subir todos os serviços:

```bash
docker compose up --build
```

Acessos:
- Frontend: [http://localhost:5173](http://localhost:5173)
- API do backend: [http://localhost:8000](http://localhost:8000)
- Admin: [http://localhost:8000/admin/](http://localhost:8000/admin/) (ou com `DJANGO_ADMIN_URL`)

Migrações (ambiente de desenvolvimento):

```bash
docker compose exec backend python manage.py migrate
```

## Produção

Subir com projeto separado:

```bash
docker compose -p smartpapers_prod -f docker-compose.prod.yml up -d --build
```

Verificar saúde:

```bash
docker compose -p smartpapers_prod -f docker-compose.prod.yml ps
```

Logs:

```bash
docker compose -p smartpapers_prod -f docker-compose.prod.yml logs -f backend
docker compose -p smartpapers_prod -f docker-compose.prod.yml logs -f frontend
```

Rebuild específico:

```bash
docker compose -p smartpapers_prod -f docker-compose.prod.yml up -d --build frontend
```

## Coleta de artigos (OpenAlex)

A coleta baixa artigos do OpenAlex, gera embeddings com Gemini e salva os dados no banco (PostgreSQL + pgvector).

Executar em desenvolvimento:

```bash
docker compose exec backend python coleta/coletar_openalex.py
```

Executar em produção:

```bash
docker compose -p smartpapers_prod -f docker-compose.prod.yml exec backend python coleta/coletar_openalex.py
```

**Notas importantes sobre a coleta:**
- Usa `python -u` (unbuffered) para acompanhar o progresso em tempo real.
- `EMBED_BATCH=32` (configuração otimizada para CPU).
- Processa apenas artigos com `embedding is None` (reprocessamento incremental).
- Conta apenas novos artigos no progresso (não reconta os já existentes).
- Cada ambiente (desenvolvimento e produção) mantém seus próprios 10.000 artigos isolados.

## Backups e restore

Os dumps são gerados em `backups/` (diretório ignorado pelo Git). Formato: `artigos-YYYYMMDD-HHMMSS.dump`.

O dump cobre: `artigo`, `autor`, `artigo_autor` e sequências. **Não inclui usuários**.

**Importante:** o restore deve respeitar a ordem por FKs: `artigo` → `autor` → `artigo_autor` → sequências. Um único `pg_restore` pode falhar por dependências de chaves estrangeiras; o procedimento validado é restaurar em etapas nessa ordem.

## Chat com streaming

O agente de chat responde em **NDJSON (Newline Delimited JSON)**, enviando eventos linha por linha conforme as etapas do processamento acontecem (planejamento, busca, síntese, etc.), terminando com um evento `resultado`.

**Frontend**: `fetch()` + `ReadableStream` (não usa `axios` para streaming). O leitor processa cada linha JSON e atualiza o progresso em tempo real.

**Nginx (produção)**: desabilita `proxy_buffering` e `proxy_cache` para o endpoint `/chat/agente/`, garantindo que cada linha chegue ao navegador imediatamente.

## Qualidade de código

Lint (frontend):

```bash
cd frontend && npx eslint .
```

Via Docker (recomendado para garantir a versão):

```bash
docker run --rm -v "C:\Users\lixeiro\Documents\SmartPapers:/app" -w /app node:22-alpine sh -c "npm ci --silent >/dev/null 2>&1 && npx eslint ."
```

Typecheck: verificar os comandos em `package.json` e `pyproject.toml` conforme o ambiente.

## Convenções

- **Nunca commitar segredos** (tokens, chaves, `.env`). Tokens sensíveis (por exemplo, Cloudflare Tunnel) ficam em caminhos do sistema com ACL restrita.
- **Não versionar migrations** — `/migrations/` está no `.gitignore`. As migrations existem localmente e entram na imagem via `COPY`.
- **Infraestrutura não pertence ao repositório** — tunnel/hospedagem (Cloudflare Tunnel) é infraestrutura, não parte do projeto. Não adicionar serviços de tunnel ao `docker-compose.prod.yml`.
- **Um único processo de coleta** — evitar coletores paralelos duplicados.
- **CSS responsivo com `dvh`** — usa `min-height: 100dvh` (dynamic viewport height) para evitar scroll indesejado no mobile (barra de URL).
- **Assets com hash** — o Nginx permite cache longo para assets com hash e força `Cache-Control: no-cache` no HTML (`/` e `/index.html`) para garantir deploys sem hard refresh.

## URLs

- Produção: [https://raiss.top](https://raiss.top)
- Admin (produção): [https://raiss.top/gestao-admina-smartpapers/](https://raiss.top/gestao-admina-smartpapers/)

## Licença

[MIT License](LICENSE)

## Suporte

Reportar problemas: [GitHub Issues](https://github.com/anomalyco/opencode/issues)
