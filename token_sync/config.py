"""
Configurações para o módulo de sincronização de tokens.

Este arquivo centraliza todas as configurações necessárias para o funcionamento
do serviço de sincronização automática de tokens.
"""

import os
from datetime import timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ===========================
# Configurações de Autenticação
# ===========================

# Credenciais EcomHub (movidas do hardcode no main.py)
ECOMHUB_EMAIL = os.getenv("ECOMHUB_EMAIL", "saviomendesalvess@gmail.com")
ECOMHUB_PASSWORD = os.getenv("ECOMHUB_PASSWORD", "Chegou123!")

# ===========================
# Configurações de Sincronização
# ===========================

# Habilitar/desabilitar sincronização automática
TOKEN_SYNC_ENABLED = os.getenv("TOKEN_SYNC_ENABLED", "false").lower() == "true"

# Duração estimada dos tokens em minutos
# Token expira em 3 minutos (tempo real de expiração no EcomHub)
TOKEN_DURATION_MINUTES = int(os.getenv("TOKEN_DURATION_MINUTES", "3"))

# Intervalo de sincronização em minutos
# Por padrão, renova com 30% de margem de segurança
# Ex: Se token dura 60 min, renova a cada 42 min (60 * 0.7)
SYNC_INTERVAL_MINUTES = int(
    os.getenv("SYNC_INTERVAL_MINUTES", str(int(TOKEN_DURATION_MINUTES * 0.7)))
)

# Sincronização inicial ao iniciar o serviço
SYNC_ON_STARTUP = os.getenv("SYNC_ON_STARTUP", "true").lower() == "true"

# ===========================
# Configurações do Chegou Hub
# ===========================

# URL do webhook para enviar tokens atualizados
CHEGOU_HUB_WEBHOOK_URL = os.getenv("CHEGOU_HUB_WEBHOOK_URL", "")

# Chave de API para autenticação com o Chegou Hub
CHEGOU_HUB_API_KEY = os.getenv("CHEGOU_HUB_API_KEY", "")

# Timeout em segundos para requisições ao Chegou Hub
CHEGOU_HUB_TIMEOUT = int(os.getenv("CHEGOU_HUB_TIMEOUT", "10"))

# Habilitar envio para Chegou Hub (só envia se URL estiver configurada)
CHEGOU_HUB_ENABLED = bool(CHEGOU_HUB_WEBHOOK_URL)

# ===========================
# Configurações de Retry e Resiliência
# ===========================

# Número máximo de tentativas em caso de falha
MAX_RETRY_ATTEMPTS = int(os.getenv("MAX_RETRY_ATTEMPTS", "3"))

# Delay inicial entre tentativas em segundos
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "5"))

# Usar backoff exponencial (dobra o delay a cada tentativa)
RETRY_EXPONENTIAL_BACKOFF = os.getenv("RETRY_EXPONENTIAL_BACKOFF", "true").lower() == "true"

# Número máximo de falhas consecutivas antes de alertar
MAX_CONSECUTIVE_FAILURES = int(os.getenv("MAX_CONSECUTIVE_FAILURES", "3"))

# Limite máximo absoluto de erros consecutivos antes de pausar sistema
# Após atingir este limite, o sistema para de tentar até reset manual
MAX_ABSOLUTE_FAILURES = int(os.getenv("MAX_ABSOLUTE_FAILURES", "100"))

# ===========================
# Configurações de Monitoramento
# ===========================

# Webhook para alertas críticos (opcional)
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

# Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Salvar logs em arquivo
LOG_TO_FILE = os.getenv("LOG_TO_FILE", "true").lower() == "true"

# Nome do arquivo de log
LOG_FILE_NAME = os.getenv("LOG_FILE_NAME", "token_sync.log")

# ===========================
# Configurações do Selenium
# ===========================

# Usar modo headless (sem interface gráfica)
SELENIUM_HEADLESS = os.getenv("ENVIRONMENT", "production") != "local"

# Timeout para operações do Selenium em segundos
SELENIUM_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "30"))

# ===========================
# Configurações de Validação
# ===========================

# Validar tokens após obtenção (faz uma chamada de teste)
VALIDATE_TOKENS_AFTER_FETCH = os.getenv("VALIDATE_TOKENS_AFTER_FETCH", "true").lower() == "true"

# País usado para teste de validação (164 = Espanha)
VALIDATION_TEST_COUNTRY_ID = int(os.getenv("VALIDATION_TEST_COUNTRY_ID", "164"))

# ===========================
# Configurações de Refresh Token
# ===========================

# Habilitar refresh via HTTP (usa refresh_token para renovar sem Selenium)
# Quando habilitado, só usa Selenium quando refresh_token expira (a cada 48h)
# CORREÇÃO: A API usa GET, não POST! Agora funciona corretamente.
ENABLE_HTTP_REFRESH = os.getenv("ENABLE_HTTP_REFRESH", "true").lower() == "true"

# URL da API EcomHub para fazer requisições de refresh
ECOMHUB_API_URL = os.getenv("ECOMHUB_API_URL", "https://api.ecomhub.app/api/orders")

# Duração do refresh_token em horas (48 horas = 2 dias)
REFRESH_TOKEN_DURATION_HOURS = int(os.getenv("REFRESH_TOKEN_DURATION_HOURS", "48"))

# ===========================
# Helpers e Funções Utilitárias
# ===========================

def get_sync_interval_seconds():
    """Retorna o intervalo de sincronização em segundos."""
    return SYNC_INTERVAL_MINUTES * 60

def get_token_duration_seconds():
    """Retorna a duração estimada dos tokens em segundos."""
    return TOKEN_DURATION_MINUTES * 60

def is_chegou_hub_configured():
    """Verifica se o Chegou Hub está configurado."""
    return bool(CHEGOU_HUB_WEBHOOK_URL and CHEGOU_HUB_API_KEY)

def get_safety_margin_minutes():
    """Retorna a margem de segurança em minutos antes da expiração."""
    return TOKEN_DURATION_MINUTES - SYNC_INTERVAL_MINUTES

# ===========================
# Validação de Configurações
# ===========================

def validate_config():
    """
    Valida as configurações e emite avisos se necessário.
    """
    logger = logging.getLogger(__name__)

    # Verificar se sincronização está habilitada
    if TOKEN_SYNC_ENABLED:
        logger.info("✅ Sincronização de tokens HABILITADA")
        logger.info(f"   - Duração estimada dos tokens: {TOKEN_DURATION_MINUTES} minutos")
        logger.info(f"   - Intervalo de sincronização: {SYNC_INTERVAL_MINUTES} minutos")
        logger.info(f"   - Margem de segurança: {get_safety_margin_minutes()} minutos")

        # Verificar margem de segurança
        if get_safety_margin_minutes() < 10:
            logger.warning("⚠️ Margem de segurança muito baixa! Considere aumentar.")

        # Verificar configuração do Chegou Hub
        if not is_chegou_hub_configured():
            logger.warning("⚠️ Chegou Hub não está configurado. Tokens serão obtidos mas não enviados.")
        else:
            logger.info(f"✅ Chegou Hub configurado: {CHEGOU_HUB_WEBHOOK_URL}")

        # Verificar credenciais
        if not ECOMHUB_EMAIL or not ECOMHUB_PASSWORD:
            logger.error("❌ Credenciais EcomHub não configuradas!")
            raise ValueError("ECOMHUB_EMAIL e ECOMHUB_PASSWORD são obrigatórios")
    else:
        logger.info("ℹ️ Sincronização de tokens DESABILITADA")

# Executar validação ao importar o módulo
if __name__ != "__main__":
    validate_config()