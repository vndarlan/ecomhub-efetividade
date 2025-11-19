# Guia de Migração - Correção de Vazamento de Drivers

## 🚨 Problema Identificado

O código original tinha **7 problemas críticos** causando travamento após múltiplas requisições:

1. **Decorator `@safe_driver_operation` vazava drivers em retries**
2. **Variável `nonlocal driver` causava condição de corrida**
3. **Função `create_driver()` não limpava recursos em exceções parciais**
4. **Sem controle de concorrência (múltiplos drivers simultâneos)**
5. **Endpoints legacy duplicavam o problema**
6. **Falta de monitoramento de drivers ativos**
7. **Sem garbage collection forçado**

## ✅ Solução Implementada

### Novos Arquivos Criados:

1. **`driver_manager.py`** - Gerenciamento robusto de drivers
   - Context manager garante fechamento
   - Semáforo limita 2 drivers simultâneos
   - Monitoramento de drivers ativos
   - Limpeza automática de órfãos

2. **`main_refactored.py`** - Versão corrigida do main.py
   - Usa ChromeDriverManager
   - Remove decorator problemático
   - Adiciona endpoints de monitoramento

## 📋 Como Migrar

### Opção 1: Substituição Completa (Recomendada)

```bash
# 1. Fazer backup do arquivo original
cp main.py main_backup.py

# 2. Substituir pelo refatorado
cp main_refactored.py main.py

# 3. Instalar dependência de monitoramento
pip install psutil

# 4. Fazer deploy
git add .
git commit -m "fix: corrigir vazamento de memória e travamentos"
git push
```

### Opção 2: Migração Gradual

Se preferir migrar gradualmente, siga estes passos:

#### Passo 1: Adicionar o driver_manager.py
```python
# Copie o arquivo driver_manager.py para seu projeto
```

#### Passo 2: Atualizar imports no main.py
```python
# Adicionar no topo do arquivo
from driver_manager import get_chrome_driver, DriverMonitor, cleanup_all_drivers, get_driver_stats
import gc
```

#### Passo 3: Substituir o decorator problemático
```python
# REMOVER:
def safe_driver_operation(driver_func):
    """Decorator para operações seguras com retry em caso de falha de sessão"""
    # ... código antigo ...

# SUBSTITUIR POR:
def safe_operation(func):
    """Decorator simplificado - SEM RETRY de driver"""
    def wrapper(*args, **kwargs):
        try:
            logger.info(f"🎯 Executando: {func.__name__}")
            result = func(*args, **kwargs)
            logger.info(f"✅ Sucesso: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"❌ Erro em {func.__name__}: {e}")
            raise
    return wrapper
```

#### Passo 4: Refatorar endpoints principais
```python
@app.post("/api/processar-ecomhub/", response_model=ProcessResponse)
@apply_rate_limit("5/minute")
async def processar_ecomhub(request_body: ProcessRequest, request: Request):
    """Endpoint principal refatorado"""

    # Validação
    if request_body.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")

    try:
        headless = os.getenv("ENVIRONMENT") != "local"

        # USAR CONTEXT MANAGER - CRÍTICO!
        with get_chrome_driver(headless=headless) as driver:
            # Fazer login
            login_ecomhub(driver)

            # Extrair dados
            orders_data = extract_via_api(
                driver,
                request_body.data_inicio,
                request_body.data_fim,
                request_body.pais_id
            )

            # Processar dados...
            # ... resto do código ...

        # Driver é AUTOMATICAMENTE fechado aqui

    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Forçar garbage collection
        gc.collect()
```

#### Passo 5: Adicionar endpoints de monitoramento
```python
@app.get("/api/driver-stats")
async def driver_stats():
    """Monitoramento de drivers"""
    return {"status": "ok", "drivers": get_driver_stats()}

@app.post("/api/cleanup")
async def cleanup_drivers(api_key: str = Depends(verify_api_key)):
    """Limpeza forçada de drivers"""
    cleanup_all_drivers()
    gc.collect()
    return {"status": "success", "message": "Limpeza executada"}
```

