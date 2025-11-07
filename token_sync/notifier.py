"""
Módulo de notificação para envio de tokens ao Chegou Hub.

Este módulo é responsável por enviar os tokens atualizados
para o Chegou Hub ou qualquer outro webhook configurado.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Importar httpx para requisições assíncronas (se disponível) ou usar requests
try:
    import httpx
    USE_HTTPX = True
except ImportError:
    import requests
    USE_HTTPX = False
    logging.warning("httpx não disponível, usando requests")

from .config import (
    CHEGOU_HUB_WEBHOOK_URL,
    CHEGOU_HUB_API_KEY,
    CHEGOU_HUB_TIMEOUT,
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    RETRY_EXPONENTIAL_BACKOFF
)

logger = logging.getLogger(__name__)


def prepare_payload(tokens_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepara o payload para envio ao Chegou Hub.

    Args:
        tokens_data: Dados dos tokens obtidos

    Returns:
        Payload formatado para envio
    """
    # Adicionar metadados extras
    payload = {
        **tokens_data,
        "source": "ecomhub-api-token-sync",
        "environment": "production",
        "sent_at": datetime.utcnow().isoformat() + "Z"
    }

    # Remover dados sensíveis se necessário
    # (por enquanto mantemos tudo)

    return payload


def send_to_chegou_hub(tokens_data: Dict[str, Any]) -> bool:
    """
    Envia tokens atualizados para o Chegou Hub.

    Args:
        tokens_data: Dados dos tokens para enviar

    Returns:
        True se enviado com sucesso, False caso contrário
    """
    if not CHEGOU_HUB_WEBHOOK_URL:
        logger.warning("URL do Chegou Hub não configurada - pulando envio")
        return False

    logger.info(f"📤 Enviando tokens para Chegou Hub: {CHEGOU_HUB_WEBHOOK_URL}")

    try:
        # Preparar dados
        payload = prepare_payload(tokens_data)

        # Preparar headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "EcomHub-Token-Sync/1.0"
        }

        # Adicionar autenticação se configurada
        if CHEGOU_HUB_API_KEY:
            headers["Authorization"] = f"Bearer {CHEGOU_HUB_API_KEY}"
            logger.debug("Autenticação adicionada ao request")

        # Enviar usando httpx ou requests
        if USE_HTTPX:
            response = _send_with_httpx(CHEGOU_HUB_WEBHOOK_URL, payload, headers)
        else:
            response = _send_with_requests(CHEGOU_HUB_WEBHOOK_URL, payload, headers)

        # Analisar resposta
        if response and response.get("status_code") in [200, 201, 202, 204]:
            logger.info(f"✅ Tokens enviados com sucesso - Status: {response['status_code']}")

            # Log da resposta se houver
            if response.get("body"):
                logger.debug(f"Resposta do Chegou Hub: {response['body'][:200]}")

            return True
        else:
            status = response.get("status_code", "unknown") if response else "error"
            logger.error(f"❌ Falha no envio - Status: {status}")

            if response and response.get("body"):
                logger.debug(f"Resposta de erro: {response['body'][:500]}")

            return False

    except Exception as e:
        logger.error(f"❌ Erro ao enviar para Chegou Hub: {e}")
        return False


def _send_with_httpx(url: str, payload: Dict, headers: Dict) -> Optional[Dict]:
    """
    Envia dados usando httpx (assíncrono).

    Args:
        url: URL de destino
        payload: Dados para enviar
        headers: Headers HTTP

    Returns:
        Dicionário com status_code e body da resposta
    """
    try:
        with httpx.Client(timeout=CHEGOU_HUB_TIMEOUT) as client:
            response = client.post(
                url,
                json=payload,
                headers=headers
            )

            return {
                "status_code": response.status_code,
                "body": response.text,
                "headers": dict(response.headers)
            }

    except httpx.TimeoutException:
        logger.error(f"⏱️ Timeout ao enviar para {url} ({CHEGOU_HUB_TIMEOUT}s)")
        return None
    except httpx.ConnectError as e:
        logger.error(f"🔌 Erro de conexão: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro httpx: {e}")
        return None


