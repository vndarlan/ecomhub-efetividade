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
from .database import get_database

logger = logging.getLogger(__name__)

def kill_orphan_chrome_processes():
    """
    Mata processos Chrome e ChromeDriver órfãos antes de iniciar novo driver.

    Returns:
        tuple: (processes_killed, success)
    """
    try:
        import subprocess
        import platform

        killed_count = 0

        if platform.system() == "Windows":
            # Windows
            commands = [
                ['taskkill', '/F', '/IM', 'chrome.exe', '/T'],
                ['taskkill', '/F', '/IM', 'chromedriver.exe', '/T']
            ]
        else:
            # Linux/Unix
            commands = [
                ['pkill', '-9', 'chrome'],
                ['pkill', '-9', 'chromedriver']
            ]

        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=10,  # Aumentado de 5s para 10s (reduz Errno 11)
                    text=True
                )
                if result.returncode == 0:
                    killed_count += 1
                    logger.info(f"🧹 Processos {cmd[-1]} mortos")
            except subprocess.TimeoutExpired:
                logger.warning(f"⏱️ Timeout ao executar {' '.join(cmd)}")
            except FileNotFoundError:
                # Comando não existe neste sistema
                pass
            except Exception as e:
                logger.warning(f"⚠️ Erro ao matar processos {cmd[-1]}: {e}")

        return killed_count, True

    except Exception as e:
        logger.error(f"❌ Erro na limpeza de processos: {e}")
        return 0, False

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
        self.paused = False  # Flag para pausar sistema após muitos erros
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

            # PASSO 1: Matar processos órfãos ANTES de criar novo driver
            logger.info("🧹 Verificando processos Chrome órfãos...")
            killed_count, cleanup_success = kill_orphan_chrome_processes()
            if killed_count > 0:
                logger.info(f"🧹 {killed_count} tipos de processos órfãos mortos")
                time.sleep(1)  # Aguardar processos terminarem (reduzido de 2s para 1s)

            # PASSO 2: Criar driver Chrome
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
            # SEMPRE fechar o driver COM RETRY
            if driver:
                # Tentar fechar normalmente (até 3 vezes)
                closed = False
                for attempt in range(3):
                    try:
                        driver.quit()
                        logger.info("✅ Driver fechado com sucesso")
                        closed = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            logger.warning(f"⚠️ Tentativa {attempt + 1} de fechar driver falhou: {e}")
                            time.sleep(1)
                        else:
                            logger.error(f"❌ Falha ao fechar driver após 3 tentativas: {e}")

                # Se falhou ao fechar normalmente, forçar kill
                if not closed:
                    logger.warning("🔨 Forçando encerramento de processos...")
                    killed_count, success = kill_orphan_chrome_processes()
                    if killed_count > 0:
                        logger.info(f"✅ {killed_count} tipos de processos forçados a encerrar")
                    else:
                        logger.error("❌ Não foi possível forçar encerramento de processos")

                # Aguardar processos encerrarem completamente
                time.sleep(1)

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

        # Armazenar tokens na memória
        self.current_tokens = tokens_data
        self.last_sync = datetime.utcnow()
        self.last_sync_success = True

        # Salvar no banco de dados
        try:
            db = get_database()
            cookies = tokens_data.get('cookies', {})

            # Extrair tokens individuais
            token = cookies.get('token', '')
            e_token = cookies.get('e_token', '')
            refresh_token = cookies.get('refresh_token', '')

            # Salvar no banco com tempo de expiração
            success = db.save_tokens(
                token=token,
                e_token=e_token,
                refresh_token=refresh_token,
                cookies=cookies,
                expires_in=TOKEN_DURATION_MINUTES * 60  # converter para segundos
            )

            if success:
                logger.info("💾 Tokens salvos no banco de dados")
            else:
                logger.error("❌ Falha ao salvar tokens no banco")

        except Exception as e:
            logger.error(f"❌ Erro ao salvar tokens no banco: {e}")

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

        IMPORTANTE: Este método tem timeout de 100 segundos via wrapper.

        Returns:
            bool: True se sincronização bem-sucedida, False caso contrário
        """
        try:
            self.sync_count += 1
            sync_start_time = time.time()

            logger.info("=" * 60)
            logger.info(f"🔄 SINCRONIZAÇÃO #{self.sync_count} INICIADA")
            logger.info(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"⏱️ Timeout máximo: 100 segundos")

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

            # Calcular tempo de execução
            sync_duration = time.time() - sync_start_time

            # Log de sucesso
            logger.info("✅ SINCRONIZAÇÃO COMPLETA COM SUCESSO")
            logger.info(f"   Tempo de execução: {sync_duration:.1f}s")
            logger.info(f"   Total de syncs: {self.sync_count}")
            logger.info(f"   Sucessos: {self.success_count}")
            logger.info(f"   Taxa de sucesso: {(self.success_count/self.sync_count)*100:.1f}%")

            # Alerta se está demorando muito
            if sync_duration > 90:
                logger.warning(f"⚠️ Sync demorou {sync_duration:.1f}s (>90s) - risco de sobreposição!")

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

    def perform_sync_with_timeout(self, timeout_seconds=120):
        """
        Executa perform_sync com timeout.

        Args:
            timeout_seconds (int): Timeout máximo em segundos

        Returns:
            bool: True se sucesso, False se falha ou timeout
        """
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self.perform_sync)

            try:
                result = future.result(timeout=timeout_seconds)
                return result
            except FuturesTimeoutError:
                logger.error(f"❌ TIMEOUT: Sync ultrapassou {timeout_seconds}s")
                logger.error("🔨 Forçando limpeza de processos...")

                # Tentar limpar processos órfãos
                kill_orphan_chrome_processes()

                # Marcar como erro
                self.error_count += 1
                self.consecutive_errors += 1
                self.last_sync_success = False

                return False
            except Exception as e:
                logger.error(f"❌ Erro no wrapper de timeout: {e}")
                return False

    def perform_sync_with_retry(self):
        """
        Realiza sincronização com sistema de retry e circuit breaker.

        Returns:
            bool: True se eventualmente bem-sucedida, False se todas tentativas falharam
        """
        # Verificar se sistema está pausado
        if self.paused:
            logger.critical("🛑 Sistema PAUSADO - sync bloqueada")
            logger.critical("   Use endpoint /api/sync/reset para despausar")
            return False

        # Auto-reset temporal: se passou 24h sem sucesso, resetar contador
        if self.consecutive_errors > 0 and self.last_sync:
            hours_since_last = (datetime.utcnow() - self.last_sync).total_seconds() / 3600
            if hours_since_last >= 24:
                old_errors = self.consecutive_errors
                self.consecutive_errors = 0
                logger.warning("=" * 60)
                logger.warning("⏰ AUTO-RESET TEMPORAL: 24h desde última tentativa")
                logger.warning(f"   Erros consecutivos resetados: {old_errors} → 0")
                logger.warning("   Sistema tentará novamente sem circuit breaker")
                logger.warning("=" * 60)

        # Limite máximo absoluto: parar se atingir MAX_ABSOLUTE_FAILURES
        if self.consecutive_errors >= MAX_ABSOLUTE_FAILURES:
            self.paused = True
            logger.critical("=" * 60)
            logger.critical(f"🛑 LIMITE MÁXIMO ATINGIDO: {self.consecutive_errors} erros consecutivos")
            logger.critical(f"   Limite configurado: {MAX_ABSOLUTE_FAILURES}")
            logger.critical("   Sistema PAUSADO - intervenção manual necessária")
            logger.critical("   Use POST /api/sync/reset para resetar e despausar")
            logger.critical("=" * 60)
            self.send_critical_alert(f"Sistema pausado após {self.consecutive_errors} erros consecutivos!")
            return False

        # Circuit breaker: se muitos erros consecutivos, aguardar mais tempo
        if self.consecutive_errors >= 3:
            # Aumentar tempo de espera progressivamente
            if self.consecutive_errors < 5:
                wait_minutes = 4  # 2 ciclos de 2min
            elif self.consecutive_errors < 10:
                wait_minutes = 8  # 4 ciclos
            else:
                wait_minutes = 16  # 8 ciclos (máximo)

            logger.warning(f"⏸️ CIRCUIT BREAKER: {self.consecutive_errors} erros consecutivos")
            logger.warning(f"⏸️ Aguardando {wait_minutes} minutos antes de tentar novamente...")
            logger.warning(f"   (Isso representa {wait_minutes // 2} ciclos de sincronização)")
            time.sleep(wait_minutes * 60)

        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
            logger.info(f"🔄 Tentativa {attempt} de {MAX_RETRY_ATTEMPTS}")

            # Usar versão com timeout (120s - maior margem de segurança)
            if self.perform_sync_with_timeout(timeout_seconds=120):
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