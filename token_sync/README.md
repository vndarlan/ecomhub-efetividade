# Token Sync - Módulo de Sincronização de Tokens

Módulo interno responsável pela lógica de obtenção e armazenamento de tokens do EcomHub.

> ⚠️ **IMPORTANTE**: A sincronização automática agora é feita via **n8n** (scheduler externo). Consulte a [documentação n8n](../n8n/README.md) para configuração.

---

## 📋 Sobre

Este módulo contém a lógica para:
1. Fazer login no EcomHub via Selenium
2. Extrair tokens de autenticação
3. Armazenar tokens no banco SQLite
4. Validar tokens
5. Fornecer tokens via endpoints da API

---

## 🔄 Como Funciona

O módulo é invocado de duas formas:

### 1. Via n8n (Recomendado) ✅

O n8n chama o endpoint `/api/sync-tokens` a cada 2 minutos:

```
n8n (Schedule) → POST /api/sync-tokens → sync_service.py → database.py
```

**Configuração**: Ver [n8n/README.md](../n8n/README.md)

### 2. Via Scheduler Interno (Não Recomendado) ⚠️

Thread em background executa automaticamente:

```
scheduler.py → sync_service.py → database.py
```

**Configuração**:
```env
TOKEN_SYNC_ENABLED=true  # Habilita scheduler interno
```

> **Por que não recomendado?**
> - Menos controle sobre falhas
> - Sem dashboard visual
> - Pode sobrepor execuções
> - Dificulta debugging

---

## 📁 Estrutura do Módulo

```
token_sync/
├── database.py         # SQLite para persistência de tokens
├── sync_service.py     # Lógica de login e extração de tokens
├── scheduler.py        # Scheduler interno (APScheduler)
├── config.py          # Configurações do módulo
├── token_validator.py  # Validação de tokens JWT
└── notifier.py        # Notificação de sincronizações
```

---

## ⚙️ Configuração

### Variáveis de Ambiente

```env
# Credenciais EcomHub (obrigatório)
ECOMHUB_EMAIL=seu-email@exemplo.com
ECOMHUB_PASSWORD=sua-senha

# Scheduler (opcional - usar n8n ao invés)
TOKEN_SYNC_ENABLED=false  # false = usar n8n, true = scheduler interno

# API Keys
API_SECRET_KEY=sua-chave-secreta
SYNC_API_KEY=chave-para-endpoint-sync
```

---

## 🗄️ Banco de Dados

**Localização**:
- Railway: `/tmp/tokens.db`
- Local: `tokens.db` (raiz do projeto)

**Schema**:
```sql
CREATE TABLE tokens (
    id INTEGER PRIMARY KEY,
    token TEXT NOT NULL,
    e_token TEXT NOT NULL,
    refresh_token TEXT,
    timestamp TEXT NOT NULL
);
```

---

## 🔌 Endpoints

Os tokens são consumidos via:

| Endpoint | Descrição |
|----------|-----------|
| `GET /api/auth` | Retorna tokens válidos do banco |
| `GET /api/auth/status` | Status do sistema de sincronização |
| `POST /api/sync-tokens` | Dispara sincronização manual (usado pelo n8n) |

---

## 📊 Fluxo de Dados

```
┌──────────────────────────────────────────┐
│  n8n (Trigger a cada 2 minutos)          │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  POST /api/sync-tokens                   │
│  (main.py - endpoint)                    │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  sync_service.py                         │
│  1. create_driver() - Inicia Selenium    │
│  2. login_ecomhub() - Faz login          │
│  3. get_auth_cookies() - Extrai tokens   │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  database.py                             │
│  save_tokens() - Salva no SQLite         │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  SQLite (/tmp/tokens.db)                 │
│  Tokens armazenados e disponíveis        │
└──────────────────────────────────────────┘
```

---

## 🕐 Timing

- **Duração dos tokens**: 3 minutos
- **Intervalo de renovação**: 2 minutos
- **Margem de segurança**: 1 minuto

---

## 🔗 Links

- [Configuração n8n (Recomendado)](../n8n/README.md)
- [README Principal](../README.md)
- [Documentação API EcomHub](../ECOMHUB_API_DOCUMENTATION.md)

---

**Última atualização:** 2025-11-11