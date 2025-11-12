"""
Agendador para sincronização automática de tokens.

Este módulo gerencia o agendamento automático das sincronizações
usando APScheduler para executar em intervalos regulares.
"""

import logging
import signal
import sys
from datetime import datetime, timedelta
from typing import Optional

# Tentar importar APScheduler
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, EVENT_JOB_MISSED
    SCHEDULER_AVAILABLE = True
except ImportError:
    SCHEDULER_AVAILABLE = False
    logging.warning("APScheduler não instalado. Instale com: pip install apscheduler")

from .config import (
    TOKEN_SYNC_ENABLED,
    SYNC_INTERVAL_MINUTES,
    SYNC_ON_STARTUP,
    TOKEN_DURATION_MINUTES
)
from .sync_service import get_service_instance

logger = logging.getLogger(__name__)


class TokenScheduler:
    """
    Gerenciador de agendamento para sincronização de tokens.

    Usa APScheduler para executar sincronizações em intervalos regulares.
    """

    def __init__(self):
        """Inicializa o agendador."""
        self.scheduler = None
        self.sync_service = None
        self.is_running = False
        self.job_id = "token_sync_job"
        self.start_time = None
        self.last_execution = None
        self.execution_count = 0
        self.error_count = 0

        if not SCHEDULER_AVAILABLE:
            logger.error("APScheduler não disponível - agendamento desabilitado")
            return

        # Criar scheduler
        self.scheduler = BackgroundScheduler(
            timezone="UTC",
            job_defaults={
                'coalesce': True,  # Se múltiplas execuções pendentes, executar apenas uma
                'max_instances': 1,  # Apenas 1 instância por vez para evitar contenção
                'misfire_grace_time': 120  # Aceitar execução até 2min atrasada
            }
        )

        # Adicionar listeners para eventos
        self.scheduler.add_listener(self._on_job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self.scheduler.add_listener(self._on_job_missed, EVENT_JOB_MISSED)

        # Obter instância do serviço
        self.sync_service = get_service_instance()

        logger.info("✅ TokenScheduler inicializado")

    def start(self):
        """
        Inicia o agendador de sincronização.

        Returns:
            bool: True se iniciado com sucesso, False caso contrário
        """
        if not TOKEN_SYNC_ENABLED:
            logger.info("ℹ️ Sincronização de tokens está DESABILITADA")
            return False

        if not SCHEDULER_AVAILABLE:
            logger.error("APScheduler não disponível")
            return False

        if self.is_running:
            logger.warning("Agendador já está rodando")
            return True

        try:
            logger.info("=" * 60)
            logger.info("🚀 INICIANDO AGENDADOR DE SINCRONIZAÇÃO")
            logger.info(f"Intervalo: {SYNC_INTERVAL_MINUTES} minutos")
            logger.info(f"Duração dos tokens: {TOKEN_DURATION_MINUTES} minutos")
            logger.info(f"Margem de segurança: {TOKEN_DURATION_MINUTES - SYNC_INTERVAL_MINUTES} minutos")

            # Sincronização inicial se configurado
            if SYNC_ON_STARTUP:
                logger.info("📍 Executando sincronização inicial...")
                try:
                    self.sync_service.perform_sync_with_retry()
                    self.last_execution = datetime.utcnow()
                except Exception as e:
                    logger.error(f"Erro na sincronização inicial: {e}")
                    # Continuar mesmo com erro

            # Agendar próximas sincronizações
            self.scheduler.add_job(
                func=self._sync_job,
                trigger=IntervalTrigger(minutes=SYNC_INTERVAL_MINUTES),
                id=self.job_id,
                name="Token Synchronization Job",
                replace_existing=True,
                next_run_time=datetime.utcnow() + timedelta(minutes=SYNC_INTERVAL_MINUTES)
            )

            # Iniciar scheduler
            self.scheduler.start()
            self.is_running = True
            self.start_time = datetime.utcnow()

            # Próxima execução
            next_run = self.get_next_run_time()
            if next_run:
                logger.info(f"⏰ Próxima sincronização: {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC")

            logger.info("✅ AGENDADOR INICIADO COM SUCESSO")
            logger.info("=" * 60)

            # Configurar handlers para shutdown gracioso
            self._setup_signal_handlers()

            return True

        except Exception as e:
            logger.error(f"❌ Erro ao iniciar agendador: {e}")
            return False

    def stop(self):
        """Para o agendador."""
        if not self.is_running:
            logger.warning("Agendador não está rodando")
            return

        logger.info("🛑 Parando agendador...")

        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=True)

            self.is_running = False

            # Estatísticas finais
            if self.start_time:
                uptime = datetime.utcnow() - self.start_time
                logger.info(f"📊 Estatísticas finais:")
                logger.info(f"   Uptime: {uptime}")
                logger.info(f"   Execuções: {self.execution_count}")
                logger.info(f"   Erros: {self.error_count}")
                if self.execution_count > 0:
                    success_rate = ((self.execution_count - self.error_count) / self.execution_count) * 100
                    logger.info(f"   Taxa de sucesso: {success_rate:.1f}%")

            logger.info("✅ Agendador parado com sucesso")

        except Exception as e:
            logger.error(f"Erro ao parar agendador: {e}")

    def _sync_job(self):
        """Job de sincronização executado pelo scheduler."""
        logger.info(f"⏰ Execução agendada #{self.execution_count + 1}")

        try:
            # Executar sincronização com retry
            success = self.sync_service.perform_sync_with_retry()

            if success:
                self.last_execution = datetime.utcnow()
                self.execution_count += 1
            else:
                self.error_count += 1

            return success

        except Exception as e:
            logger.error(f"Erro no job de sincronização: {e}")
            self.error_count += 1
            raise

    def _on_job_executed(self, event):
        """Callback quando job é executado com sucesso."""
        if event.job_id == self.job_id:
            logger.debug(f"✅ Job executado: {event.job_id}")
            # Próxima execução
            next_run = self.get_next_run_time()
            if next_run:
                try:
                    # Converter next_run para naive se tiver timezone
                    if hasattr(next_run, 'replace') and next_run.tzinfo:
                        next_run_naive = next_run.replace(tzinfo=None)
                    else:
                        next_run_naive = next_run

                    time_until = (next_run_naive - datetime.utcnow()).total_seconds() / 60
                    logger.info(f"⏰ Próxima sincronização em {time_until:.1f} minutos")
                except Exception as e:
                    logger.debug(f"Erro ao calcular tempo até próxima execução: {e}")

    def _on_job_error(self, event):
        """Callback quando job tem erro."""
        if event.job_id == self.job_id:
            logger.error(f"❌ Erro no job: {event.exception}")
            self.error_count += 1

    def _on_job_missed(self, event):
        """Callback quando job é perdido."""
        if event.job_id == self.job_id:
            logger.warning(f"⚠️ Execução perdida: {event.job_id}")
            # Tentar executar imediatamente
            logger.info("Tentando executar agora...")
            try:
                self._sync_job()
            except:
                pass

    def get_next_run_time(self) -> Optional[datetime]:
        """
        Obtém o horário da próxima execução agendada.

        Returns:
            datetime da próxima execução ou None
        """
        if not self.scheduler or not self.is_running:
            return None

        job = self.scheduler.get_job(self.job_id)
        if job:
            return job.next_run_time

        return None

    def get_status(self) -> dict:
        """
        Retorna o status atual do agendador.

        Returns:
            Dicionário com informações de status
        """
        status = {
            "scheduler_available": SCHEDULER_AVAILABLE,
            "is_running": self.is_running,
            "sync_enabled": TOKEN_SYNC_ENABLED,
            "interval_minutes": SYNC_INTERVAL_MINUTES,
            "execution_count": self.execution_count,
            "error_count": self.error_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None,
            "start_time": self.start_time.isoformat() if self.start_time else None
        }

        # Adicionar próxima execução
        next_run = self.get_next_run_time()
        if next_run:
            status["next_execution"] = next_run.isoformat()
            status["minutes_until_next"] = (next_run - datetime.utcnow()).total_seconds() / 60

        # Adicionar uptime
        if self.start_time and self.is_running:
            uptime = datetime.utcnow() - self.start_time
            status["uptime_seconds"] = uptime.total_seconds()
            status["uptime_readable"] = str(uptime)

        # Adicionar status do serviço
        if self.sync_service:
            status["service_status"] = self.sync_service.get_status()

        return status

    def trigger_sync_now(self) -> bool:
        """
        Dispara uma sincronização imediata (fora do agendamento).

        Returns:
            bool: True se sincronização executada, False caso contrário
        """
        logger.info("🔄 Sincronização manual solicitada")

        if not self.sync_service:
            logger.error("Serviço de sincronização não disponível")
            return False

        try:
            success = self.sync_service.perform_sync_with_retry()
            if success:
                self.last_execution = datetime.utcnow()
                self.execution_count += 1
            else:
                self.error_count += 1
            return success

        except Exception as e:
            logger.error(f"Erro na sincronização manual: {e}")
            self.error_count += 1
            return False

    def _setup_signal_handlers(self):
        """Configura handlers para shutdown gracioso."""
        # Signal handlers só funcionam na thread principal
        # BackgroundScheduler já tem seu próprio sistema de shutdown
        import threading
        if threading.current_thread() is not threading.main_thread():
            logger.debug("Não é thread principal - pulando configuração de signal handlers")
            return

        try:
            def signal_handler(sig, frame):
                logger.info(f"\n📍 Sinal {sig} recebido - encerrando graciosamente...")
                self.stop()
                sys.exit(0)

            # Registrar handlers
            signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # Kill

            logger.debug("Signal handlers configurados")
        except ValueError as e:
            # Erro esperado se não estiver na thread principal
            logger.debug(f"Não foi possível configurar signal handlers: {e}")


# Instância global do scheduler
_scheduler_instance = None


def get_scheduler_instance() -> Optional[TokenScheduler]:
    """
    Retorna a instância singleton do scheduler.

    Returns:
        TokenScheduler ou None se não disponível
    """
    global _scheduler_instance

    if not SCHEDULER_AVAILABLE:
        return None

    if _scheduler_instance is None:
        _scheduler_instance = TokenScheduler()

    return _scheduler_instance


def start_background_sync():
    """
    Função auxiliar para iniciar sincronização em background.

    Usada para iniciar em thread separada.
    """
    scheduler = get_scheduler_instance()
    if scheduler:
        scheduler.start()
        # Manter thread viva
        import time
        try:
            while scheduler.is_running:
                time.sleep(60)  # Check a cada minuto
        except KeyboardInterrupt:
            logger.info("Interrompido pelo usuário")
            scheduler.stop()
    else:
        logger.error("Scheduler não disponível")


# Exportar instância e função
token_scheduler = get_scheduler_instance()