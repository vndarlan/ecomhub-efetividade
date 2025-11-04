# 🔐 EcomHub Auth Service

Serviço de autenticação automática para API da EcomHub rodando na nuvem. Elimina a necessidade de copiar tokens manualmente do navegador, fornecendo um endpoint HTTP que retorna cookies e tokens de autenticação automaticamente.

## 🌐 URL do Serviço

```
https://ecomhub-selenium-production.up.railway.app
```

## 📋 O Que Este Serviço Faz

- ✅ **Autenticação automática** - Faz login na EcomHub via Selenium
- ✅ **Retorna tokens via API** - Use em n8n, Make, Zapier ou qualquer sistema
- ✅ **Sempre atualizado** - Tokens frescos a cada requisição
- ✅ **Documentação integrada** - Acesse direto no navegador

## 📚 Documentação Online

Acesse direto no navegador para consultar:

- **https://ecomhub-selenium-production.up.railway.app/** - Página inicial
- **https://ecomhub-selenium-production.up.railway.app/docs** - Documentação Swagger interativa
- **https://ecomhub-selenium-production.up.railway.app/api-ecomhub-docs** - Documentação da API EcomHub

## 🔌 Como Usar a API

### Endpoint de Autenticação

**POST /api/auth**

Retorna cookies e headers de autenticação da EcomHub.

#### Exemplo de Requisição (cURL)

```bash
curl -X POST https://ecomhub-selenium-production.up.railway.app/api/auth
```

#### Exemplo de Resposta

```json
{
  "success": true,
  "cookies": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "e_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "_ga": "GA1.1.123456789.1234567890",
    "_clck": "...",
    "_ga_5F69YZWZS3": "...",
    "_clsk": "..."
  },
  "cookie_string": "token=eyJhbGc...; e_token=eyJhbGc...; refresh_token=eyJhbGc...",
  "headers": {
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://go.ecomhub.app",
    "Referer": "https://go.ecomhub.app/",
    "User-Agent": "Mozilla/5.0...",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json"
  },
  "timestamp": "2025-11-04T15:30:00Z",
  "message": "Autenticação bem-sucedida"
}
```

## 🔧 Integração com n8n (Passo a Passo)

### 1️⃣ Obter Tokens de Autenticação

1. Adicione um nó **"HTTP Request"**
2. Configure:
   - **Method:** `POST`
   - **URL:** `https://ecomhub-selenium-production.up.railway.app/api/auth`
   - **Authentication:** None
3. Execute e guarde a resposta

### 2️⃣ Usar Tokens na API EcomHub

1. Adicione outro nó **"HTTP Request"**
2. Configure:
   - **Method:** `GET`
   - **URL:** `https://api.ecomhub.app/api/orders`
   - **Query Parameters:**
     - `offset`: `0`
     - `orderBy`: `null`
     - `orderDirection`: `null`
     - `conditions`: `{"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164]}}`
     - `search`: (deixe vazio)
   - **Headers:** Use os headers retornados no passo 1
   - **Send Headers:** ON
   - **Header Parameters:**
     ```
     Accept: */*
     Accept-Language: pt-BR,pt;q=0.9
     Origin: https://go.ecomhub.app
     Referer: https://go.ecomhub.app/
     User-Agent: {{ $json.headers["User-Agent"] }}
     X-Requested-With: XMLHttpRequest
     Content-Type: application/json
     Cookie: {{ $json.cookie_string }}
     ```

### 3️⃣ Processar Pedidos

Agora você tem acesso aos pedidos da EcomHub! Use nós do n8n para:
- Filtrar pedidos por status
- Enviar para planilhas
- Criar notificações
- Integrar com outros sistemas

## 💡 Exemplo Completo Python (Para Referência)

```python
import requests
import json

# 1. Obter autenticação
auth_response = requests.post(
    "https://ecomhub-selenium-production.up.railway.app/api/auth"
)
auth_data = auth_response.json()

# 2. Configurar sessão com cookies
session = requests.Session()
session.cookies.update(auth_data["cookies"])
session.headers.update(auth_data["headers"])

# 3. Buscar pedidos da EcomHub
conditions = {
    "orders": {
        "date": {
            "start": "2025-08-01",
            "end": "2025-08-31"
        },
        "shippingCountry_id": [164]  # Espanha
    }
}

params = {
    "offset": 0,
    "orderBy": "null",
    "orderDirection": "null",
    "conditions": json.dumps(conditions),
    "search": ""
}

response = session.get(
    "https://api.ecomhub.app/api/orders",
    params=params
)
orders = response.json()

print(f"Total de pedidos: {len(orders)}")
```

## ❓ Perguntas Frequentes

### Quanto tempo demora para obter os tokens?
Normalmente entre 10-30 segundos, pois o serviço precisa fazer login completo no navegador.

### Os tokens expiram?
Sim, recomenda-se obter novos tokens a cada uso ou quando receber erro 401 da API EcomHub.

### Posso fazer múltiplas requisições simultâneas?
Sim, o serviço suporta requisições paralelas, mas cada uma fará login independente.

### Funciona com outros países além da Espanha?
Sim! Consulte `/api-ecomhub-docs` para lista completa de IDs de países suportados.

## 🔒 Informações Técnicas

### Tecnologias
- **FastAPI** - Framework web
- **Selenium** - Automação de navegador
- **Chrome Headless** - Browser em modo servidor
- **Railway** - Hospedagem em nuvem

### Segurança
- ✅ Credenciais protegidas por variáveis de ambiente
- ✅ Tokens não são armazenados, apenas gerados sob demanda
- ✅ Conexão HTTPS

## 📞 Suporte

**Documentação Completa:**
- API de Auth: https://ecomhub-selenium-production.up.railway.app/docs
- API EcomHub: https://ecomhub-selenium-production.up.railway.app/api-ecomhub-docs

---

## 📁 Arquivos do Projeto (Para Desenvolvedores)

Este projeto está hospedado no Railway e contém:

```
ecomhub-financeiro/
├── main.py              # Aplicação FastAPI + Selenium
├── requirements.txt     # Dependências Python
├── .env.example        # Template de configuração
├── Dockerfile          # Build Docker com Chrome
├── railway.toml        # Configuração Railway
└── README.md           # Esta documentação
```

### Deploy/Manutenção

O serviço está configurado para:
- **Auto-restart** em caso de falha (até 3 tentativas)
- **Healthcheck** em `/health`
- **Logs** disponíveis no dashboard Railway

---

**Desenvolvido para facilitar automações com a API da EcomHub** 🚀
