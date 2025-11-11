# EcomHub API

API REST para integração com o sistema EcomHub, fornecendo acesso automatizado a dados de pedidos e tokens de autenticação.

## Base URL

```
https://ecomhub-selenium-production.up.railway.app
```

## Autenticação

Todas as requisições devem incluir o header `X-API-Key` com a chave de API fornecida.

```http
X-API-Key: sua-chave-api-aqui
```

## Limites de Taxa

| Endpoint | Limite |
|----------|--------|
| `/api/processar-ecomhub/` | 5 requisições/minuto |
| `/api/pedidos-status-tracking/` | 10 requisições/minuto |
| `/api/auth` | 30 requisições/minuto |
| `/api/auth/status` | 30 requisições/minuto |

## Endpoints

### 1. Obter Tokens de Autenticação

Retorna tokens válidos do EcomHub para uso direto com a API deles.

**GET** `/api/auth`

**Headers:**
```http
X-API-Key: sua-chave-api
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "cookies": {
    "token": "eyJ...",
    "e_token": "eyJ...",
    "refresh_token": "eyJ..."
  },
  "cookie_string": "token=eyJ...;e_token=eyJ...;refresh_token=eyJ...",
  "headers": {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://go.ecomhub.app",
    "Referer": "https://go.ecomhub.app/"
  },
  "timestamp": "2024-11-08T15:30:00",
  "expires_in": 120,
  "expires_at": "2024-11-08T15:33:00",
  "message": "Tokens válidos. Expira em 120 segundos"
}
```

**Resposta de Erro (503):**
```json
{
  "detail": "Tokens não disponíveis. Aguarde a sincronização automática"
}
```

### 2. Processar Dados de Pedidos

Extrai e processa dados de pedidos do EcomHub para análise.

**POST** `/api/processar-ecomhub/`

**Headers:**
```http
X-API-Key: sua-chave-api
Content-Type: application/json
```

**Body:**
```json
{
  "data_inicio": "2024-11-01",
  "data_fim": "2024-11-07",
  "pais_id": "164"
}
```

**Parâmetros:**
- `data_inicio` (string): Data inicial no formato YYYY-MM-DD
- `data_fim` (string): Data final no formato YYYY-MM-DD
- `pais_id` (string): ID do país ou "todos" para processar todos

**Países Disponíveis:**
| País | ID |
|------|-----|
| Espanha | 164 |
| Croácia | 41 |
| Grécia | 66 |
| Itália | 82 |
| Romênia | 142 |
| República Checa | 44 |
| Polônia | 139 |
| Todos | todos |

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "dados_processados": {
    "total_data": [...],
    "optimized_data": [...]
  },
  "estatisticas": {
    "total_pedidos": 150,
    "total_produtos": 25,
    "tempo_processamento": "45.2s"
  },
  "message": "Processamento concluído com sucesso"
}
```

### 3. Tracking de Status de Pedidos

Obtém informações detalhadas de status dos pedidos.

**POST** `/api/pedidos-status-tracking/`

**Headers:**
```http
X-API-Key: sua-chave-api
Content-Type: application/json
```

**Body:**
```json
{
  "data_inicio": "2024-11-01",
  "data_fim": "2024-11-07",
  "pais_id": "164"
}
```

**Resposta de Sucesso (200):**
```json
{
  "status": "success",
  "pedidos": [
    {
      "orderId": "12345",
      "customerName": "João Silva",
      "orderStatus": "delivered",
      "trackingNumber": "BR123456789",
      "totalAmount": 150.00,
      "createdAt": "2024-11-01T10:00:00Z",
      "deliveredAt": "2024-11-05T14:30:00Z"
    }
  ],
  "total_pedidos": 50,
  "data_sincronizacao": "2024-11-08T15:30:00Z",
  "pais_processado": "Espanha"
}
```

### 4. Status do Sistema

Verifica o status do sistema de sincronização de tokens.

**GET** `/api/auth/status`

**Headers:**
```http
X-API-Key: sua-chave-api
```

**Resposta (200):**
```json
{
  "status": "active",
  "has_tokens": true,
  "expires_in": 120,
  "last_update": "2024-11-08 15:30:00",
  "sync_enabled": true,
  "sync_interval": "2 minutos",
  "db_available": true
}
```

### 5. Sincronização Manual de Tokens (n8n)

Endpoint para disparar sincronização manual de tokens. **Recomendado para uso com n8n external scheduler**.

**POST** `/api/sync-tokens`

**Headers:**
```http
X-Sync-Key: sua-chave-sync-api
```

**Resposta de Sucesso (200):**
```json
{
  "success": true,
  "message": "Sincronização concluída com sucesso",
  "sync_number": 42,
  "timestamp": "2024-11-08T15:30:00Z",
  "next_sync_in_minutes": 2
}
```

#### Configuração n8n (Recomendado)

**Por que usar n8n?**
- ✅ Sem sobreposição de jobs (n8n aguarda resposta)
- ✅ Timeout configurável (máximo 2 minutos)
- ✅ Retry inteligente em caso de falha
- ✅ Dashboard visual de execuções
- ✅ Alertas fáceis de configurar

**Workflow n8n:**
```
1. Schedule Trigger (a cada 2 minutos)
   ↓
