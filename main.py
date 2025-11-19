# main_refactored.py - Versão refatorada com gerenciamento robusto de drivers
"""
Versão refatorada do main.py com correções para vazamento de memória e travamentos.
Esta versão usa o ChromeDriverManager para gerenciamento seguro de drivers.
"""

from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from collections import defaultdict
import logging
import requests
import urllib.parse
import json
from datetime import datetime
from typing import Dict, Optional
import gc

# Importar o novo gerenciador de drivers
from driver_manager import get_chrome_driver, DriverMonitor, cleanup_all_drivers, get_driver_stats

# Rate Limiting
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address)
    RATE_LIMITING_ENABLED = True
except ImportError:
    limiter = None
    RATE_LIMITING_ENABLED = False
    print("AVISO: SlowAPI não instalado - Rate limiting desabilitado")

app = FastAPI(title="EcomHub Selenium Automation - Refactored", version="2.0.0")

# Configurar rate limiting se disponível
if RATE_LIMITING_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Função auxiliar para aplicar rate limiting condicionalmente
def apply_rate_limit(limit_string):
    """Retorna decorator de rate limit se habilitado, caso contrário retorna decorator vazio"""
    if RATE_LIMITING_ENABLED and limiter:
        return limiter.limit(limit_string)
    else:
        # Decorator vazio que não faz nada
        def decorator(func):
            return func
        return decorator

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuração de CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Configuração de Autenticação via API Key
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verifica se a API Key é válida"""
    expected_api_key = os.getenv("API_SECRET_KEY")

    if not expected_api_key:
        logger.error("API_SECRET_KEY não configurada no servidor")
        raise HTTPException(
            status_code=500,
            detail="Servidor mal configurado - contate o administrador"
        )

    if not api_key:
        raise HTTPException(
            status_code=403,
            detail="API Key não fornecida. Adicione o header 'X-API-Key'"
        )

    if api_key != expected_api_key:
        raise HTTPException(
            status_code=403,
            detail="API Key inválida"
        )

    return api_key

# Models
class ProcessRequest(BaseModel):
    data_inicio: str  # YYYY-MM-DD
    data_fim: str     # YYYY-MM-DD
    pais_id: str      # ID do país ou "todos"

class ProcessResponse(BaseModel):
    status: str
    dados_processados: Dict
    estatisticas: Dict
    message: Optional[str] = None

# Constantes
ECOMHUB_URL = "https://app.ecomhub.app/login"
API_BASE_URL = "https://api.ecomhub.app/api"

# Credenciais hardcoded (temporariamente)
LOGIN_EMAIL = os.getenv("ECOMHUB_EMAIL", "saviomendesalvess@gmail.com")
LOGIN_PASSWORD = os.getenv("ECOMHUB_PASSWORD", "Chegou123!")

# Mapa de países
PAISES_MAP = {
    "164": "Espanha",
    "41": "Croácia",
    "66": "Grécia",
    "82": "Itália",
    "142": "Romênia",
    "44": "República Checa",
    "139": "Polônia",
    "todos": "Todos os Países"
}

# IDs dos países para consulta "todos"
TODOS_PAISES_IDS = ["164", "41", "66", "82", "142", "44", "139"]


def safe_operation(func):
    """
    Decorator simplificado para operações - SEM RETRY de driver
    Apenas adiciona logging e tratamento de erro
    """
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


def clean_driver_state(driver):
    """Limpa cookies e cache do driver para evitar interferência entre requisições"""
    logger.info("🧹 Limpando estado do driver...")

    try:
        # Limpar todos os cookies
        driver.delete_all_cookies()
        logger.info("✅ Cookies limpos")

        # Limpar localStorage e sessionStorage via JavaScript
        try:
            driver.execute_script("window.localStorage.clear();")
            driver.execute_script("window.sessionStorage.clear();")
            logger.info("✅ LocalStorage e SessionStorage limpos")
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível limpar storage: {e}")

        logger.info("✅ Estado do driver limpo com sucesso")
        return True

    except Exception as e:
        logger.warning(f"⚠️ Erro ao limpar estado do driver: {e}")
        # Não falhar se limpeza falhar, apenas logar warning
        return False


def healthcheck_chrome(driver):
    """Verifica se o Chrome está respondendo corretamente antes de prosseguir"""
    logger.info("🏥 Executando healthcheck do Chrome...")

    try:
        # Teste 1: Verificar se consegue obter URL atual
        current_url = driver.current_url
        logger.info(f"✅ Chrome responde - URL: {current_url}")

        # Teste 2: Verificar se consegue executar JavaScript
        test_result = driver.execute_script("return 'OK';")
        if test_result == "OK":
            logger.info("✅ JavaScript executando corretamente")
        else:
            raise Exception("JavaScript não retornou valor esperado")

        # Teste 3: Navegar para uma página simples e verificar
        driver.get("about:blank")
        if driver.current_url == "about:blank":
            logger.info("✅ Navegação funcionando corretamente")
        else:
            raise Exception("Navegação não funcionou como esperado")

        logger.info("✅ Healthcheck do Chrome: PASSOU")
        return True

    except Exception as e:
        logger.error(f"❌ Healthcheck do Chrome: FALHOU - {e}")
        raise Exception(f"Chrome não está respondendo corretamente: {e}")


@safe_operation
def login_ecomhub(driver):
    """Faz login no EcomHub - versão refatorada"""
    logger.info("🔑 Iniciando login no EcomHub...")

    start_time = time.time()

    # Healthcheck do Chrome antes de prosseguir
    healthcheck_chrome(driver)

    # Limpar estado do driver para evitar interferência
    clean_driver_state(driver)

    # Navegar para a página de login
    driver.get(ECOMHUB_URL)
    logger.info(f"⏱️ Navegação para login: {time.time() - start_time:.2f}s")

    # Aguardar página carregar
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    logger.info(f"🔗 URL atual: {driver.current_url}")

    # Verificar se há erros 500 na página
    try:
        console_logs = driver.get_log('browser')
        error_500_count = sum(1 for log in console_logs if '500' in log.get('message', ''))
        if error_500_count > 2:
            logger.error(f"⚠️ Detectados {error_500_count} erros 500 na página do EcomHub")
            raise Exception(f"EcomHub retornando erro 500 - servidor com problemas ({error_500_count} erros)")
    except Exception as e:
        if "500" in str(e):
            raise e
        # Ignorar outros erros de log
        pass

    # Verificar se já está logado
    if "/login" not in driver.current_url:
        logger.info("✅ Já está logado (redirecionamento automático)")
        return get_auth_token(driver)

    # Preencher formulário de login
    try:
        # Esperar campo de email
        email_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], #email"))
        )
        email_field.clear()
        time.sleep(0.5)
        email_field.send_keys(LOGIN_EMAIL)
        logger.info("✅ Email preenchido")

        # Campo de senha
        password_field = driver.find_element(
            By.CSS_SELECTOR,
            "input[type='password'], input[name='password'], #password"
        )
        password_field.clear()
        time.sleep(0.5)
        password_field.send_keys(LOGIN_PASSWORD)
        logger.info("✅ Senha preenchida")

        # Clicar no botão de login
        login_button = driver.find_element(
            By.CSS_SELECTOR,
            "button[type='submit'], button.btn-primary, button:has-text('Entrar'), button:has-text('Login')"
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", login_button)
        time.sleep(1)
        login_button.click()
        logger.info("🔄 Botão de login clicado")

        # Aguardar redirecionamento após login
        time.sleep(3)

        # Verificar se houve erro 500 após login
        try:
            console_logs = driver.get_log('browser')
            error_500_count = sum(1 for log in console_logs if '500' in log.get('message', ''))
            if error_500_count > 0:
                logger.error(f"⚠️ Detectados {error_500_count} erros 500 após login")
                # Não falhar imediatamente, pode ser temporário
        except:
            pass

        # Aguardar sair da página de login
        WebDriverWait(driver, 20).until(
            lambda d: "/login" not in d.current_url
        )
        logger.info(f"✅ Login realizado - Redirecionado para: {driver.current_url}")

        # Extrair token de autenticação
        auth_token = get_auth_token(driver)
        logger.info(f"🎫 Token extraído: {auth_token[:20]}..." if auth_token else "❌ Token não encontrado")

        return auth_token

    except Exception as e:
        logger.error(f"❌ Erro durante login: {e}")

        # Capturar informações de debug
        try:
            logger.error(f"🔗 URL atual: {driver.current_url}")

            # Tentar capturar screenshot para debug
            screenshot_path = f"login_error_{int(time.time())}.png"
            driver.save_screenshot(screenshot_path)
            logger.info(f"📸 Screenshot salvo: {screenshot_path}")
        except Exception as debug_error:
            logger.error(f"❌ Erro ao capturar debug info: {debug_error}")

        raise Exception(f"Falha no login: {e}")


def get_auth_token(driver) -> str:
    """Extrai o token de autenticação do localStorage ou cookies"""
    try:
        # Tentar extrair do localStorage
        token = driver.execute_script("""
            return localStorage.getItem('authToken') ||
                   localStorage.getItem('token') ||
                   localStorage.getItem('access_token') ||
                   sessionStorage.getItem('authToken') ||
                   sessionStorage.getItem('token');
        """)

        if token:
            logger.info("✅ Token encontrado no storage")
            return token

        # Tentar extrair de cookies
        cookies = driver.get_cookies()
        for cookie in cookies:
            if 'token' in cookie['name'].lower() or 'auth' in cookie['name'].lower():
                logger.info(f"✅ Token encontrado em cookie: {cookie['name']}")
                return cookie['value']

        logger.warning("⚠️ Token não encontrado no storage ou cookies")
        return None

    except Exception as e:
        logger.error(f"❌ Erro ao extrair token: {e}")
        return None


def extract_via_api(driver, data_inicio, data_fim, pais_id):
    """Extrai dados via API usando cookies de autenticação"""
    logger.info(f"📊 Extraindo dados via API: {data_inicio} a {data_fim}, País: {pais_id}")

    try:
        # Obter todos os cookies do Selenium
        selenium_cookies = driver.get_cookies()

        # Converter cookies para formato de requests
        cookies_dict = {cookie['name']: cookie['value'] for cookie in selenium_cookies}

        # Headers baseados na sessão real
        headers = {
            'Accept': 'application/json',
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'Origin': 'https://app.ecomhub.app',
            'Referer': 'https://app.ecomhub.app/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # Adicionar token se disponível
        auth_token = get_auth_token(driver)
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'

        # Processar países (todos ou individual)
        paises_a_processar = TODOS_PAISES_IDS if pais_id == "todos" else [pais_id]
        all_orders = []

        for country_id in paises_a_processar:
            # URL da API com filtros
            api_url = f"{API_BASE_URL}/orders"

            # Parâmetros da requisição
            params = {
                'date_from': data_inicio,
                'date_to': data_fim,
                'country_id': country_id,
                'page': 1,
                'per_page': 100,
                'include': 'ordersItems.productsVariants.products,carrier'
            }

            page = 1
            while True:
                params['page'] = page
                logger.info(f"📄 Buscando página {page} para país {country_id}")

                response = requests.get(
                    api_url,
                    params=params,
                    headers=headers,
                    cookies=cookies_dict,
                    timeout=30
                )

                if response.status_code == 500:
                    logger.error(f"❌ Erro 500 do servidor EcomHub para país {country_id}")
                    logger.error(f"Resposta: {response.text[:500]}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"EcomHub retornou erro 500 - servidor com problemas"
                    )

                if response.status_code != 200:
                    logger.error(f"❌ API retornou status {response.status_code}: {response.text}")
                    raise Exception(f"Erro na API: {response.status_code}")

                data = response.json()
                orders = data.get('data', [])

                # Adicionar país a cada pedido se processando "todos"
                if pais_id == "todos":
                    for order in orders:
                        order['country_name'] = PAISES_MAP.get(country_id, f"País {country_id}")

                all_orders.extend(orders)

                # Verificar se há mais páginas
                if not data.get('next_page_url'):
                    break

                page += 1
                time.sleep(0.5)  # Pequena pausa entre páginas

        logger.info(f"✅ Total de pedidos extraídos: {len(all_orders)}")
        return all_orders

    except Exception as e:
        logger.error(f"❌ Erro ao extrair via API: {e}")
        raise


def process_effectiveness_data(orders_data, incluir_pais=False):
    """Processa dados de efetividade (visualização total - todos os status)"""
    effectiveness_data = defaultdict(lambda: defaultdict(lambda: {"quantidade": 0, "pais": ""}))

    for order in orders_data:
        # Extrair informações necessárias
        product_names = []
        for item in order.get('ordersItems', []):
            if 'productsVariants' in item and item['productsVariants']:
                variant = item['productsVariants']
                if 'products' in variant and variant['products']:
                    product = variant['products']
                    product_names.append(product.get('name', 'Produto sem nome'))

        # Status do pedido
        status = order.get('shippingStatus', 'unknown')

        # País do pedido (se aplicável)
        pais = order.get('country_name', '')

        # Agregar por produto
        for product_name in product_names:
            effectiveness_data[product_name][status]["quantidade"] += 1
            if incluir_pais and pais:
                effectiveness_data[product_name][status]["pais"] = pais

    # Converter para lista
    result = []
    for product_name, statuses in effectiveness_data.items():
        product_row = {
            "produto": product_name,
            "total": sum(s["quantidade"] for s in statuses.values())
        }

        # Adicionar cada status como coluna
        for status, data in statuses.items():
            product_row[status] = data["quantidade"]
            if incluir_pais and data.get("pais"):
                product_row["pais"] = data["pais"]

        # Calcular efetividade
        delivered = statuses.get("delivered", {}).get("quantidade", 0)
        total = product_row["total"]
        product_row["efetividade"] = f"{(delivered/total*100):.1f}%" if total > 0 else "0%"

        result.append(product_row)

    # Estatísticas
    stats = {
        "total_registros": len(orders_data),
        "total_produtos": len(result),
        "produtos_unicos": len(set(o.get('ordersItems', [{}])[0].get('productsVariants', {}).get('products', {}).get('name', '')
                                 for o in orders_data if o.get('ordersItems')))
    }

    return result, stats


def process_effectiveness_optimized(orders_data, incluir_pais=False):
    """Processa dados de efetividade (visualização otimizada - status agrupados)"""

    # Mapeamento de status para categorias
    STATUS_GROUPS = {
        "delivered": "Finalizados",
        "in_transit": "Transito",
        "pending": "Transito",
        "available_for_pickup": "Transito",
        "alert": "Problemas",
        "incident": "Problemas",
        "return_to_sender": "Problemas",
        "expired": "Problemas",
        "cancelled": "Problemas",
        "unknown": "Outros"
    }

    effectiveness_data = defaultdict(lambda: defaultdict(lambda: {"quantidade": 0, "pais": ""}))

    for order in orders_data:
        # Extrair informações
        product_names = []
        for item in order.get('ordersItems', []):
            if 'productsVariants' in item and item['productsVariants']:
                variant = item['productsVariants']
                if 'products' in variant and variant['products']:
                    product = variant['products']
                    product_names.append(product.get('name', 'Produto sem nome'))

        # Mapear status para grupo
        status_original = order.get('shippingStatus', 'unknown')
        status_group = STATUS_GROUPS.get(status_original, "Outros")

        # País do pedido (se aplicável)
        pais = order.get('country_name', '')

        # Agregar por produto
        for product_name in product_names:
            effectiveness_data[product_name][status_group]["quantidade"] += 1
            if incluir_pais and pais:
                effectiveness_data[product_name][status_group]["pais"] = pais

    # Converter para lista
    result = []
    for product_name, groups in effectiveness_data.items():
        product_row = {
            "produto": product_name,
            "Finalizados": groups.get("Finalizados", {}).get("quantidade", 0),
            "Transito": groups.get("Transito", {}).get("quantidade", 0),
            "Problemas": groups.get("Problemas", {}).get("quantidade", 0),
            "Outros": groups.get("Outros", {}).get("quantidade", 0)
        }

        # Total e efetividade
        product_row["total"] = sum([
            product_row["Finalizados"],
            product_row["Transito"],
            product_row["Problemas"],
            product_row["Outros"]
        ])

        if product_row["total"] > 0:
            product_row["efetividade"] = f"{(product_row['Finalizados']/product_row['total']*100):.1f}%"
        else:
            product_row["efetividade"] = "0%"

        # Adicionar país se aplicável
        if incluir_pais:
            for group_name, group_data in groups.items():
                if group_data.get("pais"):
                    product_row["pais"] = group_data["pais"]
                    break

        result.append(product_row)

    # Estatísticas
    stats = {
        "total_registros": len(orders_data),
        "total_produtos": len(result),
        "total_finalizados": sum(r["Finalizados"] for r in result),
        "total_transito": sum(r["Transito"] for r in result),
        "total_problemas": sum(r["Problemas"] for r in result)
    }

    return result, stats


@app.post("/api/processar-ecomhub/", response_model=ProcessResponse)
@apply_rate_limit("5/minute")
async def processar_ecomhub(
    request_body: ProcessRequest,
    request: Request
):
    """
    Endpoint principal refatorado - usa ChromeDriverManager
    """
    logger.warning("⚠️ [SEM AUTENTICAÇÃO TEMPORARIAMENTE] /api/processar-ecomhub/")
    logger.info(f"📋 Processamento: {request_body.data_inicio} - {request_body.data_fim}, País: {request_body.pais_id}")

    # Validação
    if request_body.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")

    # Verificar estado dos drivers antes de iniciar
    stats = get_driver_stats()
    logger.info(f"📊 Drivers ativos antes: {stats['active_count']}")

    # Limpar drivers órfãos se houver muitos
    if stats['active_count'] > 3:
        logger.warning(f"⚠️ Muitos drivers ativos ({stats['active_count']}), limpando órfãos...")
        DriverMonitor.cleanup_orphaned_drivers(max_age_seconds=120)

    try:
        headless = os.getenv("ENVIRONMENT") != "local"

        # Usar context manager para garantir limpeza
        with get_chrome_driver(headless=headless) as driver:
            logger.info(f"🚗 Driver criado com sucesso")

            # Fazer login
            login_ecomhub(driver)

            # Extrair dados via API
            orders_data = extract_via_api(
                driver,
                request_body.data_inicio,
                request_body.data_fim,
                request_body.pais_id
            )

            if not orders_data:
                return ProcessResponse(
                    status="success",
                    dados_processados={"visualizacao_total": [], "visualizacao_otimizada": []},
                    estatisticas={"total_registros": 0, "total_produtos": 0},
                    message="Nenhum pedido encontrado"
                )

            # Processar dados
            incluir_pais = True  # Sempre incluir país
            processed_data_total, stats_total = process_effectiveness_data(orders_data, incluir_pais)
            processed_data_otimizada, stats_otimizada = process_effectiveness_optimized(orders_data, incluir_pais)

            # Estrutura da resposta
            response_data = {
                "visualizacao_total": processed_data_total,
                "visualizacao_otimizada": processed_data_otimizada,
                "stats_total": stats_total,
                "stats_otimizada": stats_otimizada
            }

            logger.info(f"✅ Processamento concluído: {stats_total['total_registros']} registros")

            # Forçar garbage collection após processamento
            gc.collect()

            return ProcessResponse(
                status="success",
                dados_processados=response_data,
                estatisticas=stats_total,
                message=f"Processados {stats_total['total_registros']} pedidos de {PAISES_MAP[request_body.pais_id]}"
            )
        # Driver é automaticamente fechado aqui pelo context manager

    except Exception as e:
        logger.error(f"❌ Erro no processamento: {e}")

        # Verificar estado dos drivers após erro
        stats = get_driver_stats()
        logger.info(f"📊 Drivers ativos após erro: {stats['active_count']}")

        raise HTTPException(status_code=500, detail=f"Erro na automação: {str(e)}")

    finally:
        # Verificar estado final dos drivers
        stats = get_driver_stats()
        logger.info(f"📊 Drivers ativos no finally: {stats['active_count']}")


@app.get("/api/driver-stats")
async def driver_stats():
    """Endpoint para monitorar estado dos drivers"""
    stats = get_driver_stats()
    return {
        "status": "ok",
        "drivers": stats
    }


@app.post("/api/cleanup")
async def cleanup_drivers(api_key: str = Depends(verify_api_key)):
    """
    Endpoint administrativo para forçar limpeza de todos os drivers
    Requer autenticação
    """
    logger.warning("🧹 Limpeza forçada requisitada via API")

    stats_before = get_driver_stats()
    cleanup_all_drivers()
    stats_after = get_driver_stats()

    # Forçar garbage collection múltiplas vezes
    for _ in range(3):
        gc.collect()
        time.sleep(0.5)

    return {
        "status": "success",
        "message": "Limpeza completa executada",
        "drivers_before": stats_before['active_count'],
        "drivers_after": stats_after['active_count']
    }


@app.get("/health")
async def health_check():
    """Health check endpoint - sem autenticação"""
    try:
        stats = get_driver_stats()

        # Verificar se há muitos drivers ativos
        health_status = "healthy"
        if stats['active_count'] > 3:
            health_status = "warning"
        if stats['active_count'] > 5:
            health_status = "critical"

        # Verificar memória se disponível
        memory_status = "unknown"
        if 'memory' in stats:
            if stats['memory']['used_percent'] < 70:
                memory_status = "healthy"
            elif stats['memory']['used_percent'] < 85:
                memory_status = "warning"
            else:
                memory_status = "critical"

        return {
            "status": health_status,
            "timestamp": datetime.utcnow().isoformat(),
            "drivers": {
                "active": stats['active_count'],
                "status": health_status
            },
            "memory": {
                "status": memory_status,
                "used_percent": stats.get('memory', {}).get('used_percent', -1)
            }
        }
    except Exception as e:
        logger.error(f"❌ Erro no health check: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.on_event("startup")
async def startup_event():
    """Executado ao iniciar a aplicação"""
    logger.info("🚀 Aplicação iniciada - Versão refatorada com ChromeDriverManager")

    # Limpar qualquer driver órfão de execuções anteriores
    cleanup_all_drivers()

    logger.info("✅ Startup completo")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado ao encerrar a aplicação"""
    logger.info("🛑 Encerrando aplicação...")

    # Garantir que todos os drivers sejam fechados
    cleanup_all_drivers()

    logger.info("✅ Shutdown completo")


