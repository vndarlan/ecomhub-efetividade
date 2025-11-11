# Configuração n8n para Sincronização de Tokens EcomHub

Esta pasta contém a configuração **interna** para usar o n8n como scheduler externo para renovação automática de tokens do EcomHub.

> ⚠️ **Nota**: Esta é uma documentação de **configuração interna**. Para documentação da API pública, consulte o [README.md principal](../README.md).

---

## 📋 Sobre

O n8n é usado para chamar periodicamente o endpoint `/api/sync-tokens` que faz login no EcomHub e atualiza os tokens no banco de dados. Isso garante que os tokens estejam sempre válidos para os consumidores da API.

**Por que usar n8n?**
- ✅ Sem sobreposição de jobs (n8n aguarda resposta)
- ✅ Timeout configurável (máximo 2 minutos)
- ✅ Retry inteligente em caso de falha
- ✅ Dashboard visual de execuções
- ✅ Alertas fáceis de configurar
- ✅ Controle granular de erros consecutivos

---

## 🔄 Fluxo de Funcionamento

```
┌─────────────────────────────────────────────────────────┐
│  n8n (Renovador Externo)                                │
│  ↓                                                       │
│  Schedule Trigger (a cada 2 minutos)                    │
│  ↓                                                       │
│  POST /api/sync-tokens                                  │
│  ↓                                                       │
│  API faz login no EcomHub → salva tokens no banco      │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  Banco de Dados  │
                │  (tokens válidos) │
                └──────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│  Consumidores da API                                     │
│  ↓                                                       │
│  GET /api/auth (quando precisam de tokens)              │
│  ↓                                                       │
│  Recebem tokens válidos para usar na API EcomHub        │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Configuração

### 1. Importar Workflow no n8n

1. Acesse seu n8n
2. Vá em **Workflows** → **Import from file**
3. Selecione o arquivo [`n8n-sync-workflow.json`](./n8n-sync-workflow.json)
4. Clique em **Import**

### 2. Configurar Variáveis de Ambiente

**No n8n**, adicione as seguintes variáveis de ambiente:

```bash
API_URL=https://sua-api.railway.app
SYNC_API_KEY=sua-chave-secreta-forte-aqui
```

**No Railway** (sua API), configure:

```bash
SYNC_API_KEY=mesma-chave-secreta-forte-aqui
TOKEN_SYNC_ENABLED=false  # Desabilitar scheduler interno
```

### 3. Ativar o Workflow

1. Abra o workflow importado
2. Clique no botão **Active** no canto superior direito
3. Verifique se o status mudou para "Active"

---

## 📊 Estrutura do Workflow

O workflow possui os seguintes nós:

1. **Schedule Trigger** - Dispara a cada 2 minutos
2. **POST Sync Tokens** - Faz requisição para `/api/sync-tokens`
3. **Verificar Sucesso** - Verifica se a sincronização foi bem-sucedida
4. **Log Sucesso** - Registra sucesso e reseta contador de erros
5. **Log Erro** - Registra erro e incrementa contador
6. **3+ Erros?** - Verifica se houve 3 ou mais erros consecutivos
7. **Enviar Alerta** - Envia alerta em caso de múltiplas falhas
8. **Reset Contador Erros** - Zera contador após sucesso

### Fluxo de Execução

```
Trigger (2min)
    ↓
POST /api/sync-tokens
    ↓
Verificar Sucesso?
    ├─ ✅ SIM → Log Sucesso → Reset Contador
    └─ ❌ NÃO → Log Erro → 3+ Erros?
                              ├─ SIM → Enviar Alerta
                              └─ NÃO → (Aguarda próximo ciclo)
```

---

## ⚙️ Endpoint: POST /api/sync-tokens

### Request

```http
POST https://sua-api.railway.app/api/sync-tokens
X-Sync-Key: sua-chave-sync-api
```

### Response (Sucesso - 200)

```json
{
  "success": true,
  "message": "Sincronização concluída com sucesso",
  "sync_number": 42,
  "timestamp": "2024-11-08T15:30:00Z",
  "next_sync_in_minutes": 2
}
```

### Response (Erro - 500)

```json
{
  "success": false,
  "error": "Erro ao fazer login no EcomHub",
  "detail": "Timeout ao aguardar elemento de login"
}
```

---

## 🔔 Configurar Alertas (Opcional)

O workflow já possui lógica para detectar **3 ou mais falhas consecutivas**. Para receber alertas, conecte um nó após o **"Enviar Alerta"**:

### Slack

1. Adicione um nó **Slack** após "Enviar Alerta"
2. Configure suas credenciais do Slack
3. Use a variável `{{$json.message}}` como texto da mensagem

### Discord

1. Adicione um nó **Discord** após "Enviar Alerta"
2. Configure o Webhook URL
3. Use a variável `{{$json.message}}` como conteúdo

### Email

1. Adicione um nó **Send Email** após "Enviar Alerta"
2. Configure seu servidor SMTP
3. Subject: `🚨 ALERTA: {{$json.consecutive_errors}} falhas no Token Sync`
4. Body: `{{$json.message}}`

---

## ⏰ Timing e Sincronização

**⚠️ IMPORTANTE:** Os tokens do EcomHub expiram a cada **3 minutos**.

- **Intervalo do n8n**: 2 minutos
- **Margem de segurança**: 1 minuto
- **Timeout da requisição**: 120 segundos (2 minutos)
- **Retries**: 2 tentativas com intervalo de 10 segundos

---

## 📝 Logs e Monitoramento

### Ver Execuções no n8n

1. Vá em **Executions** no menu lateral
2. Veja histórico de todas as execuções
3. Clique em uma execução para ver detalhes

### Ver Logs da API

```bash
# Via Railway CLI
railway logs

# Via Dashboard
https://railway.app → Seu Projeto → Deployments → View Logs
```

### Verificar Status dos Tokens

```bash
curl -H "X-API-Key: sua-chave" https://sua-api.railway.app/api/auth/status
```

---

## 📚 Arquivos nesta Pasta

| Arquivo | Descrição |
|---------|-----------|
| [`n8n-sync-workflow.json`](./n8n-sync-workflow.json) | Workflow completo do n8n para importação |
| [`README.md`](./README.md) | Este arquivo - documentação de configuração |

---

## 🔗 Links Úteis

- [Documentação do n8n](https://docs.n8n.io/)
- [Railway Documentation](https://docs.railway.app/)
- [README Principal da API](../README.md)
- [Documentação da API EcomHub](../ECOMHUB_API_DOCUMENTATION.md)

---

**Última atualização:** 2025-11-11
**Versão do Workflow:** 1.0.0
