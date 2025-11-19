# driver_manager.py - Gerenciamento robusto de instâncias ChromeDriver
"""
Módulo para gerenciamento seguro e eficiente de instâncias do ChromeDriver.
Resolve problemas de vazamento de memória e travamento em produção.
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager as ChromeDriverInstaller
import threading
import time
import logging
import gc
import os
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime
import psutil

logger = logging.getLogger(__name__)

# Controle global de concorrência
_driver_semaphore = threading.Semaphore(2)  # Máximo 2 drivers simultâneos
_active_drivers = {}  # Rastreamento de drivers ativos
_drivers_lock = threading.Lock()  # Lock para acesso ao dicionário

class DriverMonitor:
    """Monitora drivers ativos e fornece estatísticas"""

    @staticmethod
    def register_driver(driver_id: str, driver):
        """Registra um novo driver criado"""
        with _drivers_lock:
            _active_drivers[driver_id] = {
                'driver': driver,
                'created_at': datetime.now(),
                'thread_id': threading.current_thread().ident
            }
            logger.info(f"📊 Driver registrado: {driver_id} | Total ativos: {len(_active_drivers)}")

    @staticmethod
    def unregister_driver(driver_id: str):
        """Remove um driver do registro"""
        with _drivers_lock:
            if driver_id in _active_drivers:
                del _active_drivers[driver_id]
                logger.info(f"📊 Driver removido: {driver_id} | Total ativos: {len(_active_drivers)}")

    @staticmethod
    def get_active_count() -> int:
        """Retorna número de drivers ativos"""
        with _drivers_lock:
            return len(_active_drivers)

    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Retorna estatísticas detalhadas dos drivers"""
        with _drivers_lock:
            stats = {
                'active_count': len(_active_drivers),
                'drivers': []
            }
            for driver_id, info in _active_drivers.items():
                age = (datetime.now() - info['created_at']).total_seconds()
                stats['drivers'].append({
                    'id': driver_id,
                    'age_seconds': age,
                    'thread_id': info['thread_id']
                })
            return stats

    @staticmethod
    def cleanup_orphaned_drivers(max_age_seconds: int = 300):
        """Remove drivers órfãos mais velhos que max_age_seconds"""
        with _drivers_lock:
            now = datetime.now()
            orphaned = []

            for driver_id, info in _active_drivers.items():
                age = (now - info['created_at']).total_seconds()
                if age > max_age_seconds:
                    orphaned.append(driver_id)

            for driver_id in orphaned:
                logger.warning(f"🧹 Limpando driver órfão: {driver_id} (idade: {age:.0f}s)")
                try:
                    driver = _active_drivers[driver_id]['driver']
                    driver.quit()
                except Exception as e:
                    logger.error(f"❌ Erro ao limpar driver órfão {driver_id}: {e}")
                finally:
                    del _active_drivers[driver_id]

            if orphaned:
                logger.info(f"✅ {len(orphaned)} drivers órfãos removidos")
                gc.collect()  # Forçar garbage collection


