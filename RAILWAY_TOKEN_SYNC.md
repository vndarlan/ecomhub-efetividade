# 🔄 Sincronização de Tokens no Railway

## ⚠️ Limitação Importante do Railway

O Railway tem uma **limitação mínima de 5 minutos** para Cron Jobs, mas nossos tokens do EcomHub **expiram em 3 minutos**.

Por isso, usamos uma **thread em background** que executa a cada 2 minutos dentro do próprio servidor.

## ✅ Como Funciona

### 1. Thread em Background
- Roda dentro do processo principal do servidor
- Executa a cada 2 minutos (configurável)
- Não afeta o desempenho da API
- Logs integrados com o servidor principal

### 2. Fluxo de Execução
```
Servidor Inicia
    ↓
Verifica TOKEN_SYNC_ENABLED=true
    ↓
Inicia Thread de Sincronização
    ↓
A cada 2 minutos:
    - Login via Selenium
    - Obtém novos tokens
    - Armazena em memória
    - (Opcional) Envia para Chegou Hub
```

## 🚀 Configuração no Railway

### Variáveis de Ambiente Necessárias

```env
# OBRIGATÓRIAS
ECOMHUB_EMAIL=seu_email@exemplo.com
ECOMHUB_PASSWORD=sua_senha
TOKEN_SYNC_ENABLED=true

# OPCIONAIS (quando Chegou Hub estiver pronto)
CHEGOU_HUB_WEBHOOK_URL=https://seu-webhook
CHEGOU_HUB_API_KEY=sua-api-key

# CONFIGURAÇÃO DO INTERVALO (opcional)
TOKEN_SYNC_INTERVAL_MINUTES=2  # padrão é 2 minutos
```

## 📊 Monitoramento

### Logs Esperados no Railway

No início do servidor:
```
🔄 Iniciando serviço de sincronização de tokens...
✅ Serviço de sincronização iniciado em background (a cada 2 minutos)
INFO:     Started server process [1]
INFO:     Uvicorn running on http://0.0.0.0:8001
```

A cada 2 minutos:
```
[TokenSync] 🔄 Iniciando sincronização de tokens...
[TokenSync] Fazendo login no EcomHub...
[TokenSync] ✅ Login realizado com sucesso
[TokenSync] ✅ Tokens sincronizados com sucesso
[TokenSync] Próxima sincronização em 2 minutos
```

## ❌ O Que NÃO Fazer

### Não Use Cron Jobs do Railway
- Mínimo de 5 minutos não atende nossa necessidade
- Tokens expiram em 3 minutos
- Causaria falhas de autenticação

### Não Desative a Thread
- É essencial para manter tokens válidos
- Sem ela, cada request precisaria fazer login novamente
- Aumentaria tempo de resposta drasticamente

## 🔧 Troubleshooting

### "Tokens expirando mesmo com sync ativado"
1. Verifique se `TOKEN_SYNC_ENABLED=true` está configurado
2. Procure nos logs por "Serviço de sincronização iniciado"
3. Verifique se não há erros de login nos logs

### "Thread parando após algum tempo"
- A thread é daemon=True, não deveria parar
- Verifique logs para erros
- Se necessário, faça redeploy

### "Consumo alto de recursos"
- O login via Selenium usa recursos por ~15-20 segundos a cada 2 minutos
- Isso é normal e necessário
- Considere aumentar recursos do Railway se necessário

## 📈 Performance

### Impacto da Sincronização
- **CPU**: Pico de ~30% por 15-20 segundos a cada 2 minutos
- **RAM**: ~100-200MB adicional durante login
- **Rede**: Mínima (apenas login e download de tokens)

### Benefícios
- ✅ Tokens sempre válidos
- ✅ Responses mais rápidos (não precisa fazer login a cada request)
- ✅ Maior confiabilidade
- ✅ Menos chance de rate limiting

## 🎯 Resumo

| Aspecto | Detalhe |
|---------|---------|
| **Método** | Thread em background |
| **Intervalo** | 2 minutos (configurável) |
| **Duração Token** | 3 minutos |
| **Margem Segurança** | 1 minuto |
| **Railway Cron** | NÃO usar (mínimo 5 min) |

## 💡 Dica

Se o Railway adicionar suporte para cron jobs com intervalos menores que 5 minutos no futuro, poderemos migrar para cron. Por enquanto, a thread em background é a melhor solução.