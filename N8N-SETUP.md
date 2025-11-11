# Configuração n8n - Token Sync

## 📋 Pré-requisitos

1. **n8n instalado** (self-hosted ou n8n.cloud)
2. **Railway API configurada** com as variáveis:
   - `SYNC_API_KEY` (gere com: `openssl rand -hex 32`)
   - `TOKEN_SYNC_ENABLED=false`

---

## 🚀 Passo a Passo

### 1. Importar Workflow no n8n

1. Abra o n8n
2. Clique em **"+"** (novo workflow)
3. Clique nos **3 pontos** no canto superior direito
4. Selecione **"Import from File"**
5. Selecione o arquivo: **`n8n-sync-workflow.json`**

### 2. Configurar Variáveis de Ambiente no n8n

No n8n, adicione as seguintes variáveis de ambiente:

```bash
# URL da sua API no Railway
API_URL=https://sua-api.railway.app

# Mesma chave configurada no Railway
SYNC_API_KEY=sua-chave-secreta-forte-aqui
```

**Como adicionar:**
- **n8n self-hosted**: Arquivo `.env` ou variáveis do sistema
- **n8n.cloud**: Settings → Variables

### 3. Ativar o Workflow

1. No workflow importado, clique em **"Activate"** (botão no topo)
2. Pronto! O workflow começará a executar a cada 2 minutos

---

## 🧪 Testar Manualmente

Antes de ativar, teste manualmente:

1. Clique em **"Execute Workflow"** (botão no topo)
2. Verifique os logs de cada nó
3. Confirme que recebeu resposta de sucesso

---

## 📊 Monitoramento

### Logs no n8n

- **Executions**: Veja todas as execuções no histórico
- **Verde**: Sucesso ✅
- **Vermelho**: Erro ❌

### Logs no Railway

```bash
# Via Railway CLI
railway logs

# Procure por:
✅ Sync manual disparada por...
✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO
```

---

## 🔔 Configurar Alertas (Opcional)

O workflow já tem um nó **"Enviar Alerta"** configurado para disparar após 3 falhas consecutivas.

### Opção 1: Slack

1. Adicione um nó **Slack** após **"Enviar Alerta"**
2. Configure webhook do Slack
3. Conecte ao nó **"Enviar Alerta"**

### Opção 2: Discord

1. Adicione um nó **Discord** após **"Enviar Alerta"**
2. Configure webhook do Discord
3. Conecte ao nó **"Enviar Alerta"**

### Opção 3: Email

1. Adicione um nó **Send Email** após **"Enviar Alerta"**
2. Configure SMTP
3. Conecte ao nó **"Enviar Alerta"**

### Opção 4: Telegram

1. Adicione um nó **Telegram** após **"Enviar Alerta"**
2. Configure bot token
3. Conecte ao nó **"Enviar Alerta"**

---

## 🔧 Troubleshooting

### Erro: "SYNC_API_KEY não configurada"

**Solução**: Adicione a variável `SYNC_API_KEY` no Railway:
```bash
railway variables set SYNC_API_KEY=sua-chave-aqui
```

### Erro: "Header X-Sync-Key não fornecido"

**Solução**: Verifique se a variável `SYNC_API_KEY` está configurada no n8n

### Erro: "X-Sync-Key inválida"

**Solução**: As chaves no Railway e n8n devem ser IDÊNTICAS

### Workflow não executa

**Solução**:
1. Verifique se o workflow está **ativado** (toggle verde)
2. Verifique se o Schedule Trigger está configurado para 2 minutos

### Timeout após 2 minutos

**Solução**: Isso é esperado se o job demorar muito. Verifique:
1. Logs do Railway para erros de ChromeDriver
2. Uso de memória do container (pode estar em OOM)

---

## 📈 Estatísticas

Após configurar, você terá:

- ✅ **Execução a cada 2 minutos** (720 syncs/dia)
- ✅ **Timeout de 120s** por execução
- ✅ **Retry automático** (2 tentativas com 10s de intervalo)
- ✅ **Circuit breaker** após 3 falhas consecutivas
- ✅ **Alertas** configuráveis
- ✅ **Dashboard visual** de todas as execuções

---

## 🎯 Próximos Passos

Depois que tudo estiver funcionando:

1. **Monitore por 24h** para garantir estabilidade
2. **Configure alertas** (Slack/Discord/Email)
3. **Opcional**: Ajuste intervalo se necessário (não recomendado <2min)
4. **Opcional**: Adicione métricas (Prometheus, Grafana, etc)

---

## 📞 Suporte

Se encontrar problemas:

1. Verifique logs do Railway: `railway logs`
2. Verifique execuções do n8n: Aba "Executions"
3. Teste endpoint manualmente:
   ```bash
   curl -X POST https://sua-api.railway.app/api/sync-tokens \
     -H "X-Sync-Key: sua-chave"
   ```

---

**Criado em**: 2025-01-11
**Versão**: 1.0.0
