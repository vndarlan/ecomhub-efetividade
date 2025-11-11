# 📘 Documentação Completa da API EcomHub

Esta documentação mapeia **TODOS** os campos retornados pela API oficial da EcomHub, com explicações detalhadas de cada variável.

---

## 🔗 Informações Básicas

| Item | Valor |
|------|-------|
| **URL Base** | `https://api.ecomhub.app/api/orders` |
| **Método** | `GET` |
| **Autenticação** | Cookie-based (sessão) |
| **Formato de Resposta** | JSON Array |
| **Limite por Página** | 48 pedidos |
| **Paginação** | Via parâmetro `offset` |

---

## 🔐 1. AUTENTICAÇÃO

### Cookies Necessários

A API requer cookies de sessão obtidos após login em `https://go.ecomhub.app/login`:

| Cookie | Descrição | Obrigatório |
|--------|-----------|-------------|
| `token` | Token de autenticação principal | ✅ Sim |
| `e_token` | Token estendido/alternativo | ✅ Sim |
| `refresh_token` | Token para renovação de sessão | ⚠️ Recomendado |

**Duração dos Tokens:** ~3 minutos (requer renovação frequente)

### Headers Obrigatórios

```http
Accept: */*
Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7
Origin: https://go.ecomhub.app
Referer: https://go.ecomhub.app/
X-Requested-With: XMLHttpRequest
Content-Type: application/json
```

---

## 📋 2. PARÂMETROS DE REQUISIÇÃO

Todos os parâmetros são passados via **Query String**:

| Parâmetro | Tipo | Obrigatório | Descrição | Exemplo |
|-----------|------|-------------|-----------|---------|
| `offset` | integer | Sim | Número da página (0 = primeira) | `0`, `1`, `2` |
| `orderBy` | string | Sim | Campo para ordenação (use `"null"`) | `"null"` |
| `orderDirection` | string | Sim | Direção (`"asc"`, `"desc"` ou `"null"`) | `"null"` |
| `conditions` | JSON string | Sim | Filtros complexos (veja abaixo) | `"{\"orders\":{...}}"` |
| `search` | string | Não | Termo de busca livre | `""` ou `"João"` |

---

## 🔍 3. ESTRUTURA DO PARÂMETRO `conditions`

O parâmetro `conditions` é um **JSON stringificado** que contém todos os filtros:

### Estrutura Básica

```json
{
  "orders": {
    "date": {
      "start": "2025-10-01",
      "end": "2025-10-31"
    },
    "shippingCountry_id": [164, 82, 66]
  }
}
```

### Campos Disponíveis em `orders`

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `date.start` | string (YYYY-MM-DD) | Data início (inclusive) | `"2025-10-01"` |
| `date.end` | string (YYYY-MM-DD) | Data fim (inclusive) | `"2025-10-31"` |
| `shippingCountry_id` | array[integer] | IDs dos países para filtrar | `[164]` ou `[164, 82]` |
| `status` | array[string] | **OPCIONAL**: Filtrar por status específicos | `["delivered", "shipped"]` |

**⚠️ IMPORTANTE:** Você DEVE converter o objeto JSON para string antes de enviar:

```python
import json
conditions = {"orders": {...}}
conditions_str = json.dumps(conditions)  # Converter para string!
```

---

## 🌍 4. PAÍSES SUPORTADOS

| País | ID | Código ISO |
|------|----|----|
| Espanha | `164` | ES |
| Croácia | `41` | HR |
| Grécia | `66` | GR |
| Itália | `82` | IT |
| Romênia | `142` | RO |
| República Checa | `44` | CZ |
| Polônia | `139` | PL |

---

## 📦 5. ESTRUTURA COMPLETA DE RESPOSTA

A API retorna um **array JSON** com até 48 objetos (pedidos). Abaixo está o mapeamento COMPLETO de todos os campos:

### 5.1. Campos de Identificação

