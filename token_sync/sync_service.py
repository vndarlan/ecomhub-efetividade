"""
Serviço principal de sincronização de tokens.

Este módulo contém a lógica principal para:
- Obter tokens frescos via Selenium
- Validar tokens obtidos
- Enviar para o Chegou Hub
- Gerenciar estado e métricas
"""

import logging
from datetime import datetime, timedelta
import time
import json
import sys
import os

# Adicionar diretório pai ao path para importar do main.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import create_driver, login_ecomhub, get_auth_cookies
from .config import *

logger = logging.getLogger(__name__)

class TokenSyncService:
    """
    Serviço responsável pela sincronização de tokens.

    Mantém o estado dos tokens, realiza sincronizações e
    gerencia métricas de sucesso/falha.
    """

    def __init__(self):
        """Inicializa o serviço de sincronização."""
        self.last_sync = None
        self.last_sync_success = None
        self.current_tokens = None
        self.sync_count = 0
        self.success_count = 0
        self.error_count = 0
        self.consecutive_errors = 0
        self.service_start_time = datetime.utcnow()

        logger.info("=" * 60)
        logger.info("Token Sync Service inicializado")
        logger.info(f"Duração estimada dos tokens: {TOKEN_DURATION_MINUTES} minutos")
        logger.info(f"Intervalo de sincronização: {SYNC_INTERVAL_MINUTES} minutos")
        logger.info(f"Margem de segurança: {get_safety_margin_minutes()} minutos")
        logger.info("=" * 60)

    def get_fresh_tokens(self):
        """
        Obtém novos tokens via Selenium.

        Returns:
            dict: Dicionário contendo cookies, headers e metadados
            None: Em caso de erro
        """
        driver = None
        try:
            logger.info("🔄 Obtendo tokens frescos via Selenium...")
            start_time = time.time()

            # Criar driver Chrome
            driver = create_driver(headless=SELENIUM_HEADLESS)
            logger.debug(f"Driver criado (headless={SELENIUM_HEADLESS})")

            # Fazer login no EcomHub
            login_success = login_ecomhub(driver)
            if not login_success:
                raise Exception("Falha no login do EcomHub")

            logger.info("✅ Login realizado com sucesso")

            # Extrair cookies
            cookies = get_auth_cookies(driver)
            if not cookies:
                raise Exception("Nenhum cookie obtido após login")

            logger.info(f"📦 Cookies extraídos: {list(cookies.keys())}")

            # Extrair User-Agent e outros headers úteis
            user_agent = driver.execute_script("return navigator.userAgent;")

            # Preparar headers padrão para API
            headers = {
                "Accept": "*/*",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Origin": "https://go.ecomhub.app",
                "Referer": "https://go.ecomhub.app/",
                "User-Agent": user_agent,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/json"
            }

            # Calcular tempo de expiração estimado
            current_time = datetime.utcnow()
            expiration_time = current_time + timedelta(minutes=TOKEN_DURATION_MINUTES)

            # Preparar resposta completa
            tokens_data = {
                "cookies": cookies,
                "cookie_string": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
                "headers": headers,
                "timestamp": current_time.isoformat() + "Z",
                "valid_until_estimate": expiration_time.isoformat() + "Z",
                "duration_minutes": TOKEN_DURATION_MINUTES,
                "sync_number": self.sync_count + 1,
                "obtained_in_seconds": round(time.time() - start_time, 2)
            }

            logger.info(f"✅ Tokens obtidos em {tokens_data['obtained_in_seconds']}s")

            return tokens_data

        except Exception as e:
            logger.error(f"❌ Erro ao obter tokens: {e}")
            return None

        finally:
            # Sempre fechar o driver
            if driver:
                try:
                    driver.quit()
                    logger.debug("Driver fechado")
                except:
                    pass

    def validate_and_store_tokens(self, tokens_data):
        """
        Valida e armazena os tokens obtidos.

        Args:
            tokens_data (dict): Dados dos tokens obtidos

        Returns:
            bool: True se válidos e armazenados, False caso contrário
        """
        if not tokens_data:
            return False

        # Validar tokens se configurado
        if VALIDATE_TOKENS_AFTER_FETCH:
            # Importar validador (será criado depois)
            try:
                from .token_validator import validate_tokens
                if not validate_tokens(tokens_data['cookies']):
                    logger.error("❌ Tokens obtidos não passaram na validação")
                    return False
                logger.info("✅ Tokens validados com sucesso")
            except ImportError:
                logger.warning("⚠️ Módulo de validação não disponível, pulando validação")

        # Armazenar tokens
        self.current_tokens = tokens_data
        self.last_sync = datetime.utcnow()
        self.last_sync_success = True

        logger.info("💾 Tokens armazenados localmente")
        return True

    def send_to_chegou_hub(self, tokens_data):
        """
        Envia tokens para o Chegou Hub.

        Args:
            tokens_data (dict): Dados dos tokens para enviar

        Returns:
            bool: True se enviado com sucesso, False caso contrário
        """
        if not CHEGOU_HUB_ENABLED:
            logger.debug("Chegou Hub não configurado, pulando envio")
            return True

        try:
            # Importar notificador (será criado depois)
            from .notifier import send_to_chegou_hub as notifier_send
            success = notifier_send(tokens_data)

            if success:
                logger.info("✅ Tokens enviados para Chegou Hub")
            else:
                logger.warning("⚠️ Falha ao enviar para Chegou Hub")

            return success

        except ImportError:
            logger.warning("⚠️ Módulo notificador não disponível")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao enviar para Chegou Hub: {e}")
            return False

    def perform_sync(self):
        """
        Realiza uma sincronização completa de tokens.

        Esta é a função principal que:
        1. Obtém tokens frescos
        2. Valida os tokens
        3. Armazena localmente
        4. Envia para Chegou Hub

        Returns:
            bool: True se sincronização bem-sucedida, False caso contrário
        """
        try:
            self.sync_count += 1
            logger.info("=" * 60)
            logger.info(f"🔄 SINCRONIZAÇÃO #{self.sync_count} INICIADA")
            logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            if self.last_sync:
                time_since_last = (datetime.utcnow() - self.last_sync).total_seconds() / 60
                logger.info(f"Última sync: {time_since_last:.1f} minutos atrás")

            # Etapa 1: Obter tokens frescos
            tokens_data = self.get_fresh_tokens()
            if not tokens_data:
                raise Exception("Falha ao obter tokens")

            # Etapa 2: Validar e armazenar
            if not self.validate_and_store_tokens(tokens_data):
                raise Exception("Falha na validação dos tokens")

            # Etapa 3: Enviar para Chegou Hub
            chegou_hub_success = self.send_to_chegou_hub(tokens_data)

            # Atualizar métricas
            self.success_count += 1
            self.consecutive_errors = 0
            self.last_sync_success = True

            # Log de sucesso
            logger.info("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO")
            logger.info(f"   Total de syncs: {self.sync_count}")
            logger.info(f"   Sucessos: {self.success_count}")
            logger.info(f"   Taxa de sucesso: {(self.success_count/self.sync_count)*100:.1f}%")

            if not chegou_hub_success and CHEGOU_HUB_ENABLED:
                logger.warning("⚠️ Tokens obtidos mas não enviados ao Chegou Hub")

            logger.info("=" * 60)
            return True

        except Exception as e:
            # Atualizar métricas de erro
            self.error_count += 1
            self.consecutive_errors += 1
            self.last_sync_success = False

            logger.error(f"❌ FALHA NA SINCRONIZAÇÃO #{self.sync_count}")
            logger.error(f"   Erro: {e}")
            logger.error(f"   Erros consecutivos: {self.consecutive_errors}")
            logger.error(f"   Total de erros: {self.error_count}")

            # Alertar se muitos erros consecutivos
            if self.consecutive_errors >= MAX_CONSECUTIVE_FAILURES:
                self.send_critical_alert(f"⚠️ {self.consecutive_errors} falhas consecutivas na sincronização!")

            logger.info("=" * 60)
            return False

    def perform_sync_with_retry(self):
        """
        Realiza sincronização com sistema de retry.

        Returns:
            bool: True se eventualmente bem-sucedida, False se todas tentativas falharam
        """
        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            logger.info(f"🔄 Tentativa {attempt} de {MAX_RETRY_ATTEMPTS}")

            if self.perform_sync():
                return True

            if attempt < MAX_RETRY_ATTEMPTS:
                # Calcular delay para próxima tentativa
                if RETRY_EXPONENTIAL_BACKOFF:
                    delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
                else:
                    delay = RETRY_DELAY_SECONDS

                logger.info(f"⏳ Aguardando {delay}s antes da próxima tentativa...")
                time.sleep(delay)

        logger.error(f"❌ Todas as {MAX_RETRY_ATTEMPTS} tentativas falharam")
        return False

    def get_current_tokens(self):
        """
        Retorna os tokens atuais armazenados.

        Returns:
            dict: Tokens atuais ou None se não houver
        """
        if not self.current_tokens:
            logger.warning("Nenhum token armazenado ainda")
            return None

        # Verificar se tokens ainda devem estar válidos
        if self.last_sync:
            time_since_sync = (datetime.utcnow() - self.last_sync).total_seconds() / 60
            if time_since_sync > TOKEN_DURATION_MINUTES:
                logger.warning(f"⚠️ Tokens provavelmente expirados (última sync há {time_since_sync:.0f} min)")

        return self.current_tokens

    def get_status(self):
        """
        Retorna o status atual do serviço.

        Returns:
            dict: Dicionário com métricas e status
        """
        uptime = (datetime.utcnow() - self.service_start_time).total_seconds()

        status = {
            "service_running": True,
            "uptime_seconds": uptime,
            "uptime_readable": str(timedelta(seconds=int(uptime))),
            "sync_count": self.sync_count,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": (self.success_count / self.sync_count * 100) if self.sync_count > 0 else 0,
            "consecutive_errors": self.consecutive_errors,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_sync_success": self.last_sync_success,
            "tokens_available": self.current_tokens is not None,
            "sync_interval_minutes": SYNC_INTERVAL_MINUTES,
            "token_duration_minutes": TOKEN_DURATION_MINUTES
        }

        # Calcular próxima sincronização
        if self.last_sync:
            next_sync = self.last_sync + timedelta(minutes=SYNC_INTERVAL_MINUTES)
            status["next_sync"] = next_sync.isoformat()
            status["next_sync_in_minutes"] = max(0, (next_sync - datetime.utcnow()).total_seconds() / 60)

        return status

    def send_critical_alert(self, message):
        """
        Envia alerta crítico se configurado.

        Args:
            message (str): Mensagem de alerta
        """
        logger.critical(message)

        if ALERT_WEBHOOK_URL:
            try:
                import requests
                payload = {
                    "text": message,
                    "service": "token_sync",
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": self.get_status()
                }
                requests.post(ALERT_WEBHOOK_URL, json=payload, timeout=5)
                logger.info("🚨 Alerta crítico enviado")
            except Exception as e:
                logger.error(f"Falha ao enviar alerta: {e}")


# Instância global do serviço
_service_instance = None

def get_service_instance():
    """
    Retorna a instância singleton do serviço.

    Returns:
        TokenSyncService: Instância do serviço
    """
    global _service_instance
    if _service_instance is None:
        _service_instance = TokenSyncService()
    return _service_instance