def _send_with_requests(url: str, payload: Dict, headers: Dict) -> Optional[Dict]:
    """
    Envia dados usando requests (síncrono).

    Args:
        url: URL de destino
        payload: Dados para enviar
        headers: Headers HTTP

    Returns:
        Dicionário com status_code e body da resposta
    """
    try:
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=CHEGOU_HUB_TIMEOUT
        )

        return {
            "status_code": response.status_code,
            "body": response.text,
            "headers": dict(response.headers)
        }

    except requests.exceptions.Timeout:
        logger.error(f"⏱️ Timeout ao enviar para {url} ({CHEGOU_HUB_TIMEOUT}s)")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.error(f"🔌 Erro de conexão: {e}")
        return None
    except Exception as e:
        logger.error(f"Erro requests: {e}")
        return None


def send_with_retry(tokens_data: Dict[str, Any]) -> bool:
    """
    Envia tokens com sistema de retry.

    Args:
        tokens_data: Dados dos tokens para enviar

    Returns:
        True se eventualmente enviado, False se todas tentativas falharam
    """
    import time

    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        logger.info(f"🔄 Tentativa de envio {attempt}/{MAX_RETRY_ATTEMPTS}")

        if send_to_chegou_hub(tokens_data):
            logger.info(f"✅ Enviado na tentativa {attempt}")
            return True

        if attempt < MAX_RETRY_ATTEMPTS:
            # Calcular delay
            if RETRY_EXPONENTIAL_BACKOFF:
                delay = RETRY_DELAY_SECONDS * (2 ** (attempt - 1))
            else:
                delay = RETRY_DELAY_SECONDS

            logger.info(f"⏳ Aguardando {delay}s antes da próxima tentativa...")
            time.sleep(delay)

    logger.error(f"❌ Todas as {MAX_RETRY_ATTEMPTS} tentativas de envio falharam")
    return False


def test_webhook_connectivity(url: str = None, api_key: str = None) -> bool:
    """
    Testa a conectividade com o webhook do Chegou Hub.

    Args:
        url: URL para testar (usa configuração padrão se não fornecida)
        api_key: API key (usa configuração padrão se não fornecida)

    Returns:
        True se webhook acessível, False caso contrário
    """
    test_url = url or CHEGOU_HUB_WEBHOOK_URL
    test_key = api_key or CHEGOU_HUB_API_KEY

    if not test_url:
        logger.error("Nenhuma URL configurada para teste")
        return False

    logger.info(f"🔍 Testando conectividade com: {test_url}")

    # Payload de teste
    test_payload = {
        "test": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "message": "Teste de conectividade do Token Sync Service"
    }

    # Headers
    headers = {"Content-Type": "application/json"}
    if test_key:
        headers["Authorization"] = f"Bearer {test_key}"

    try:
        if USE_HTTPX:
            with httpx.Client(timeout=5) as client:
                response = client.post(test_url, json=test_payload, headers=headers)
                status = response.status_code
        else:
            response = requests.post(test_url, json=test_payload, headers=headers, timeout=5)
            status = response.status_code

        if status < 500:  # Qualquer coisa exceto erro de servidor
            logger.info(f"✅ Webhook acessível - Status: {status}")
            return True
        else:
            logger.error(f"❌ Webhook retornou erro de servidor: {status}")
            return False

    except Exception as e:
        logger.error(f"❌ Erro ao testar webhook: {e}")
        return False


def format_tokens_for_display(tokens_data: Dict[str, Any]) -> str:
    """
    Formata tokens para exibição segura (oculta valores sensíveis).

    Args:
        tokens_data: Dados dos tokens

    Returns:
        String formatada para log
    """
    if not tokens_data:
        return "No tokens"

    safe_data = {}

    # Cookies - mostrar apenas chaves
    if "cookies" in tokens_data:
        safe_data["cookies"] = list(tokens_data["cookies"].keys())

    # Cookie string - mostrar apenas tamanho
    if "cookie_string" in tokens_data:
        safe_data["cookie_string_length"] = len(tokens_data["cookie_string"])

    # Headers - mostrar sem valores sensíveis
    if "headers" in tokens_data:
        safe_headers = {}
        for key, value in tokens_data["headers"].items():
            if key.lower() in ["authorization", "cookie"]:
                safe_headers[key] = "***hidden***"
            else:
                safe_headers[key] = value[:50] + "..." if len(value) > 50 else value
        safe_data["headers"] = safe_headers

    # Outros campos seguros
    for key in ["timestamp", "valid_until_estimate", "sync_number"]:
        if key in tokens_data:
            safe_data[key] = tokens_data[key]

    return json.dumps(safe_data, indent=2)