# 📘 Documentação Completa da API EcomHub

Esta documentação mapeia **TODOS** os campos retornados pela API oficial da EcomHub, com explicações detalhadas de cada variável.

> 💡 **Exemplo Completo**: Para ver um pedido REAL com TODAS as 69 variáveis retornadas pela API,
> consulte o arquivo **[`pedido_raw_ecomhub.json`](pedido_raw_ecomhub.json)** neste repositório.

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

### Usando Este Servidor

**Este servidor obtém tokens on-demand via Selenium!** Ao invés de fazer login manualmente, use o endpoint `/api/auth`:

```bash
# Obter tokens via Selenium on-demand
curl -H "X-API-Key: sua-chave-api" \
  https://ecomhub-selenium-production.up.railway.app/api/auth
```

**Resposta:**
```json
{
  "success": true,
  "cookies": {
    "token": "eyJhbGciOiJIUzI1...",
    "e_token": "eyJhbGciOiJIUzI1...",
    "refresh_token": "eyJhbGciOiJIUzI1..."
  },
  "cookie_string": "token=eyJ...;e_token=eyJ...;refresh_token=eyJ...",
  "headers": {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "Origin": "https://go.ecomhub.app",
    "Referer": "https://go.ecomhub.app/",
    "User-Agent": "Mozilla/5.0..."
  },
  "timestamp": "2025-11-11T14:00:00.000Z",
  "message": "Tokens obtidos com sucesso. Expiram em ~3 minutos."
}
```

**Características:**
- ⚠️ Cada requisição cria um driver Chrome e executa login (~50 segundos)
- ⏱️ Tokens expiram em aproximadamente **3 minutos**
- ✅ Endpoint disponível 24/7

### Cookies Necessários

Para chamar a API da EcomHub, use os cookies retornados pelo endpoint `/api/auth`:

| Cookie | Descrição | Fonte |
|--------|-----------|-------|
| `token` | Token de autenticação principal | `/api/auth` |
| `e_token` | Token estendido/alternativo | `/api/auth` |
| `refresh_token` | Token para renovação | `/api/auth` (opcional) |

**Duração dos Tokens:** ~3 minutos

### Headers Obrigatórios

Ao fazer requisições para `https://api.ecomhub.app/api/orders`:

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

### Exemplo Real de URL

**URL completa com conditions encodado:**
```
https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions=%7B%22orders%22%3A%7B%22date%22%3A%7B%22start%22%3A%222025-11-04%22%2C%22end%22%3A%222025-11-11%22%7D%2C%22status%22%3A%5B%22lost%22%2C%22ready_to_ship%22%5D%7D%7D&search=
```

**Decodificado, o parâmetro `conditions` acima contém:**
```json
{
  "orders": {
    "date": {
      "start": "2025-11-04",
      "end": "2025-11-11"
    },
    "status": ["lost", "ready_to_ship"]
  }
}
```

Este exemplo filtra pedidos entre 04/11/2025 e 11/11/2025 com status "perdido" ou "preparado para envio".

---

## 🌍 4. PAÍSES SUPORTADOS

Principais países utilizados neste projeto:

| País | ID | Código ISO |
|------|----|----|
| Espanha | `164` | ES |
| Croácia | `41` | HR |
| Grécia | `66` | GR |
| Itália | `82` | IT |
| Romênia | `142` | RO |
| República Checa | `44` | CZ |
| Polônia | `139` | PL |

