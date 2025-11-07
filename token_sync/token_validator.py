"""
Módulo de validação de tokens.

Este módulo é responsável por validar se os tokens obtidos
ainda estão funcionando, fazendo uma chamada de teste à API do EcomHub.
"""

import requests
import json
import logging
from datetime import datetime, timedelta
from .config import VALIDATION_TEST_COUNTRY_ID, SELENIUM_TIMEOUT

logger = logging.getLogger(__name__)

def validate_tokens(cookies, full_test=False):
    """
    Valida se os tokens ainda funcionam fazendo uma chamada à API.

    Args:
        cookies (dict): Dicionário de cookies para validar
        full_test (bool): Se True, faz teste mais completo buscando dados reais

    Returns:
        bool: True se tokens são válidos, False caso contrário
    """
    if not cookies:
        logger.error("Nenhum cookie fornecido para validação")
        return False

    try:
        logger.debug("🔍 Validando tokens...")

        # URL da API do EcomHub
        test_url = "https://api.ecomhub.app/api/orders"

        # Preparar período de teste (últimos 7 dias)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

        # Condições de busca
        conditions = {
            "orders": {
                "date": {
                    "start": start_date,
                    "end": end_date
                },
                "shippingCountry_id": [VALIDATION_TEST_COUNTRY_ID]  # Espanha por padrão
            }
        }

        # Parâmetros da requisição
        params = {
            "offset": 0,
            "orderBy": "null",
            "orderDirection": "null",
            "conditions": json.dumps(conditions),
            "search": ""
        }

        # Headers necessários
        headers = {
            "Accept": "*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://go.ecomhub.app",
            "Referer": "https://go.ecomhub.app/",
            "X-Requested-With": "XMLHttpRequest"
        }

        # Fazer requisição de teste
        response = requests.get(
            test_url,
            params=params,
            headers=headers,
            cookies=cookies,
            timeout=SELENIUM_TIMEOUT
        )

        # Analisar resposta
        if response.status_code == 200:
            # Tokens válidos!
            if full_test:
                try:
                    data = response.json()
                    if isinstance(data, list):
                        logger.info(f"✅ Tokens válidos - API retornou {len(data)} pedidos")
                    else:
                        logger.info(f"✅ Tokens válidos - Resposta tipo: {type(data).__name__}")
                except:
                    logger.info("✅ Tokens válidos - Status 200 recebido")
            else:
                logger.debug("✅ Tokens válidos")

            return True

        elif response.status_code == 401:
            # Tokens expirados ou inválidos
            logger.warning("❌ Tokens inválidos - Status 401 (Unauthorized)")
            return False

        elif response.status_code == 403:
            # Acesso negado
            logger.warning("❌ Tokens inválidos - Status 403 (Forbidden)")
            return False

        else:
            # Status inesperado
            logger.warning(f"⚠️ Status inesperado na validação: {response.status_code}")
            logger.debug(f"Resposta: {response.text[:500]}")

            # Considerar como inválido para ser conservador
            return False

    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout na validação (>{SELENIUM_TIMEOUT}s)")
        return None  # None indica erro de rede, não necessariamente token inválido

    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Erro de conexão na validação: {e}")
        return None

    except Exception as e:
        logger.error(f"❌ Erro inesperado na validação: {e}")
        return None


def estimate_token_expiration(last_sync_time, duration_minutes):
    """
    Estima quando os tokens irão expirar.

    Args:
        last_sync_time (datetime): Hora da última sincronização
        duration_minutes (int): Duração estimada dos tokens em minutos

    Returns:
        datetime: Tempo estimado de expiração
        bool: True se provavelmente ainda válido, False se provavelmente expirado
    """
    if not last_sync_time:
        logger.warning("Sem tempo de última sincronização")
        return None, False

    expiration_time = last_sync_time + timedelta(minutes=duration_minutes)
    current_time = datetime.utcnow()

    is_probably_valid = current_time < expiration_time

    if is_probably_valid:
        remaining_minutes = (expiration_time - current_time).total_seconds() / 60
        logger.debug(f"⏰ Tokens provavelmente válidos por mais {remaining_minutes:.1f} minutos")
    else:
        expired_minutes = (current_time - expiration_time).total_seconds() / 60
        logger.warning(f"⚠️ Tokens provavelmente expiraram há {expired_minutes:.1f} minutos")

    return expiration_time, is_probably_valid


def quick_validate(cookies):
    """
    Validação rápida dos tokens (não faz chamada à API).

    Apenas verifica se os cookies essenciais estão presentes.

    Args:
        cookies (dict): Dicionário de cookies

    Returns:
        bool: True se cookies parecem válidos, False caso contrário
    """
    if not cookies:
        return False

    # Cookies essenciais que devem estar presentes
    essential_cookies = ['token', 'e_token']

    for cookie_name in essential_cookies:
        if cookie_name not in cookies:
            logger.warning(f"Cookie essencial ausente: {cookie_name}")
            return False

        if not cookies[cookie_name]:
            logger.warning(f"Cookie essencial vazio: {cookie_name}")
            return False

    logger.debug(f"✅ Validação rápida OK - Cookies essenciais presentes")
    return True


def validate_token_response(tokens_data):
    """
    Valida a estrutura completa da resposta de tokens.

    Args:
        tokens_data (dict): Dados completos dos tokens

    Returns:
        bool: True se estrutura válida, False caso contrário
    """
    if not tokens_data:
        logger.error("Dados de tokens vazios")
        return False

    # Campos obrigatórios
    required_fields = ['cookies', 'headers', 'timestamp']

    for field in required_fields:
        if field not in tokens_data:
            logger.error(f"Campo obrigatório ausente: {field}")
            return False

    # Validar cookies
    if not quick_validate(tokens_data.get('cookies')):
        return False

    # Validar headers
    headers = tokens_data.get('headers', {})
    if not headers.get('User-Agent'):
        logger.warning("User-Agent ausente nos headers")

    logger.debug("✅ Estrutura de tokens válida")
    return True


def test_token_endpoint(base_url, cookies):
    """
    Testa um endpoint específico com os tokens.

    Útil para testar diferentes endpoints ou debugging.

    Args:
        base_url (str): URL base para teste
        cookies (dict): Cookies para usar

    Returns:
        tuple: (status_code, response_text)
    """
    try:
        response = requests.get(
            base_url,
            cookies=cookies,
            timeout=10,
            headers={"Accept": "*/*"}
        )

        return response.status_code, response.text[:500]

    except Exception as e:
        logger.error(f"Erro ao testar endpoint {base_url}: {e}")
        return None, str(e)