#### Passo 6: Adicionar hooks de startup/shutdown
```python
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Aplicação iniciada")
    cleanup_all_drivers()  # Limpar órfãos de execuções anteriores

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🛑 Encerrando...")
    cleanup_all_drivers()  # Garantir fechamento de todos os drivers
```

## 🧪 Testando a Solução

### Teste Local
```bash
# Instalar dependências
pip install psutil

# Executar localmente (browser visível)
ENVIRONMENT=local python main.py

# Em outro terminal, testar múltiplas requisições
for i in {1..10}; do
    curl -X POST http://localhost:8001/api/processar-ecomhub/ \
        -H "Content-Type: application/json" \
        -d '{"data_inicio":"2024-01-01","data_fim":"2024-01-31","pais_id":"164"}'
    sleep 2
done

# Monitorar drivers ativos
watch -n 1 'curl http://localhost:8001/api/driver-stats'
```

### Verificar Melhorias

#### Antes (Problemas):
- ❌ Travamento após 5-10 requisições
- ❌ Memória crescendo continuamente
- ❌ Drivers órfãos acumulando
- ❌ Necessário redeploy frequente

#### Depois (Corrigido):
- ✅ Suporta requisições ilimitadas
- ✅ Memória estável
- ✅ Máximo 2 drivers simultâneos
- ✅ Auto-recuperação de erros
- ✅ Monitoramento em tempo real

## 📊 Monitoramento em Produção

### Endpoints Úteis:

1. **Health Check**: `GET /health`
   - Retorna status geral
   - Alerta se muitos drivers ativos
   - Monitora uso de memória

2. **Driver Stats**: `GET /api/driver-stats`
   - Lista drivers ativos
   - Tempo de vida de cada driver
   - Uso de memória

3. **Cleanup Manual**: `POST /api/cleanup`
   - Força limpeza de todos os drivers
   - Útil em emergências
   - Requer autenticação

### Logs Importantes:

Procure por estes logs para monitorar a saúde:

```
📊 Driver registrado: driver_xxx | Total ativos: 1
✅ Driver driver_xxx fechado com sucesso
📊 Driver removido: driver_xxx | Total ativos: 0
💾 Memória: 512MB disponível (45.2% usado)
🧹 Limpando driver órfão: driver_xxx (idade: 301s)
```

## ⚠️ Avisos Importantes

1. **NÃO use o decorator `@safe_driver_operation` antigo** - ele causa vazamento
2. **SEMPRE use context manager** (`with get_chrome_driver()`)
3. **Monitore uso de memória** especialmente em Railway
4. **Configure alertas** para health check crítico
5. **Teste localmente primeiro** antes de fazer deploy

## 🚀 Deploy para Railway

```bash
# Adicionar ao railway.toml se necessário
[build]
builder = "nixpacks"
buildCommand = "pip install -r requirements.txt && pip install psutil"

[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

# Fazer deploy
railway up
```

## 📝 Checklist de Migração

- [ ] Fazer backup do main.py original
- [ ] Copiar driver_manager.py para o projeto
- [ ] Instalar psutil: `pip install psutil`
- [ ] Atualizar requirements.txt
- [ ] Substituir main.py ou aplicar mudanças gradualmente
- [ ] Testar localmente com múltiplas requisições
- [ ] Verificar logs e monitoramento
- [ ] Deploy para produção
- [ ] Monitorar por 24h
- [ ] Configurar alertas se necessário

## 🆘 Troubleshooting

### Problema: "Module psutil not found"
```bash
pip install psutil
# Adicionar ao requirements.txt
echo "psutil" >> requirements.txt
```

### Problema: "Timeout esperando driver slot"
- Há 2+ requisições simultâneas
- Aguarde ou force limpeza: `POST /api/cleanup`

### Problema: "Memória insuficiente"
- Driver órfão consumindo memória
- Use `/api/cleanup` para limpar
- Verifique com `/api/driver-stats`

## 📞 Suporte

Se encontrar problemas:
1. Verifique os logs detalhados
2. Use `/api/driver-stats` para diagnóstico
3. Force limpeza com `/api/cleanup` se necessário
4. Em último caso, faça rollback para main_backup.py