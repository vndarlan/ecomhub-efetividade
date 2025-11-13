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

## Endpoints

### 1. Obter Tokens de Autenticação

Retorna tokens válidos do EcomHub obtidos via Selenium on-demand.

⚠️ **IMPORTANTE**:
- Cada requisição cria um driver Chrome e executa login completo (~50 segundos)
- Tokens expiram em aproximadamente 3 minutos

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
    "Referer": "https://go.ecomhub.app/",
    "User-Agent": "Mozilla/5.0..."
  },
  "timestamp": "2024-11-08T15:30:00Z",
  "message": "Tokens obtidos com sucesso. Expiram em ~3 minutos."
}
```

**Resposta de Erro (500):**
```json
{
  "detail": "Falha ao fazer login no EcomHub"
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

## Códigos de Erro

| Código | Descrição |
|--------|-----------|
| 400 | Requisição inválida - verifique os parâmetros |
| 403 | API Key inválida ou ausente |
| 429 | Limite de taxa excedido |
| 500 | Erro interno do servidor |
| 503 | Serviço temporariamente indisponível |


## Sobre a Análise de Efetividade

A API inclui funcionalidades de análise de efetividade de entregas, calculando métricas como:

- **Taxa de entrega por produto**: Percentual de pedidos entregues com sucesso
- **Visualização otimizada**: Agrupa status em categorias (Finalizados, Em Trânsito, Problemas)
- **Efetividade Parcial**: (Entregues / Finalizados) × 100
- **Efetividade Total**: (Entregues / Total de Pedidos) × 100

Estas métricas são retornadas automaticamente nos dados processados pelo endpoint `/api/processar-ecomhub/`.