> **⚠️ Nota:** Existem outros países disponíveis além dos listados acima. Para ver todos os IDs de países disponíveis, acesse diretamente a plataforma EcomHub em [go.ecomhub.app](https://go.ecomhub.app).

---

## 📦 5. ESTRUTURA COMPLETA DE RESPOSTA

A API retorna um **array JSON** com até 48 objetos (pedidos) por página. Abaixo está o mapeamento COMPLETO de todos os campos:

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

Lista completa de status possíveis (12 status válidos na API):

| Status | Descrição em Português | Categoria |
|--------|------------------------|-----------|
| `created` | Criado | 📋 Inicial |
| `preparing_for_shipping` | Preparando | 📦 Preparação |
| `ready_to_ship` | Preparado para envio | 📦 Preparação |
| `with_courier` | Em transito | 🚚 Em trânsito |
| `out_for_delivery` | Em processo de entrega | 🚚 Em trânsito |
| `delivered` | Entregue | ✅ Sucesso |
| `returning` | Retornando | ⚠️ Problema |
| `returned` | Retornado | ⚠️ Problema |
| `issue` | Incidencia | ⚠️ Problema |
| `lost` | Perdido | ⚠️ Problema |
| `cancelled` | Cancelado | ❌ Cancelado |
| `unknown` | Indefinido | ❓ Desconhecido |

---

## 📋 6.1. DICIONÁRIO COMPLETO DE TODAS AS VARIÁVEIS DO PEDIDO

Esta seção mapeia **TODAS** as variáveis retornadas pela API, sem exceção (120+ campos).

> 💡 **Referência**: Consulte o arquivo [`pedido_raw_ecomhub.json`](pedido_raw_ecomhub.json) para ver um exemplo real completo.

---

### 📌 NÍVEL RAIZ - Campos Principais (64 campos)

#### 🆔 IDs e Identificadores

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `id` | string (UUID) | ID único do pedido no EcomHub | `"57de214e-331b-41d5-b9fe-89cf3d0282e9"` |
| `store_id` | string (UUID) | ID da loja que vendeu o produto | `"4d640af7-be32-429d-aefd-51341b2a137f"` |
| `warehouse_id` | string (UUID) | ID do armazém de origem do pedido | `"50f69f0a-472a-4b55-ae0e-d159a96555a0"` |
| `external_id` | string | ID externo do pedido (do Shopify) | `"11734956802416"` |
| `shopifyOrderNumber` | string | Número do pedido no Shopify (sem #) | `"1507"` |
| `shopifyOrderName` | string | Nome do pedido no Shopify (com #) | `"#1507"` |
| `shippingMethod_id` | string (UUID) | ID do método de envio utilizado | `"ce7e6cf0-115e-4ddb-a808-e7f5d98bf61a"` |

#### 📅 Datas e Timestamps

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `createdAt` | string (ISO 8601) | Data/hora de criação do pedido no EcomHub | `"2025-11-11T11:31:54.000Z"` |
| `updatedAt` | string (ISO 8601) | Data/hora da última atualização | `"2025-11-11T13:21:11.000Z"` |
| `date` | string (ISO 8601) | Data/hora principal do pedido | `"2025-11-11T11:31:54.000Z"` |
| `dateDay` | string (ISO 8601) | Data do pedido sem hora (meia-noite UTC) | `"2025-11-11T00:00:00.000Z"` |
| `statusDateReturning` | string/null | Data quando entrou em status "returning" | `null` ou `"2025-11-15T10:00:00.000Z"` |
| `statusDateReturned` | string/null | Data quando foi marcado como "returned" | `null` |
| `statusDateLost` | string/null | Data quando foi marcado como "lost" | `null` |
| `statusDateCancelled` | string/null | Data quando foi cancelado | `null` |
| `statusDateWithCourier` | string/null | Data quando foi enviado à transportadora | `null` |
| `revenueReleaseDate` | string/null | Data prevista para liberação da receita | `null` |

#### 👤 Informações do Cliente

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `customerName` | string | Nome completo do cliente | `"Nela Rupenovic"` |
| `customerPhone` | string | Telefone do cliente com código do país | `"+385098495696"` |
| `customerEmail` | string/null | Email do cliente | `null` ou `"cliente@exemplo.com"` |
| `customerPreferences` | object/null | Preferências do cliente (geralmente null) | `null` |
| `companyName` | string | Nome da empresa (se aplicável) | `""` (vazio se pessoa física) |
| `companyId` | string | ID fiscal da empresa (CNPJ, VAT, etc) | `""` |

#### 📍 Endereços

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `billingAddress` | string | Endereço de cobrança completo (JSON stringificado) | `"{\"zip\":\"52440\",\"city\":\"Poreč\",...}"` |
| `shippingAddress` | string | Endereço de entrega (rua e número) | `"Eufrazijeva 4/3 "` |
| `shippingPostalCode` | string | CEP/Código Postal | `"52440"` |
| `shippingCity` | string | Cidade de entrega | `"Poreč - Parenzo"` |
| `shippingProvince` | string | Estado/Província | `""` (pode ser vazio) |
| `shippingCountry` | string | Código do país (ISO 3166-1 alpha-2) | `"hr"` (Croácia) |
| `shippingCountry_id` | integer | ID do país no sistema | `41` |

#### 💰 Valores e Preços

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `price` | string | Preço final pago pelo cliente | `"55"` (em EUR) |
| `priceOriginal` | string | Preço original antes de descontos | `"55"` |
| `currency_id` | integer | ID da moeda no sistema | `1` (EUR) |
| `paymentMethod` | string | Método de pagamento | `"cod"` (Cash on Delivery) |

**Valores de `paymentMethod`:**
- `"cod"` - Cash on Delivery (Pagamento na entrega)
- `"credit_card"` - Cartão de crédito
- `"bank_transfer"` - Transferência bancária
- Outros valores específicos da plataforma

#### 💸 Custos Operacionais

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `costCommission` | string | Comissão cobrada no pedido | `"1"` |
| `costCommissionReturn` | string | Comissão cobrada em caso de devolução | `"0.5"` |
| `costWarehouse` | string | Custo do armazém para processar pedido | `"1.5"` |
| `costWarehouseReturn` | string | Custo do armazém em caso de devolução | `"0"` |
| `costCourier` | string | Custo da transportadora | `"6.16"` |
| `costCourierReturn` | string | Custo da transportadora em devoluções | `"0"` |
| `costPaymentMethod` | string | Custo/taxa do método de pagamento | `"0"` |
| `isCostManuallyOverwritten` | boolean | Se os custos foram alterados manualmente | `false` |

#### 📦 Envio e Rastreamento

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `origin` | string | Plataforma de origem do pedido | `"shopify_api"` |
| `waybill` | string | Código de rastreamento da transportadora | `"17502054388772"` |
| `trackingUrl` | string | URL base para rastreamento | `"https://gls-group.eu/HR/en/parcel-tracking/"` |
| `weight` | integer | Peso do pacote em gramas | `400` (400g) |
| `volume` | integer | Volume do pacote | `1` |
| `volumetricWeight` | string | Peso volumétrico calculado | `"0"` |
| `weightVolumetricFactor` | integer | Fator de conversão peso volumétrico | `500000` |

#### 📊 Status e Controle

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `status` | string | Status atual do pedido (ver seção 6) | `"ready_to_ship"` |
| `isTest` | boolean | Se é um pedido de teste | `false` |
| `note` | string/null | Observações sobre o pedido | `null` |
| `raw` | string | JSON stringificado com dados brutos do Shopify | `"{\"store_id\":\"...\"}"` |
| `revenueReleaseWindow` | integer | Janela de dias para liberação da receita | `7` |

#### ⚠️ Gestão de Problemas

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `issue` | boolean/null | Se há algum problema com o pedido | `null` ou `true` |
| `issueDescription` | string/null | Descrição do problema | `null` ou `"Cliente não encontrado"` |
| `issueResolution` | string/null | Tipo de resolução aplicada | `null` ou `"reenvio"` |
| `issueResolutionDetail` | string/null | Detalhes da resolução | `null` |
| `issueResolution_by` | string/null | Quem resolveu o problema (user ID) | `null` |
| `isIssueResolutable` | boolean/null | Se o problema pode ser resolvido | `null` ou `true` |
| `issueResolutionUrl` | string/null | URL relacionada à resolução | `null` |
| `errorCode` | string/null | Código de erro técnico | `null` |
| `errorDetails` | string/null | Detalhes técnicos do erro | `null` |

---

### 🌍 OBJETOS RELACIONADOS - Nível Raiz

#### `countries` (1 campo)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `countries.name` | string | Nome do país em inglês | `"Croatia"` |

#### `stores` (2 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `stores.id` | string (UUID) | ID da loja | `"4d640af7-be32-429d-aefd-51341b2a137f"` |
| `stores.name` | string | Nome da loja | `"MirisneLux HR"` |

#### `warehouses` (7 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `warehouses.id` | string (UUID) | ID do armazém | `"50f69f0a-472a-4b55-ae0e-d159a96555a0"` |
| `warehouses.namePublic` | string | Nome público do armazém | `"EU - Leste"` |
| `warehouses.status` | string | Status operacional do armazém | `"active"` |
| `warehouses.cost` | string | Custo padrão de processamento | `"1.5"` |
| `warehouses.costReturn` | string | Custo de processamento de devoluções | `"0"` |
| `warehouses.costPerUnit` | string | Custo por unidade processada | `"0"` |
| `warehouses.costPerUnitReturn` | string | Custo por unidade em devoluções | `"0"` |

#### `currencies` (2 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `currencies.id` | integer | ID da moeda no sistema | `1` |
| `currencies.code` | string | Código ISO da moeda | `"EUR"` |

#### `shippingMethods` e `couriers` (2 campos + 1 subcampo)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `shippingMethods.name` | string | Nome do método de envio | `"GLS - Croácia"` |
| `shippingMethods.couriers` | object | Dados da transportadora | `{...}` |
| `shippingMethods.couriers.name` | string | Nome da empresa transportadora | `"GLS - HS"` |

---

### 📦 ARRAY `ordersItems` - Itens do Pedido

**⚠️ IMPORTANTE:** `ordersItems` é um **array** que pode conter múltiplos itens. Cada item representa um produto no pedido.

#### Campos Diretos do Item (12 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `ordersItems[].id` | string (UUID) | ID único do item no pedido | `"d367f2fd-42a9-4ff3-b4bd-e8f60e1e23b8"` |
| `ordersItems[].order_id` | string (UUID) | ID do pedido pai | `"57de214e-331b-41d5-b9fe-89cf3d0282e9"` |
| `ordersItems[].external_id` | string/null | ID externo do item | `null` |
| `ordersItems[].description` | string/null | Descrição do item | `null` |
| `ordersItems[].price` | string | Preço deste item específico | `"55"` |
| `ordersItems[].priceOriginal` | string | Preço original do item | `"55"` |
| `ordersItems[].cost` | string | Custo de aquisição do item | `"15"` |
| `ordersItems[].unitsPerBundle` | integer | Unidades por pacote | `1` |
| `ordersItems[].productsVariant_id` | string (UUID) | ID da variante do produto | `"ccbc028a-c965-41bd-a971-27d1898b03a6"` |
| `ordersItems[].stockEntry_id` | string (UUID) | ID da entrada de estoque | `"b048c18a-a86a-45aa-9cd6-eda0a924cc86"` |
| `ordersItems[].group` | integer | Grupo do item (para agrupamento) | `0` |
| `ordersItems[].productsVariants` | object | **Dados da variante do produto** | `{...}` |
| `ordersItems[].stockEntries` | object | **Dados de estoque** | `{...}` |

---

### 🎨 `ordersItems[].productsVariants` - Variantes do Produto (10 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `productsVariants.id` | string (UUID) | ID da variante | `"ccbc028a-c965-41bd-a971-27d1898b03a6"` |
| `productsVariants.product_id` | string (UUID) | ID do produto pai | `"9d067218-aa9c-4e0e-8d84-dd9a3292eb79"` |
| `productsVariants.stockItem_id` | string (UUID) | ID do item de estoque | `"9335943a-4568-4533-a7f7-941ef6464b10"` |
| `productsVariants.featuredImage` | string/null | Imagem destacada da variante | `null` ou `"/path/image.jpg"` |
| `productsVariants.description` | string/null | Descrição da variante | `null` |
| `productsVariants.quantity` | integer | Quantidade da variante | `1` |
| `productsVariants.price` | string | Preço adicional da variante | `"0"` |
| `productsVariants.order` | integer/null | Ordem de exibição | `null` |
| `productsVariants.isRemoved` | boolean | Se a variante foi removida | `false` |
| `productsVariants.attributes` | string | Atributos da variante (tamanho, cor, etc) | `"Kit 2 perfumes + 1 creme flash"` |
| `productsVariants.products` | object | **Dados do produto principal** | `{...}` |

---

### 🛍️ `productsVariants.products` - Produto Principal (11 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `products.id` | string (UUID) | ID do produto | `"9d067218-aa9c-4e0e-8d84-dd9a3292eb79"` |
| `products.name` | string | **Nome do produto** | `"Combo de 4 Perfumes Feminino com 2 cremes"` |
| `products.isBundle` | boolean | Se é um pacote/combo de produtos | `true` |
| `products.createdAt` | string (ISO 8601) | Data de criação do produto | `"2025-05-15T15:11:02.000Z"` |
| `products.variantsAttributes` | array/null | Atributos das variantes disponíveis | `null` |
| `products.featuredImage` | string | **Caminho da imagem principal** | `"/public/products/featuredImage-1749650632737-ff41516c.png"` |
| `products.description` | string | Descrição do produto | `"Combo de 4 Perfume + 2 Cremes\nKit Plutores\nKit Flash"` |
| `products.status` | string | Status do produto no catálogo | `"active"` |
| `products.provider_id` | string (UUID) | ID do fornecedor do produto | `"c1d6424f-ce8c-461a-ba04-6c97c8719fae"` |
| `products.price` | string | Preço base do produto | `"15"` |
| `products.analyzis` | string/null | Análises ou dados adicionais | `null` |

**🖼️ URL completa da imagem:**
```
https://api.ecomhub.app{products.featuredImage}
Exemplo: https://api.ecomhub.app/public/products/featuredImage-1749650632737-ff41516c.png
```

---

### 📊 `ordersItems[].stockEntries` - Entradas de Estoque (8 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `stockEntries.id` | string (UUID) | ID da entrada de estoque | `"b048c18a-a86a-45aa-9cd6-eda0a924cc86"` |
| `stockEntries.warehouse_id` | string (UUID) | ID do armazém | `"50f69f0a-472a-4b55-ae0e-d159a96555a0"` |
| `stockEntries.stockItem_id` | string (UUID) | ID do item de estoque | `"9335943a-4568-4533-a7f7-941ef6464b10"` |
| `stockEntries.quantity` | integer | Quantidade movimentada (negativo = saída) | `-1` |
| `stockEntries.isProcessed` | boolean | Se a movimentação foi processada | `true` |
| `stockEntries.note` | string/null | Observações sobre a movimentação | `null` |
| `stockEntries.created_by` | string/null | Usuário que criou a entrada | `null` |
| `stockEntries.createdAt` | string (ISO 8601) | Data da movimentação | `"2025-11-11T11:31:54.000Z"` |
| `stockEntries.stockItems` | object | **Dados do item de estoque** | `{...}` |

---

### 📦 `stockEntries.stockItems` - Item de Estoque (13 campos)

| Campo | Tipo | Descrição | Exemplo |
|-------|------|-----------|---------|
| `stockItems.id` | string (UUID) | ID do item de estoque | `"9335943a-4568-4533-a7f7-941ef6464b10"` |
| `stockItems.label` | string/null | Etiqueta/rótulo do item | `null` |
| `stockItems.attributesValues` | object/null | Valores de atributos específicos | `null` |
| `stockItems.sku` | string | **SKU (código do produto)** | `"missvivienne"` |
| `stockItems.description` | string/null | Descrição do item | `null` |
| `stockItems.weight` | integer | Peso em gramas | `400` |
| `stockItems.width` | integer | Largura em cm | `1` |
| `stockItems.length` | integer | Comprimento em cm | `1` |
| `stockItems.height` | integer | Altura em cm | `1` |
| `stockItems.isStockUntracked` | boolean | Se não rastreia estoque | `false` |
| `stockItems.featuredImage` | string/null | Imagem do item de estoque | `null` |
| `stockItems.createdAt` | string (ISO 8601) | Data de criação | `"2025-05-15T14:40:29.000Z"` |
| `stockItems.provider_id` | string (UUID) | ID do fornecedor | `"c1d6424f-ce8c-461a-ba04-6c97c8719fae"` |

---

### 📊 RESUMO TOTAL

**Campos por categoria:**
- **Nível raiz:** 64 campos
- **Objetos relacionados:** 15 campos (countries, stores, warehouses, currencies, shippingMethods)
- **ordersItems (item):** 12 campos
- **productsVariants:** 10 campos
- **products:** 11 campos
- **stockEntries:** 8 campos
- **stockItems:** 13 campos

**TOTAL: 133 campos únicos mapeados** ✅

---

### 💡 CAMPOS MAIS IMPORTANTES PARA CADA CASO DE USO

**Para tracking/rastreamento:**
- `waybill`, `trackingUrl`, `status`, `shippingMethods.couriers.name`

**Para financeiro:**
- `price`, `priceOriginal`, `costCourier`, `costWarehouse`, `costCommission`, `paymentMethod`

**Para logística:**
- `warehouse_id`, `warehouses.namePublic`, `weight`, `volume`, `shippingCountry`

**Para produto:**
- `ordersItems[].productsVariants.products.name`, `ordersItems[].productsVariants.products.featuredImage`
- `ordersItems[].stockEntries.stockItems.sku`

**Para cliente:**
- `customerName`, `customerEmail`, `customerPhone`, `shippingAddress`, `shippingCity`, `shippingCountry`

**Para análise de problemas:**
- `issue`, `issueDescription`, `issueResolution`, `errorCode`, `errorDetails`, `status`

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

## ⚠️ 8. TRATAMENTO DE ERROS

| Status HTTP | Significado | Ação |
|-------------|-------------|------|
| `200` | Sucesso | Processar array de pedidos |
| `401` | Não autorizado | Tokens expirados - renovar login |
| `403` | Acesso negado | Verificar cookies |
| `429` | Rate limit excedido | Aguardar antes de nova requisição |
| `500` | Erro interno | Tentar novamente após alguns segundos |

---

## 📌 9. CAMPOS MAIS IMPORTANTES

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