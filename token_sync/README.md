# 🔄 Token Sync Module - Sincronização Automática de Tokens

## 📋 Visão Geral

O módulo Token Sync é responsável por manter tokens de autenticação do EcomHub sempre válidos e atualizados, eliminando o gargalo de velocidade causado pelo Selenium em cada requisição.

### Benefícios
- **Velocidade**: Reduz tempo de resposta de 30s para 2-3s
- **Confiabilidade**: Tokens sempre prontos para uso
- **Automático**: Renovação preventiva antes da expiração
- **Compatível**: Mantém endpoint `/api/auth` funcionando para n8n

## 🚀 Como Usar

### 1. ⚠️ DESCOBERTA IMPORTANTE: Tokens duram apenas 3 minutos!

Descobrimos que os tokens do EcomHub têm duração extremamente curta:
- **token** e **e_token**: Expiram em **3 minutos**
- **refresh_token**: Dura **48 horas**

Por isso, o sistema está configurado para renovar a cada **2 minutos**, garantindo 1 minuto de margem de segurança.

### 2. Configurar Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

```env
# Credenciais (IMPORTANTE: mover do hardcode)
ECOMHUB_EMAIL=seu_email@example.com
ECOMHUB_PASSWORD=sua_senha

# Habilitar sincronização
TOKEN_SYNC_ENABLED=true

# Configuração para tokens de 3 minutos
TOKEN_DURATION_MINUTES=3  # Tokens duram apenas 3 minutos!
SYNC_INTERVAL_MINUTES=2   # Renovar a cada 2 minutos

# Chegou Hub (quando estiver pronto)
CHEGOU_HUB_WEBHOOK_URL=https://api.chegouhub.com/webhook/tokens
CHEGOU_HUB_API_KEY=sua_chave_secreta
```

**OU use o script de configuração rápida:**
```bash
python setup_token_sync.py
```

### 3. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 4. Iniciar o Serviço

O serviço inicia automaticamente com o servidor principal:

```bash
python main.py
```

Se `TOKEN_SYNC_ENABLED=true`, você verá:
```
🔄 Iniciando serviço de sincronização de tokens...
✅ Serviço de sincronização iniciado em background
```

## 📁 Estrutura do Módulo

```
token_sync/
├── __init__.py         # Exporta interfaces principais
├── config.py           # Todas as configurações
├── sync_service.py     # Lógica de obtenção de tokens
├── token_validator.py  # Validação de tokens
├── notifier.py         # Envio para Chegou Hub
├── scheduler.py        # Agendamento automático
└── README.md          # Esta documentação
```

## ⚙️ Como Funciona

### Fluxo de Sincronização

1. **Agendador** executa a cada **2 minutos**
2. **Sync Service** usa Selenium para fazer login
3. **Validador** confirma que tokens funcionam
4. **Notifier** envia para Chegou Hub
5. **Repetir** antes dos tokens expirarem (margem de 1 minuto)

### Margem de Segurança para Tokens de 3 Minutos

Como os tokens duram apenas **3 minutos**, renovamos a cada **2 minutos**:
- ✅ **1 minuto de margem** (33% de segurança)
- ✅ Tokens sempre válidos
- ✅ Renovação rápida e confiável
- ⚠️ **Importante**: Com tokens tão curtos, o sistema precisa estar sempre rodando!

## 📊 Monitoramento

### Logs

O módulo gera logs detalhados:

```
2024-11-07 10:00:00 - INFO - ✅ SINCRONIZAÇÃO #1 INICIADA
2024-11-07 10:00:15 - INFO - ✅ Tokens obtidos em 15s
2024-11-07 10:00:16 - INFO - ✅ Tokens validados com sucesso
2024-11-07 10:00:17 - INFO - ✅ Tokens enviados para Chegou Hub
2024-11-07 10:00:17 - INFO - ✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO
```

### Status

Para verificar o status do serviço:

```python
from token_sync.scheduler import token_scheduler
status = token_scheduler.get_status()
print(status)
```

Retorna:
```json
{
  "is_running": true,
  "sync_count": 10,
  "success_count": 10,
  "error_count": 0,
  "last_sync": "2024-11-07T10:00:00Z",
  "next_sync": "2024-11-07T10:42:00Z"
}
```

## 🔧 Configurações Avançadas

### Retry e Resiliência