class ChromeDriverManager:
    """Context manager para criação e destruição segura do ChromeDriver"""

    def __init__(self, headless: bool = True, timeout: int = 60):
        self.headless = headless
        self.timeout = timeout
        self.driver = None
        self.driver_id = None
        self.creation_time = None

    def __enter__(self):
        """Cria e retorna um driver com garantia de limpeza"""
        # Aguardar semáforo (máximo 2 drivers simultâneos)
        acquired = _driver_semaphore.acquire(timeout=30)
        if not acquired:
            raise Exception("Timeout esperando liberação de driver slot (máximo 2 simultâneos)")

        try:
            self.creation_time = time.time()
            self.driver_id = f"driver_{int(self.creation_time)}_{threading.current_thread().ident}"

            logger.info(f"🚗 Criando ChromeDriver ID: {self.driver_id}")

            # Verificar memória disponível antes de criar
            self._check_memory()

            # Criar driver com proteção contra exceções parciais
            self.driver = self._create_driver_safely()

            # Registrar driver ativo
            DriverMonitor.register_driver(self.driver_id, self.driver)

            # Configurar healthcheck inicial
            self._initial_healthcheck()

            return self.driver

        except Exception as e:
            # Se falhar, liberar semáforo imediatamente
            _driver_semaphore.release()
            logger.error(f"❌ Falha ao criar driver: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Garante que o driver seja fechado, independente de exceções"""
        if self.driver:
            try:
                elapsed = time.time() - self.creation_time
                logger.info(f"⏱️ Driver {self.driver_id} ativo por {elapsed:.1f}s")

                # Tentar fechar gracefully
                self.driver.quit()
                logger.info(f"✅ Driver {self.driver_id} fechado com sucesso")

            except Exception as e:
                logger.error(f"❌ Erro ao fechar driver {self.driver_id}: {e}")
                # Tentar forçar fechamento
                try:
                    self.driver.service.stop()
                except:
                    pass
            finally:
                # Remover do registro
                DriverMonitor.unregister_driver(self.driver_id)
                self.driver = None

                # Liberar semáforo
                _driver_semaphore.release()

                # Forçar garbage collection
                gc.collect()

    def _create_driver_safely(self) -> webdriver.Chrome:
        """Cria driver com proteção contra vazamento em caso de falha parcial"""
        driver = None
        try:
            options = self._get_chrome_options()

            if os.getenv("ENVIRONMENT") == "local":
                # Ambiente local
                service = Service(ChromeDriverInstaller().install())
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Produção (Railway)
                driver = webdriver.Chrome(options=options)

            # Configurar timeouts
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)

            # Anti-detecção
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            logger.info(f"✅ ChromeDriver criado com sucesso: {self.driver_id}")
            return driver

        except Exception as e:
            # Se driver foi criado mas configuração falhou, fechar imediatamente
            if driver:
                try:
                    driver.quit()
                    logger.info("🧹 Driver parcialmente criado foi fechado")
                except:
                    pass
            raise Exception(f"Falha ao criar ChromeDriver: {e}")

    def _get_chrome_options(self) -> Options:
        """Retorna opções do Chrome configuradas para o ambiente"""
        options = Options()

        if os.getenv("ENVIRONMENT") == "local":
            # Local - browser visível
            options.add_argument("--window-size=1366,768")
            logger.info("🔧 Modo LOCAL - Browser visível")
        else:
            # Produção - Railway otimizado
            logger.info("🔧 Modo PRODUÇÃO - Railway")

            # Headless
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

            # Porta de debugging única por processo
            debug_port = 9000 + (os.getpid() % 10000)
            options.add_argument(f"--remote-debugging-port={debug_port}")

            # Otimizações de memória
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            options.add_argument("--renderer-process-limit=1")

            # Desabilitar recursos não necessários
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-sync")
            options.add_argument("--disable-translate")

            # Configurações de rede
            options.add_argument("--aggressive-cache-discard")
            options.add_argument("--disable-background-networking")

            # Tamanho da janela
            options.add_argument("--window-size=1366,768")
            options.add_argument("--start-maximized")

            # Localização do Chrome
            options.binary_location = "/usr/bin/google-chrome"

            # Anti-detecção
            options.add_experimental_option("useAutomationExtension", False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--disable-blink-features=AutomationControlled")

            # Logging
            options.add_argument("--log-level=3")
            options.add_argument("--silent")

            # Estabilidade para containers
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-features=VizDisplayCompositor")

        return options

    def _initial_healthcheck(self):
        """Verifica se o driver está funcionando após criação"""
        try:
            # Teste básico
            self.driver.get("about:blank")
            if self.driver.current_url != "about:blank":
                raise Exception("Driver não navegou corretamente")

            # Teste JavaScript
            result = self.driver.execute_script("return 'OK';")
            if result != "OK":
                raise Exception("JavaScript não está funcionando")

            logger.info(f"✅ Healthcheck inicial passou para {self.driver_id}")

        except Exception as e:
            logger.error(f"❌ Healthcheck falhou para {self.driver_id}: {e}")
            raise

    def _check_memory(self):
        """Verifica memória disponível antes de criar driver"""
        try:
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            used_percent = memory.percent

            logger.info(f"💾 Memória: {available_mb:.0f}MB disponível ({used_percent:.1f}% usado)")

            if used_percent > 85:
                # Tentar limpar drivers órfãos
                DriverMonitor.cleanup_orphaned_drivers(max_age_seconds=120)
                gc.collect()

                # Verificar novamente
                memory = psutil.virtual_memory()
                used_percent = memory.percent

                if used_percent > 90:
                    raise Exception(f"Memória insuficiente: {used_percent:.1f}% usado")
        except ImportError:
            # psutil não instalado, continuar sem verificação
            pass


@contextmanager
def get_chrome_driver(headless: bool = True, timeout: int = 60):
    """
    Context manager conveniente para usar ChromeDriver

    Uso:
        with get_chrome_driver() as driver:
            driver.get("https://example.com")
            # ... fazer operações ...
        # Driver é automaticamente fechado aqui
    """
    manager = ChromeDriverManager(headless=headless, timeout=timeout)
    driver = manager.__enter__()
    try:
        yield driver
    finally:
        manager.__exit__(None, None, None)


def cleanup_all_drivers():
    """Força limpeza de todos os drivers ativos (usar com cuidado)"""
    logger.warning("⚠️ Limpando TODOS os drivers ativos...")

    with _drivers_lock:
        for driver_id, info in list(_active_drivers.items()):
            try:
                driver = info['driver']
                driver.quit()
                logger.info(f"✅ Driver {driver_id} fechado forçadamente")
            except Exception as e:
                logger.error(f"❌ Erro ao fechar driver {driver_id}: {e}")

        _active_drivers.clear()

    # Forçar garbage collection múltiplas vezes
    for _ in range(3):
        gc.collect()
        time.sleep(0.5)

    logger.info("✅ Limpeza completa finalizada")


def get_driver_stats() -> Dict[str, Any]:
    """Retorna estatísticas atuais dos drivers"""
    stats = DriverMonitor.get_stats()

    # Adicionar informações de memória se psutil disponível
    try:
        import psutil
        memory = psutil.virtual_memory()
        stats['memory'] = {
            'used_percent': memory.percent,
            'available_mb': memory.available / (1024 * 1024)
        }
    except ImportError:
        pass

    return stats