@app.get("/")
async def root():
    """Página inicial com informações da API"""
    html = """
    <html>
        <head>
            <title>EcomHub API - Refactored</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f5f5f5;
                }
                h1 { color: #333; }
                .endpoint {
                    background: white;
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 5px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .method {
                    font-weight: bold;
                    color: #fff;
                    padding: 3px 8px;
                    border-radius: 3px;
                    margin-right: 10px;
                }
                .post { background-color: #49cc90; }
                .get { background-color: #61affe; }
                code {
                    background: #f4f4f4;
                    padding: 2px 5px;
                    border-radius: 3px;
                }
                .warning {
                    background-color: #fff3cd;
                    border-left: 5px solid #ffc107;
                    padding: 10px;
                    margin: 20px 0;
                }
                .success {
                    background-color: #d4edda;
                    border-left: 5px solid #28a745;
                    padding: 10px;
                    margin: 20px 0;
                }
            </style>
        </head>
        <body>
            <h1>🚀 EcomHub API - Versão Refatorada</h1>

            <div class="success">
                <strong>✅ Versão 2.0.0</strong><br>
                Sistema refatorado com gerenciamento robusto de drivers
            </div>

            <h2>Endpoints Disponíveis</h2>

            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/processar-ecomhub/</strong><br>
                <p>Processa dados do EcomHub com extração via API</p>
                <p><strong>Body:</strong> <code>{"data_inicio": "YYYY-MM-DD", "data_fim": "YYYY-MM-DD", "pais_id": "164"}</code></p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/api/driver-stats</strong><br>
                <p>Monitoramento de drivers ativos e memória</p>
            </div>

            <div class="endpoint">
                <span class="method post">POST</span>
                <strong>/api/cleanup</strong><br>
                <p>Força limpeza de todos os drivers (requer autenticação)</p>
                <p><strong>Header:</strong> <code>X-API-Key: {sua-api-key}</code></p>
            </div>

            <div class="endpoint">
                <span class="method get">GET</span>
                <strong>/health</strong><br>
                <p>Health check do sistema</p>
            </div>

            <div class="warning">
                <strong>⚠️ Melhorias Implementadas:</strong><br>
                • Context manager para garantir fechamento de drivers<br>
                • Semáforo limitando 2 drivers simultâneos<br>
                • Monitoramento de drivers ativos<br>
                • Limpeza automática de drivers órfãos<br>
                • Garbage collection forçado<br>
                • Verificação de memória disponível
            </div>
        </body>
    </html>
    """
    return HTMLResponse(content=html)