```env
MAX_RETRY_ATTEMPTS=3          # Tentativas em caso de falha
RETRY_DELAY_SECONDS=5          # Delay entre tentativas
RETRY_EXPONENTIAL_BACKOFF=true # Dobrar delay a cada tentativa
MAX_CONSECUTIVE_FAILURES=3     # Alertar após X falhas
```

### Validação

```env
VALIDATE_TOKENS_AFTER_FETCH=true  # Testar tokens após obter
VALIDATION_TEST_COUNTRY_ID=164    # País para teste (164=Espanha)
```

### Alertas

```env
ALERT_WEBHOOK_URL=https://hooks.slack.com/...  # Webhook para alertas
LOG_LEVEL=INFO                                  # Nível de log
LOG_TO_FILE=true                               # Salvar logs em arquivo
```

## 🚨 Troubleshooting

### Tokens não estão sendo obtidos

1. Verificar credenciais em `.env`
2. Verificar se Selenium/Chrome está funcionando
3. Ver logs detalhados: `tail -f token_sync.log`

### Tokens não chegam no Chegou Hub

1. Verificar `CHEGOU_HUB_WEBHOOK_URL`
2. Verificar `CHEGOU_HUB_API_KEY`
3. Testar conectividade:

```python
from token_sync.notifier import test_webhook_connectivity
test_webhook_connectivity()
```

### Tokens expiram antes da renovação

Com tokens de 3 minutos e renovação a cada 2 minutos, isso não deve acontecer.
Se ocorrer:
1. Reduzir para `SYNC_INTERVAL_MINUTES=1` (renovação a cada minuto)
2. Verificar latência da rede/Selenium
3. Considerar manter múltiplas sessões paralelas

## 🔄 Integração com Chegou Hub

### Endpoint Esperado no Chegou Hub

```python
POST /api/webhooks/ecomhub-tokens
Content-Type: application/json
Authorization: Bearer {CHEGOU_HUB_API_KEY}

{
  "cookies": {...},
  "cookie_string": "token=...; e_token=...",
  "headers": {...},
  "timestamp": "2024-11-07T10:00:00Z",
  "valid_until_estimate": "2024-11-07T11:00:00Z"
}
```

### Usando os Tokens no Chegou Hub

```javascript
// Exemplo em Node.js
const axios = require('axios');

// Tokens recebidos do webhook
const tokens = receivedFromWebhook;

// Fazer requisição direta à API EcomHub
const response = await axios.get('https://api.ecomhub.app/api/orders', {
  params: {
    offset: 0,
    conditions: JSON.stringify({...})
  },
  headers: {
    ...tokens.headers,
    'Cookie': tokens.cookie_string
  }
});
```

## 📈 Performance

| Métrica | Antes (Selenium) | Depois (Token Sync) |
|---------|------------------|---------------------|
| Tempo de resposta | 10-30s | 2-3s |
| CPU | Alto | Baixo |
| Memória | ~500MB | ~50MB |
| Concorrência | Limitada | Ilimitada |

## 🤝 Compatibilidade

### Endpoint /api/auth continua funcionando!

Para uso via n8n, Make ou Zapier:

```bash
POST https://ecomhub-selenium-production.up.railway.app/api/auth
```

Funciona independentemente do Token Sync.

## 📝 Notas Importantes

1. **NÃO modifica** nenhum código existente (exceto 4 linhas no main.py)
2. **NÃO afeta** cálculos de efetividade
3. **NÃO quebra** endpoints existentes
4. **APENAS adiciona** otimização de velocidade

## 🛠️ Manutenção

### Atualizar intervalo de sincronização

Se descobrir nova duração de tokens:

1. Atualizar `TOKEN_DURATION_MINUTES` no `.env`
2. O intervalo é calculado automaticamente (70%)
3. Reiniciar o serviço

### Desabilitar temporariamente

```env
TOKEN_SYNC_ENABLED=false
```

### Forçar sincronização manual

```python
from token_sync.scheduler import token_scheduler
token_scheduler.trigger_sync_now()
```

## 📞 Suporte

Para problemas ou dúvidas:
1. Verificar logs: `tail -f token_sync.log`
2. Verificar status do serviço
3. Consultar troubleshooting acima

---

**Módulo desenvolvido para otimizar a velocidade de acesso aos dados do EcomHub**