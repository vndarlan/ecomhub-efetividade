#!/usr/bin/env python
"""
Script para executar o serviço de sincronização de tokens de forma independente.

Útil para:
- Testar o serviço sem iniciar o servidor FastAPI
- Rodar como processo separado
- Deploy independente no Railway

Uso:
    python run_token_sync.py
"""

import os
import sys
import logging
import signal
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('token_sync_standalone.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Função principal para executar o serviço."""
    logger.info("=" * 60)
    logger.info("TOKEN SYNC SERVICE - MODO STANDALONE")
    logger.info("=" * 60)
    logger.info(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Verificar se está habilitado
    if not os.getenv("TOKEN_SYNC_ENABLED", "false").lower() == "true":
        logger.error("❌ TOKEN_SYNC_ENABLED não está habilitado no .env")
        logger.info("Configure TOKEN_SYNC_ENABLED=true para executar")
        sys.exit(1)

    # Verificar credenciais
    if not os.getenv("ECOMHUB_EMAIL") or not os.getenv("ECOMHUB_PASSWORD"):
        logger.warning("⚠️ Credenciais EcomHub não configuradas no .env")
        logger.info("Usando valores padrão do código (não recomendado)")

    # Importar e iniciar o scheduler
    try:
        from token_sync.scheduler import get_scheduler_instance

        logger.info("📦 Módulos carregados com sucesso")

        # Obter instância do scheduler
        scheduler = get_scheduler_instance()
        if not scheduler:
            logger.error("❌ Não foi possível criar instância do scheduler")
            logger.info("Verifique se APScheduler está instalado: pip install apscheduler")
            sys.exit(1)

        # Configurar handler para shutdown gracioso
        def signal_handler(sig, frame):
            logger.info(f"\n📍 Sinal {sig} recebido - encerrando graciosamente...")
            if scheduler:
                scheduler.stop()
            logger.info("👋 Serviço encerrado")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar o scheduler
        logger.info("🚀 Iniciando scheduler...")
        if scheduler.start():
            logger.info("✅ Serviço rodando com sucesso!")
            logger.info("Pressione Ctrl+C para parar")
            logger.info("-" * 60)

            # Manter o processo vivo
            import time
            while scheduler.is_running:
                time.sleep(60)  # Check a cada minuto

                # Opcional: mostrar status periodicamente
                if datetime.now().minute % 15 == 0:  # A cada 15 minutos
                    status = scheduler.get_status()
                    logger.info(f"📊 Status: Syncs={status['sync_count']}, "
                              f"Erros={status['error_count']}, "
                              f"Próxima em {status.get('minutes_until_next', 0):.1f} min")

        else:
            logger.error("❌ Falha ao iniciar o serviço")
            sys.exit(1)

    except ImportError as e:
        logger.error(f"❌ Erro ao importar módulos: {e}")
        logger.info("Certifique-se de que todas as dependências estão instaladas:")
        logger.info("  pip install -r requirements.txt")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⚠️ Interrompido pelo usuário")
        if 'scheduler' in locals():
            scheduler.stop()
        sys.exit(0)

    except Exception as e:
        logger.error(f"❌ Erro crítico: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TOKEN SYNC SERVICE - Sincronização Automática de Tokens")
    print("=" * 60)
    print("\nEste serviço mantém tokens EcomHub sempre atualizados.")
    print("Configurações são lidas do arquivo .env\n")

    # Verificar configuração básica
    sync_enabled = os.getenv("TOKEN_SYNC_ENABLED", "false").lower() == "true"
    interval = os.getenv("SYNC_INTERVAL_MINUTES", "42")

    print(f"Status: {'HABILITADO ✅' if sync_enabled else 'DESABILITADO ❌'}")
    print(f"Intervalo: {interval} minutos")

    chegou_hub_url = os.getenv("CHEGOU_HUB_WEBHOOK_URL", "")
    if chegou_hub_url:
        print(f"Chegou Hub: {chegou_hub_url[:50]}...")
    else:
        print("Chegou Hub: NÃO CONFIGURADO")

    print("\n" + "-" * 60)

    if not sync_enabled:
        print("\n⚠️ ATENÇÃO: Serviço está desabilitado!")
        print("Configure TOKEN_SYNC_ENABLED=true no arquivo .env\n")
        response = input("Deseja continuar mesmo assim? (s/N): ")
        if response.lower() != 's':
            print("Abortado.")
            sys.exit(0)

    print("\nIniciando serviço...\n")
    main()