2. HTTP Request
   - Method: POST
   - URL: https://sua-api.railway.app/api/sync-tokens
   - Headers: {"X-Sync-Key": "{{$env.SYNC_API_KEY}}"}
   - Timeout: 120000ms (2 minutos)
   ↓
3. IF (Error)
   - Wait 10s
   - Retry (max 2x)
   ↓
4. IF (3 falhas consecutivas)
   - Send alert (Slack/Email/etc)
```

**Variáveis de Ambiente Necessárias:**
```bash
# No Railway (sua API)
SYNC_API_KEY=chave-secreta-forte-aqui
TOKEN_SYNC_ENABLED=false  # Desabilitar scheduler interno

# No n8n
SYNC_API_KEY=mesma-chave-secreta-forte-aqui
API_URL=https://sua-api.railway.app
```

**Nota Importante:** Os tokens do EcomHub expiram a cada **3 minutos**, por isso a sincronização deve rodar a cada **2 minutos** (margem de segurança de 1 minuto).

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Requisição inválida - verifique os parâmetros |
| 403 | API Key inválida ou ausente |
| 429 | Limite de taxa excedido |
| 500 | Erro interno do servidor |
| 503 | Serviço temporariamente indisponível |

## Exemplos de Uso

### cURL

```bash
# Obter tokens
curl -H "X-API-Key: sua-chave-api" \
  https://ecomhub-selenium-production.up.railway.app/api/auth

# Processar pedidos
curl -X POST \
  -H "X-API-Key: sua-chave-api" \
  -H "Content-Type: application/json" \
  -d '{"data_inicio":"2024-11-01","data_fim":"2024-11-07","pais_id":"164"}' \
  https://ecomhub-selenium-production.up.railway.app/api/processar-ecomhub/
```

### JavaScript/Fetch

```javascript
// Obter tokens
const response = await fetch('https://ecomhub-selenium-production.up.railway.app/api/auth', {
  headers: {
    'X-API-Key': 'sua-chave-api'
  }
});
const tokens = await response.json();

// Processar pedidos
const response = await fetch('https://ecomhub-selenium-production.up.railway.app/api/processar-ecomhub/', {
  method: 'POST',
  headers: {
    'X-API-Key': 'sua-chave-api',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    data_inicio: '2024-11-01',
    data_fim: '2024-11-07',
    pais_id: '164'
  })
});
const data = await response.json();
```

### Python/Requests

```python
import requests

# Configurar headers
headers = {
    'X-API-Key': 'sua-chave-api'
}

# Obter tokens
response = requests.get(
    'https://ecomhub-selenium-production.up.railway.app/api/auth',
    headers=headers
)
tokens = response.json()

# Processar pedidos
response = requests.post(
    'https://ecomhub-selenium-production.up.railway.app/api/processar-ecomhub/',
    headers=headers,
    json={
        'data_inicio': '2024-11-01',
        'data_fim': '2024-11-07',
        'pais_id': '164'
    }
)
data = response.json()
```

### n8n Integration

```json
{
  "method": "POST",
  "url": "https://ecomhub-selenium-production.up.railway.app/api/processar-ecomhub/",
  "headers": {
    "X-API-Key": "{{$credentials.ecomhub.apiKey}}",
    "Content-Type": "application/json"
  },
  "body": {
    "data_inicio": "{{$json.data_inicio}}",
    "data_fim": "{{$json.data_fim}}",
    "pais_id": "164"
  }
}
```

## Sobre a Análise de Efetividade

A API inclui funcionalidades de análise de efetividade de entregas, calculando métricas como:

- **Taxa de entrega por produto**: Percentual de pedidos entregues com sucesso
- **Visualização otimizada**: Agrupa status em categorias (Finalizados, Em Trânsito, Problemas)
- **Efetividade Parcial**: (Entregues / Finalizados) × 100
- **Efetividade Total**: (Entregues / Total de Pedidos) × 100

Estas métricas são retornadas automaticamente nos dados processados pelo endpoint `/api/processar-ecomhub/`.