```json
{
  "id": 12345,
  "external_id": "ext_abc123",
  "shopifyOrderNumber": "1041",
  "shopifyOrderName": "#1041"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `id` | integer | ID interno do pedido no EcomHub |
| `external_id` | string | ID externo/original do pedido |
| `shopifyOrderNumber` | string | Número do pedido no Shopify (sem #) |
| `shopifyOrderName` | string | Nome do pedido no Shopify (com #) |

---

### 5.2. Status e Datas

```json
{
  "status": "delivered",
  "createdAt": "2025-10-01T10:00:00.000Z",
  "updatedAt": "2025-10-15T14:30:00.000Z",
  "date": "2025-10-01T10:00:00.000Z",
  "dateDay": "2025-10-01",

  "statusDateReturning": null,
  "statusDateReturned": "2025-10-20T10:00:00.000Z",
  "statusDateLost": null,
  "statusDateCancelled": null,
  "statusDateWithCourier": "2025-10-05T08:00:00.000Z"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `status` | string | Status atual do pedido (ver seção 6) |
| `createdAt` | string (ISO 8601) | Data/hora de criação do pedido |
| `updatedAt` | string (ISO 8601) | Data/hora da última atualização |
| `date` | string (ISO 8601) | Data principal do pedido |
| `dateDay` | string (YYYY-MM-DD) | Data sem hora (apenas dia) |
| `statusDateReturning` | string/null | Data/hora quando entrou em devolução |
| `statusDateReturned` | string/null | Data/hora quando foi devolvido |
| `statusDateLost` | string/null | Data/hora quando foi marcado como perdido |
| `statusDateCancelled` | string/null | Data/hora de cancelamento |
| `statusDateWithCourier` | string/null | Data/hora quando foi enviado à transportadora |

---

### 5.3. Informações do Cliente

```json
{
  "customerName": "João Silva",
  "customerEmail": "joao@example.com",
  "customerPhone": "+55 11 99999-9999",
  "customerPreferences": {}
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `customerName` | string | Nome completo do cliente |
| `customerEmail` | string | Email do cliente |
| `customerPhone` | string | Telefone com código do país |
| `customerPreferences` | object | Preferências do cliente (geralmente vazio) |

---

### 5.4. Endereços

```json
{
  "billingAddress": "Rua A, 123, Apto 45",
  "shippingAddress": "Rua B, 456",
  "shippingPostalCode": "12345-000",
  "shippingCity": "São Paulo",
  "shippingProvince": "SP",
  "shippingCountry": "Brasil",
  "shippingCountry_id": 164
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `billingAddress` | string | Endereço de cobrança completo |
| `shippingAddress` | string | Endereço de entrega (rua e número) |
| `shippingPostalCode` | string | CEP/Código Postal |
| `shippingCity` | string | Cidade de entrega |
| `shippingProvince` | string | Estado/Província (código) |
| `shippingCountry` | string | Nome do país em português |
| `shippingCountry_id` | integer | ID do país (ver seção 4) |

---

### 5.5. Valores e Pagamento

```json
{
  "price": "29.99",
  "priceOriginal": "39.99",
  "currency_id": 1,
  "paymentMethod": "credit_card"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `price` | string | Preço final pago (com desconto) |
| `priceOriginal` | string | Preço original (antes do desconto) |
| `currency_id` | integer | ID da moeda (ver `currencies.code`) |
| `paymentMethod` | string | Método de pagamento usado |

---

### 5.6. Envio e Rastreamento

```json
{
  "waybill": "BR123456789",
  "trackingUrl": "https://tracking.carrier.com/?waybill=BR123456789",
  "weight": "500",
  "volume": "10"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `waybill` | string | Código de rastreamento do pedido |
| `trackingUrl` | string | URL completa para rastreamento |
| `weight` | string | Peso do pacote (gramas) |
| `volume` | string | Volume do pacote |

---

### 5.7. Loja e Armazém

```json
{
  "store_id": 5,
  "warehouse_id": 2,

  "stores": {
    "id": 5,
    "name": "Loja Principal"
  },
  "warehouses": {
    "id": 2,
    "name": "Armazém SP"
  }
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `store_id` | integer | ID da loja que vendeu |
| `warehouse_id` | integer | ID do armazém de origem |
| `stores` | object | Dados completos da loja |
| `stores.id` | integer | ID da loja |
| `stores.name` | string | Nome da loja |
| `warehouses` | object | Dados completos do armazém |

---

### 5.8. Questões/Problemas

```json
{
  "issue": false,
  "issueDescription": null,
  "issueResolution": null,
  "issueResolutionDetail": null,
  "isIssueResolutable": true
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `issue` | boolean | Se há algum problema com o pedido |
| `issueDescription` | string/null | Descrição do problema |
| `issueResolution` | string/null | Resolução aplicada |
| `issueResolutionDetail` | string/null | Detalhes da resolução |
| `isIssueResolutable` | boolean | Se o problema pode ser resolvido |

---

### 5.9. Origem e Flags

```json
{
  "origin": "shopify",
  "isTest": false
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `origin` | string | Plataforma de origem (`"shopify"`, etc) |
| `isTest` | boolean | Se é um pedido de teste |

---

### 5.10. Objetos Relacionados

```json
{
  "countries": {
    "id": 164,
    "name": "Espanha",
    "code": "ES"
  },
  "currencies": {
    "id": 1,
    "code": "EUR",
    "symbol": "€"
  },
  "shippingMethods": {
    "id": 3,
    "name": "Correios"
  }
}
```

| Objeto | Descrição | Campos Importantes |
|--------|-----------|-------------------|
| `countries` | Dados do país | `id`, `name`, `code` |
| `currencies` | Dados da moeda | `id`, `code`, `symbol` |
| `shippingMethods` | Método de envio | `id`, `name` |

---

### 5.11. **Itens do Pedido** (`ordersItems`)

**⚠️ IMPORTANTE:** Este é um **array** que contém todos os produtos do pedido.

```json
{
  "ordersItems": [
    {
      "id": 999,
      "price": "29.99",
      "quantity": 2,

      "productsVariants": {
        "id": 888,
        "sku": "PROD-VAR-123",

        "products": {
          "id": 777,
          "name": "Nome do Produto",
          "description": "Descrição do produto",
          "featuredImage": "/images/product-123.jpg"
        }
      },

      "stockEntries": {
        "stockItems": {
          "sku": "SKU-123-45",
          "barcode": "7891234567890"
        }
      }
    }
  ]
}
```

#### Estrutura de `ordersItems`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `ordersItems` | array | Lista de itens/produtos do pedido |
| `ordersItems[].id` | integer | ID do item do pedido |
| `ordersItems[].price` | string | Preço deste item |
| `ordersItems[].quantity` | integer | Quantidade deste item |

#### Estrutura de `productsVariants`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `productsVariants` | object | Variante do produto (tamanho, cor, etc) |
| `productsVariants.id` | integer | ID da variante |
| `productsVariants.sku` | string | SKU da variante |

#### Estrutura de `products`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `products` | object | Dados do produto principal |
| `products.id` | integer | ID do produto |
| `products.name` | string | **Nome do produto** |
| `products.description` | string | Descrição do produto |
| `products.featuredImage` | string | **Caminho da imagem principal** |

**URL completa da imagem:**
```
https://api.ecomhub.app/public/products/{featuredImage}
```

#### Estrutura de `stockEntries`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `stockEntries` | object | Informações de estoque |
| `stockEntries.stockItems` | object | Item de estoque |
| `stockEntries.stockItems.sku` | string | SKU do item em estoque |
| `stockEntries.stockItems.barcode` | string | Código de barras |

---

### 5.12. Dados Brutos (Raw)

```json
{
  "raw": "{\"lineItems\":[...]}"
}
```

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `raw` | string | JSON stringificado com dados brutos do Shopify |

---

## 📊 6. STATUS DE PEDIDOS

Lista completa de status possíveis:

| Status | Descrição em Português | Categoria |
|--------|------------------------|-----------|
| `delivered` | Entregue | ✅ Sucesso |
| `with_courier` | Com transportadora | 🚚 Em trânsito |
| `out_for_delivery` | Saiu para entrega | 🚚 Em trânsito |
| `preparing_for_shipping` | Preparando para envio | 📦 Preparação |
| `ready_to_ship` | Pronto para enviar | 📦 Preparação |
| `shipped` | Enviado | 🚚 Em trânsito |
| `returning` | Em devolução | ⚠️ Problema |
| `returned` | Devolvido | ⚠️ Problema |
| `issue` | Com problema | ⚠️ Problema |
| `cancelled` / `canceled` / `cancelado` | Cancelado | ❌ Cancelado |
| `processing` | Processando | 📋 Inicial |
| `pending` | Pendente | 📋 Inicial |

---

## 🔢 7. PAGINAÇÃO

A API retorna **no máximo 48 pedidos por página**. Para obter todos os pedidos:

```python
page = 0
all_orders = []

while True:
    params = {
        "offset": page,
        "orderBy": "null",
        "orderDirection": "null",
        "conditions": json.dumps(conditions),
        "search": ""
    }

    response = session.get(API_URL, params=params)
    orders = response.json()

    if not orders or len(orders) == 0:
        break  # Fim: nenhum pedido retornado

    all_orders.extend(orders)
    page += 1  # Próxima página
```

**Como saber se é a última página:**
- Retorna array vazio `[]`
- Retorna menos de 48 pedidos

---

## 💡 8. EXEMPLOS PRÁTICOS

### 8.1. Requisição Completa em Python

```python
import requests
import json

# 1. Obter cookies (via Selenium após login)
cookies = {
    'token': 'seu_token_aqui',
    'e_token': 'seu_e_token_aqui',
    'refresh_token': 'seu_refresh_token_aqui'
}

# 2. Headers
headers = {
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9",
    "Origin": "https://go.ecomhub.app",
    "Referer": "https://go.ecomhub.app/",
    "X-Requested-With": "XMLHttpRequest"
}

# 3. Filtros
conditions = {
    "orders": {
        "date": {
            "start": "2025-10-01",
            "end": "2025-10-31"
        },
        "shippingCountry_id": [164]  # Espanha
    }
}

# 4. Parâmetros
params = {
    "offset": 0,
    "orderBy": "null",
    "orderDirection": "null",
    "conditions": json.dumps(conditions),  # IMPORTANTE: converter para string!
    "search": ""
}

# 5. Fazer requisição
response = requests.get(
    "https://api.ecomhub.app/api/orders",
    params=params,
    headers=headers,
    cookies=cookies,
    timeout=60
)

# 6. Processar resposta
if response.status_code == 200:
    orders = response.json()
    print(f"Total: {len(orders)} pedidos")

    for order in orders:
        print(f"Pedido #{order['shopifyOrderNumber']}")
        print(f"Status: {order['status']}")
        print(f"Cliente: {order['customerName']}")

        # Acessar produto
        if order['ordersItems']:
            product_name = order['ordersItems'][0]['productsVariants']['products']['name']
            print(f"Produto: {product_name}")
```

### 8.2. Requisição cURL

```bash
curl -X GET "https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions=%7B%22orders%22%3A%7B%22date%22%3A%7B%22start%22%3A%222025-10-01%22%2C%22end%22%3A%222025-10-31%22%7D%2C%22shippingCountry_id%22%3A%5B164%5D%7D%7D&search=" \
  -H "Accept: */*" \
  -H "Accept-Language: pt-BR,pt;q=0.9" \
  -H "Origin: https://go.ecomhub.app" \
  -H "Referer: https://go.ecomhub.app/" \
  -H "Cookie: token=SEU_TOKEN; e_token=SEU_E_TOKEN"
```

### 8.3. Filtrar por Status Específicos

```python
conditions = {
    "orders": {
        "date": {"start": "2025-10-01", "end": "2025-10-31"},
        "shippingCountry_id": [164],
        "status": ["delivered", "shipped", "with_courier"]  # Apenas estes status
    }
}
```

### 8.4. Múltiplos Países

```python
conditions = {
    "orders": {
        "date": {"start": "2025-10-01", "end": "2025-10-31"},
        "shippingCountry_id": [164, 82, 66]  # Espanha, Itália, Grécia
    }
}
```

---

## ⚠️ 9. TRATAMENTO DE ERROS

| Status HTTP | Significado | Ação |
|-------------|-------------|------|
| `200` | Sucesso | Processar array de pedidos |
| `401` | Não autorizado | Tokens expirados - renovar login |
| `403` | Acesso negado | Verificar cookies |
| `429` | Rate limit excedido | Aguardar antes de nova requisição |
| `500` | Erro interno | Tentar novamente após alguns segundos |

---

## 📌 10. CAMPOS MAIS IMPORTANTES

Para a maioria dos casos de uso, estes são os campos essenciais:

| Campo | Para que serve |
|-------|----------------|
| `id` | Identificar pedido único |
| `shopifyOrderNumber` | Número legível do pedido |
| `status` | Status atual (entregue, enviado, etc) |
| `date` / `createdAt` | Quando o pedido foi criado |
| `customerName` | Nome do cliente |
| `customerEmail` | Contato do cliente |
| `shippingCountry` | País de destino |
| `shippingAddress` | Endereço de entrega |
| `price` | Valor pago |
| `waybill` | Código de rastreamento |
| `ordersItems[0].productsVariants.products.name` | Nome do produto |
| `ordersItems[0].productsVariants.products.featuredImage` | Imagem do produto |

---

## 🚀 11. DICAS E BOAS PRÁTICAS

### 11.1. Renovação de Tokens

**⚠️ CRÍTICO:** Tokens expiram em ~3 minutos!

```python
# Renovar tokens a cada 2 minutos
import time
last_refresh = time.time()

while True:
    if time.time() - last_refresh > 120:  # 2 minutos
        cookies = refresh_tokens()  # Fazer novo login
        last_refresh = time.time()

    # Fazer requisições...
```

### 11.2. Otimização de Requisições

- **Use paginação**: Não tente carregar todos os pedidos de uma vez
- **Filtre por país**: Reduz volume de dados
- **Use períodos curtos**: Máximo 30-90 dias por requisição
- **Cache de resultados**: Armazene localmente para evitar requisições repetidas

### 11.3. Extração de Dados

```python
# Extrair imagem completa
image_path = order['ordersItems'][0]['productsVariants']['products']['featuredImage']
full_image_url = f"https://api.ecomhub.app/public/products{image_path}"

# Acessar dados aninhados com segurança
product_name = (order.get('ordersItems', [{}])[0]
                .get('productsVariants', {})
                .get('products', {})
                .get('name', 'N/A'))
```

---

## 📝 12. NOTAS FINAIS

- **Formato de Datas:** Todas as datas estão em **UTC** no formato ISO 8601
- **Encoding:** Sempre use **UTF-8** para caracteres especiais
- **Timeout:** Recomenda-se timeout de **60 segundos** por requisição
- **Rate Limiting:** A API não documenta limites, mas use com moderação

---

## 📞 13. SUPORTE

Esta documentação foi gerada através da análise do código fonte do projeto `ecomhub-api`.

Para dúvidas ou atualizações, consulte o código em:
- `main.py` - Funções `extract_via_api()` e `extract_orders_for_tracking()`
- `CLAUDE.md` - Instruções do projeto

---

**Última atualização:** 2025-11-11
**Versão:** 1.0.0
**Status:** ✅ Documentação Completa

---

🤖 Gerado com análise detalhada do código fonte
