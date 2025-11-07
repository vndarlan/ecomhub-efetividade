"""
Script para descobrir quanto tempo os tokens do EcomHub permanecem válidos.

Este script:
1. Obtém tokens frescos via Selenium
2. Testa a validade dos tokens a cada 10 minutos
3. Registra quando os tokens expiram
4. Salva o resultado em um arquivo de log

Uso: python test_token_duration.py
"""

import time
import requests
import json
import logging
from datetime import datetime
import sys
import os

# Adicionar o diretório atual ao path para importar do main
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import create_driver, login_ecomhub, get_auth_cookies

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('token_duration_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_api_with_tokens(cookies):
    """
    Testa se os tokens ainda são válidos fazendo uma chamada à API.

    Returns:
        True se os tokens são válidos, False se expiraram
    """
    try:
        test_url = "https://api.ecomhub.app/api/orders"

        # Buscar pedidos dos últimos 7 dias como teste
        conditions = {
            "orders": {
                "date": {
                    "start": "2024-11-01",
                    "end": "2024-11-07"
                },
                "shippingCountry_id": [164]  # Espanha
            }
        }

        params = {
            "offset": 0,
            "orderBy": "null",
            "orderDirection": "null",
            "conditions": json.dumps(conditions),
            "search": ""
        }

        headers = {
            "Accept": "*/*",
            "Origin": "https://go.ecomhub.app",
            "Referer": "https://go.ecomhub.app/"
        }

        response = requests.get(
            test_url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=30
        )

        if response.status_code == 200:
            # Tokens ainda válidos
            data = response.json()
            logger.info(f"✅ Tokens válidos - Resposta com {len(data) if isinstance(data, list) else 0} pedidos")
            return True
        elif response.status_code == 401:
            # Tokens expirados
            logger.warning("❌ Tokens expirados - Status 401")
            return False
        else:
            # Status inesperado
            logger.warning(f"⚠️ Status inesperado: {response.status_code}")
            logger.debug(f"Resposta: {response.text[:200]}")
            return None

    except Exception as e:
        logger.error(f"Erro ao testar tokens: {e}")
        return None

def test_token_validity():
    """
    Função principal que descobre quanto tempo os tokens permanecem válidos.
    """
    logger.info("=" * 60)
    logger.info("TESTE DE DURAÇÃO DE TOKENS ECOMHUB")
    logger.info("=" * 60)

    try:
        # Passo 1: Obter tokens frescos
        logger.info("Obtendo tokens frescos via Selenium...")

        driver = None
        try:
            driver = create_driver()
            login_success = login_ecomhub(driver)

            if not login_success:
                logger.error("Falha no login no EcomHub")
                return

            cookies = get_auth_cookies(driver)
            driver.quit()

            logger.info(f"✅ Tokens obtidos com sucesso: {list(cookies.keys())}")

        except Exception as e:
            logger.error(f"Erro ao obter tokens: {e}")
            if driver:
                driver.quit()
            return

        # Passo 2: Testar validade inicial
        logger.info("\nTestando validade inicial dos tokens...")
        if not test_api_with_tokens(cookies):
            logger.error("Tokens inválidos logo após obtenção! Abortando teste.")
            return

        # Passo 3: Loop de teste de validade
        start_time = datetime.now()
        test_interval_seconds = 600  # 10 minutos
        test_number = 0

        logger.info(f"\nIniciando loop de teste (intervalo: {test_interval_seconds/60:.0f} minutos)")
        logger.info(f"Início: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 60)

        while True:
            # Aguardar intervalo
            logger.info(f"Aguardando {test_interval_seconds/60:.0f} minutos para próximo teste...")
            time.sleep(test_interval_seconds)

            test_number += 1
            elapsed_time = datetime.now() - start_time
            elapsed_minutes = elapsed_time.total_seconds() / 60

            logger.info(f"\n[Teste #{test_number}] Tempo decorrido: {elapsed_minutes:.0f} minutos")

            # Testar validade
            token_valid = test_api_with_tokens(cookies)

            if token_valid is False:
                # Tokens expiraram!
                logger.info("=" * 60)
                logger.info(f"🔴 TOKENS EXPIRARAM!")
                logger.info(f"Duração total: {elapsed_minutes:.0f} minutos ({elapsed_time})")
                logger.info(f"Hora de expiração: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)

                # Salvar resultado
                result = {
                    "duration_minutes": int(elapsed_minutes),
                    "duration_readable": str(elapsed_time),
                    "start_time": start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "tests_performed": test_number
                }

                with open("token_duration_result.json", "w") as f:
                    json.dump(result, f, indent=2)

                logger.info(f"Resultado salvo em token_duration_result.json")
                logger.info(f"\n🎯 RECOMENDAÇÃO: Configurar TOKEN_DURATION_MINUTES={int(elapsed_minutes)} no .env")
                logger.info(f"   Intervalo de renovação sugerido: {int(elapsed_minutes * 0.7)} minutos")
                break

            elif token_valid is True:
                logger.info(f"✅ Tokens ainda válidos após {elapsed_minutes:.0f} minutos")

                # Se passar de 24 horas, considerar que não expiram
                if elapsed_minutes > 1440:  # 24 horas
                    logger.info("=" * 60)
                    logger.info("⚠️ Teste rodando há mais de 24 horas!")
                    logger.info("Tokens parecem ter duração muito longa ou indefinida.")
                    logger.info("Considere usar TOKEN_DURATION_MINUTES=1440 (24h)")
                    logger.info("=" * 60)
                    break
            else:
                # Erro no teste - tentar novamente no próximo ciclo
                logger.warning("⚠️ Erro no teste - continuando...")

    except KeyboardInterrupt:
        logger.info("\n\n⚠️ Teste interrompido pelo usuário")
        elapsed = datetime.now() - start_time if 'start_time' in locals() else None
        if elapsed:
            logger.info(f"Tempo decorrido até interrupção: {elapsed}")
    except Exception as e:
        logger.error(f"Erro crítico no teste: {e}", exc_info=True)

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTE DE DURAÇÃO DE TOKENS - ECOMHUB")
    print("=" * 60)
    print("\nEste teste pode demorar várias horas para completar.")
    print("O script testará a validade dos tokens a cada 10 minutos")
    print("até que eles expirem.\n")
    print("Você pode interromper a qualquer momento com Ctrl+C\n")

    input("Pressione ENTER para iniciar o teste...")

    test_token_validity()