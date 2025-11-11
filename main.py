# main.py - COM SUPORTE A "TODOS OS PAÍSES" + REPÚBLICA CHECA E POLÔNIA
from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security import APIKeyHeader
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time
import os
from collections import defaultdict
import logging
import requests
import urllib.parse
import json
from datetime import datetime
from typing import Dict, Optional

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
    print("⚠️ SlowAPI não instalado - Rate limiting desabilitado")

app = FastAPI(title="EcomHub Selenium Automation", version="1.0.0")

# Configurar rate limiting se disponível
if RATE_LIMITING_ENABLED:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configuração de logging
logging.basicConfig(level=logging.INFO)
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
    pais_id: str      # 164=Espanha, 41=Croácia, 66=Grécia, 82=Itália, 142=Romênia, 44=Rep.Checa, 139=Polônia, "todos"=Todos

class ProcessResponse(BaseModel):
    status: str
    dados_processados: dict
    estatisticas: dict
    message: str

# Novos modelos para tracking de status
class TrackingRequest(BaseModel):
    data_inicio: str  # YYYY-MM-DD
    data_fim: str     # YYYY-MM-DD
    pais_id: str      # ID do país ou "todos"

class TrackingResponse(BaseModel):
    status: str
    pedidos: list     # Lista com dados completos de cada pedido
    total_pedidos: int
    data_sincronizacao: str
    pais_processado: str

class AuthResponse(BaseModel):
    success: bool
    cookies: Dict[str, str]
    cookie_string: str
    headers: Dict[str, str]
    timestamp: str
    message: str
    expires_in: Optional[int] = None  # segundos até expirar
    expires_at: Optional[str] = None  # timestamp de expiração

# Configurações
ECOMHUB_URL = "https://go.ecomhub.app/login"

# IMPORTANTE: Credenciais obrigatórias via variáveis de ambiente
LOGIN_EMAIL = os.getenv("ECOMHUB_EMAIL")
LOGIN_PASSWORD = os.getenv("ECOMHUB_PASSWORD")

# Validar credenciais na inicialização
if not LOGIN_EMAIL or not LOGIN_PASSWORD:
    logger.warning("⚠️ ECOMHUB_EMAIL ou ECOMHUB_PASSWORD não configurados")
    logger.warning("A API funcionará mas endpoints que dependem do login falharão")

PAISES_MAP = {
    "164": "Espanha",
    "41": "Croácia",
    "66": "Grécia", 
    "82": "Itália",
    "142": "Romênia",
    "44": "República Checa",   # NOVO
    "139": "Polônia",          # NOVO
    "todos": "Todos os Países"
}

# IDs dos países para consulta "todos" - ATUALIZADO
TODOS_PAISES_IDS = ["164", "41", "66", "82", "142", "44", "139"]

def create_driver(headless=True):
    """Cria driver Chrome configurado - VERSÃO RAILWAY OTIMIZADA"""
    options = Options()
    
    # Para ambiente local
    if os.getenv("ENVIRONMENT") == "local":
        headless = False
        logger.info("🔧 Modo LOCAL - Browser visível")
        options.add_argument("--window-size=1366,768")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    # Para Railway (produção) - configuração otimizada para estabilidade
    logger.info("🔧 Modo PRODUÇÃO - Railway")
    
    # Configurações críticas para Railway
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # Configurações de memória e performance
    options.add_argument("--memory-pressure-off")
    options.add_argument("--max_old_space_size=4096")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    
    # Configurações de recursos
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    
    # Configurações de rede
    options.add_argument("--aggressive-cache-discard")
    options.add_argument("--disable-background-networking")
    
    # Configurações de janela
    options.add_argument("--window-size=1366,768")
    options.add_argument("--start-maximized")
    
    # Localização do Chrome
    options.binary_location = "/usr/bin/google-chrome"
    
    # Configurações adicionais para estabilidade
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Configurações de log
    options.add_argument("--log-level=3")  # Fatal only
    options.add_argument("--silent")

    # Flags de estabilidade para containers (Railway)
    options.add_argument("--disable-dev-shm-usage")  # Crucial para evitar crashes em containers
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-setuid-sandbox")

    try:
        driver = webdriver.Chrome(options=options)
        logger.info("✅ ChromeDriver criado para Railway")

        # Configurações de timeout AUMENTADAS para evitar falhas
        driver.implicitly_wait(20)
        driver.set_page_load_timeout(90)  # Aumentado de 45 para 90
        driver.set_script_timeout(60)     # Aumentado de 30 para 60
        
        # Adicionar user agent para parecer mais natural
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar driver Railway: {e}")
        raise HTTPException(status_code=500, detail=f"Erro Chrome Railway: {str(e)}")

def retry_with_backoff(func, max_retries=3, backoff_factor=2):
    """Executa função com retry e backoff exponencial"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            wait_time = backoff_factor ** attempt
            logger.warning(f"❌ Tentativa {attempt + 1} falhou: {e}")
            logger.info(f"⏳ Aguardando {wait_time}s antes da próxima tentativa...")
            time.sleep(wait_time)

def login_ecomhub(driver):
    """Faz login no EcomHub com retry automático"""
    logger.info("Fazendo login no EcomHub...")
    
    def _do_login():
        # Verificar se o driver ainda está ativo
        try:
            driver.current_url
        except Exception:
            raise Exception("Driver perdeu conexão - sessão inválida")
        
        driver.get(ECOMHUB_URL)
        
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        time.sleep(3)
        
        # Verificar se já está logado
        if "login" not in driver.current_url.lower():
            logger.info("✅ Já logado - redirecionando...")
            return True
        
        email_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "input-email"))
        )
        email_field.clear()
        email_field.send_keys(LOGIN_EMAIL)
        logger.info("✅ Email preenchido")
        
        password_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "input-password"))
        )
        password_field.clear()
        password_field.send_keys(LOGIN_PASSWORD)
        logger.info("✅ Senha preenchida")
        
        time.sleep(2)
        
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[role='button'].btn.tone-default"))
        )
        
        driver.execute_script("arguments[0].scrollIntoView();", login_button)
        time.sleep(1)
        
        login_button.click()
        logger.info("✅ Botão de login clicado")
        
        # Aguardar redirecionamento com timeout maior
        WebDriverWait(driver, 30).until(
            lambda d: "login" not in d.current_url.lower() or 
                     len(d.find_elements(By.ID, "input-email")) == 0
        )
        
        logger.info("✅ Login realizado com sucesso!")
        logger.info(f"🔗 URL atual: {driver.current_url}")
        return True
    
    try:
        return retry_with_backoff(_do_login, max_retries=3)
        
    except Exception as e:
        logger.error(f"❌ Erro no login após tentativas: {e}")
        logger.error(f"🔗 URL atual: {driver.current_url}")
        
        try:
            driver.save_screenshot("login_error.png")
            logger.info("📸 Screenshot salvo: login_error.png")
        except:
            pass
            
        raise e

def get_auth_cookies(driver):
    """Obter cookies de autenticação após login"""
    cookies = driver.get_cookies()
    session_cookies = {}
    
    for cookie in cookies:
        session_cookies[cookie['name']] = cookie['value']
    
    logger.info(f"✅ Cookies obtidos: {list(session_cookies.keys())}")
    return session_cookies

def extract_via_api(driver, data_inicio, data_fim, pais_id):
    """Extrai dados via API direta do EcomHub - COM SUPORTE A TODOS OS PAÍSES + NOVOS PAÍSES"""
    logger.info("🚀 Extraindo via API direta...")
    
    # Verificar se o driver ainda está ativo antes de prosseguir
    try:
        driver.current_url
        logger.info("✅ Driver ativo - prosseguindo com extração")
    except Exception as e:
        logger.error(f"❌ Driver inativo: {e}")
        raise Exception("Sessão do Chrome perdida durante extração")
    
    # Obter cookies após login
    cookies = get_auth_cookies(driver)
    
    # LÓGICA MODIFICADA: Se pais_id for "todos", usar todos os países (incluindo novos)
    if pais_id == "todos":
        logger.info("🌍 Processando TODOS OS PAÍSES (incluindo República Checa e Polônia)")
        paises_ids = [int(pid) for pid in TODOS_PAISES_IDS]  # [164, 41, 66, 82, 142, 44, 139]
    else:
        logger.info(f"🌍 Processando país específico: {PAISES_MAP.get(pais_id, pais_id)}")
        paises_ids = [int(pais_id)]
    
    conditions = {
        "orders": {
            "date": {
                "start": data_inicio,
                "end": data_fim
            },
            "shippingCountry_id": paises_ids  # ARRAY de países
        }
    }
    
    api_url = "https://api.ecomhub.app/api/orders"
    
    headers = {
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://go.ecomhub.app",
        "Referer": "https://go.ecomhub.app/",
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "X-Requested-With": "XMLHttpRequest"
    }
    
    logger.info(f"🔍 Conditions: {json.dumps(conditions)}")
    
    all_orders = []
    page = 0
    
    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)
    
    while True:
        params = {
            "offset": page,
            "orderBy": "null",
            "orderDirection": "null", 
            "conditions": json.dumps(conditions),
            "search": ""
        }
        
        try:
            logger.info(f"📡 Página {page}...")
            
            response = session.get(api_url, params=params, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"❌ Erro {response.status_code}")
                break
            
            orders = response.json()
            logger.info(f"✅ Página {page}: {len(orders)} pedidos")
            
            if not orders or len(orders) == 0:
                logger.info(f"📡 Fim na página {page}")
                break
            
            # Processar pedidos
            for order in orders:
                try:
                    produto = "Produto Desconhecido"
                    imagem_url = None
                    
                    # Extrair produto e imagem
                    orders_items = order.get("ordersItems", [])
                    if orders_items and len(orders_items) > 0:
                        first_item = orders_items[0]
                        variants = first_item.get("productsVariants", {})
                        products = variants.get("products", {})
                        produto = products.get("name", produto)
                        
                        # Obter imagem do produto
                        featured_image = products.get("featuredImage")
                        if featured_image:
                            if featured_image.startswith('/'):
                                imagem_url = f"https://api.ecomhub.app{featured_image}"
                            else:
                                imagem_url = featured_image
                    
                    # Tentar obter imagem do campo raw também
                    if not imagem_url:
                        try:
                            raw_data = json.loads(order.get('raw', '{}'))
                            line_items = raw_data.get('lineItems', [])
                            if line_items and len(line_items) > 0:
                                imagem_url = line_items[0].get('image')
                        except:
                            pass
                    
                    # CAMPO ADICIONAL: País de entrega para identificação quando "todos"
                    pais_entrega = order.get('shippingCountry', '')
                    
                    order_data = {
                        'imagem_url': imagem_url,
                        'numero_pedido': order.get('shopifyOrderNumber', ''),
                        'produto': produto,
                        'data': order.get('createdAt', ''),
                        'pais': pais_entrega,  # País de entrega
                        'preco': order.get('price', ''),
                        'status': order.get('status', ''),
                        'loja': order.get('stores', {}).get('name', ''),
                        'pais_id': order.get('shippingCountry_id', '')  # ID do país para controle
                    }
                    
                    all_orders.append(order_data)
                    
                except Exception as e:
                    logger.warning(f"Erro pedido: {e}")
                    continue
            
            page += 1
            
            if len(all_orders) > 50000:
                logger.warning("⚠️ Limite 50k atingido")
                break
                
        except Exception as e:
            logger.error(f"❌ Erro página {page}: {e}")
            break
    
    logger.info(f"✅ Total: {len(all_orders)} pedidos de {page} páginas")
    return all_orders

def extract_orders_for_tracking(driver, data_inicio, data_fim, pais_id):
    """Extrai dados COMPLETOS para tracking de status de pedidos - APENAS STATUS ATIVOS"""
    logger.info(f"🔍 Extraindo dados para tracking - {data_inicio} a {data_fim}, País: {pais_id}")
    
    # Status ativos que precisam de monitoramento (baseado nos dados reais da EcomHub)
    STATUS_ATIVOS = [
        'processing', 'shipped', 'issue', 'returning'
    ]
    
    # Status finalizados que IGNORAMOS (otimização)
    STATUS_FINALIZADOS = ['delivered', 'returned', 'cancelled', 'canceled', 'cancelado']
    
    logger.info(f"📊 Buscando apenas status ativos: {STATUS_ATIVOS}")
    
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']
    
    api_url = "https://api.ecomhub.app/api/orders"
    
    # Determinar países para processar
    if pais_id == "todos":
        paises_processar = TODOS_PAISES_IDS
        logger.info(f"🌍 Processando TODOS os países: {paises_processar}")
    else:
        paises_processar = [pais_id]
        logger.info(f"🏴 Processando país específico: {pais_id}")
    
    all_orders = []
    
    for current_pais_id in paises_processar:
        logger.info(f"🔍 Processando país {current_pais_id}...")
        
        # Filtro DIRETO na API da EcomHub - apenas status ativos
        conditions = {
            "orders": {
                "date": {
                    "start": data_inicio,
                    "end": data_fim
                },
                "shippingCountry_id": int(current_pais_id),
                "status": STATUS_ATIVOS  # FILTRO DIRETO NA API!
            }
        }
        
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Origin": "https://go.ecomhub.app",
            "Referer": "https://go.ecomhub.app/",
            "User-Agent": driver.execute_script("return navigator.userAgent;"),
            "X-Requested-With": "XMLHttpRequest"
        }
        
        session = requests.Session()
        session.headers.update(headers)
        session.cookies.update(cookies)
        
        page = 0
        while True:
            params = {
                "offset": page,
                "orderBy": "null", 
                "orderDirection": "null",
                "conditions": json.dumps(conditions),
                "search": ""
            }
            
            try:
                response = session.get(api_url, params=params, timeout=60)
                
                if response.status_code != 200:
                    logger.error(f"❌ Erro {response.status_code} para país {current_pais_id}")
                    break
                
                orders = response.json()
                logger.info(f"✅ País {current_pais_id}, Página {page}: {len(orders)} pedidos")
                
                if not orders or len(orders) == 0:
                    break
                
                # Adicionar pedidos COMPLETOS - incluindo TODOS os campos originais
                for order in orders:
                    try:
                        # Dados completos do pedido original da API
                        complete_order = {
                            # IDs e identificadores
                            "id": order.get("id"),
                            "external_id": order.get("external_id"),
                            "shopifyOrderNumber": order.get("shopifyOrderNumber"),
                            "shopifyOrderName": order.get("shopifyOrderName"),
                            
                            # Status e datas
                            "status": order.get("status"),
                            "createdAt": order.get("createdAt"),
                            "updatedAt": order.get("updatedAt"),
                            "date": order.get("date"),
                            "dateDay": order.get("dateDay"),
                            
                            # Datas específicas de status
                            "statusDateReturning": order.get("statusDateReturning"),
                            "statusDateReturned": order.get("statusDateReturned"),
                            "statusDateLost": order.get("statusDateLost"),
                            "statusDateCancelled": order.get("statusDateCancelled"),
                            "statusDateWithCourier": order.get("statusDateWithCourier"),
                            
                            # Dados do cliente
                            "customerName": order.get("customerName"),
                            "customerEmail": order.get("customerEmail"),
                            "customerPhone": order.get("customerPhone"),
                            "customerPreferences": order.get("customerPreferences"),
                            
                            # Endereços
                            "billingAddress": order.get("billingAddress"),
                            "shippingAddress": order.get("shippingAddress"),
                            "shippingPostalCode": order.get("shippingPostalCode"),
                            "shippingCity": order.get("shippingCity"),
                            "shippingProvince": order.get("shippingProvince"),
                            "shippingCountry": order.get("shippingCountry"),
                            "shippingCountry_id": order.get("shippingCountry_id"),
                            
                            # Informações financeiras
                            "price": order.get("price"),
                            "priceOriginal": order.get("priceOriginal"),
                            "currency_id": order.get("currency_id"),
                            "paymentMethod": order.get("paymentMethod"),
                            
                            # Tracking e entrega
                            "waybill": order.get("waybill"),
                            "trackingUrl": order.get("trackingUrl"),
                            "weight": order.get("weight"),
                            "volume": order.get("volume"),
                            
                            # Loja e warehouse
                            "store_id": order.get("store_id"),
                            "warehouse_id": order.get("warehouse_id"),
                            
                            # Issues e problemas
                            "issue": order.get("issue"),
                            "issueDescription": order.get("issueDescription"),
                            "issueResolution": order.get("issueResolution"),
                            "issueResolutionDetail": order.get("issueResolutionDetail"),
                            "isIssueResolutable": order.get("isIssueResolutable"),
                            
                            # Dados dos produtos (primeiro produto)
                            "produto_nome": "Produto Desconhecido",
                            "produto_sku": None,
                            "produto_preco": None,
                            
                            # Dados de relacionamentos
                            "countries": order.get("countries"),
                            "stores": order.get("stores"),
                            "warehouses": order.get("warehouses"),
                            "shippingMethods": order.get("shippingMethods"),
                            "currencies": order.get("currencies"),
                            
                            # Dados brutos
                            "raw": order.get("raw"),
                            "ordersItems": order.get("ordersItems"),
                            
                            # Flags
                            "isTest": order.get("isTest", False),
                            "origin": order.get("origin"),
                            
                            # Metadados para tracking
                            "data_extracao": data_inicio + " - " + data_fim,
                            "pais_origem_consulta": current_pais_id
                        }
                        
                        # Extrair nome do produto dos ordersItems
                        orders_items = order.get("ordersItems", [])
                        if orders_items and len(orders_items) > 0:
                            first_item = orders_items[0]
                            variants = first_item.get("productsVariants", {})
                            products = variants.get("products", {})
                            complete_order["produto_nome"] = products.get("name", "Produto Desconhecido")
                            complete_order["produto_preco"] = first_item.get("price")
                            
                            # SKU do produto
                            stock_entries = first_item.get("stockEntries", {})
                            stock_items = stock_entries.get("stockItems", {})
                            complete_order["produto_sku"] = stock_items.get("sku")
                        
                        all_orders.append(complete_order)
                        
                    except Exception as e:
                        logger.warning(f"Erro ao processar pedido para tracking: {e}")
                        continue
                
                page += 1
                
                if len(all_orders) > 50000:
                    logger.warning("⚠️ Limite 50k atingido no tracking")
                    break
                    
            except Exception as e:
                logger.error(f"❌ Erro página {page} do país {current_pais_id}: {e}")
                break
    
    logger.info(f"✅ Tracking: {len(all_orders)} pedidos ATIVOS extraídos (filtro otimizado)")
    logger.info(f"📊 Status filtrados: {STATUS_ATIVOS}")
    return all_orders

def process_effectiveness_data(orders_data, incluir_pais=False):
    """Processa dados e calcula efetividade por produto - VISUALIZAÇÃO TOTAL"""
    logger.info("Processando efetividade por produto - VISUALIZAÇÃO TOTAL...")
    
    product_counts = defaultdict(lambda: {"Total_Registros": 0, "Delivered_Count": 0, "imagem_url": None, "pais": None})
    
    # Obter status únicos
    unique_statuses = list(set([order['status'] for order in orders_data if order['status']]))
    unique_statuses = sorted([status.strip() for status in unique_statuses])
    
    # Processar cada pedido
    for order in orders_data:
        produto = order.get('produto', 'Produto Desconhecido').strip()
        if not produto:
            produto = 'Produto Desconhecido'
        
        status = order.get('status', '').strip()
        imagem_url = order.get('imagem_url')
        pais = order.get('pais', '')
        
        # CHAVE MODIFICADA: incluir país quando necessário
        if incluir_pais:
            chave_produto = f"{produto}|{pais}"  # Chave única por produto+país
        else:
            chave_produto = produto
        
        # Inicializar produto se não existe
        if chave_produto not in product_counts:
            product_counts[chave_produto] = {"Total_Registros": 0, "Delivered_Count": 0, "imagem_url": imagem_url, "pais": pais, "produto_nome": produto}
            for unique_status in unique_statuses:
                product_counts[chave_produto][unique_status] = 0
        
        # Guardar primeira imagem e país encontrados para o produto
        if imagem_url and not product_counts[chave_produto]["imagem_url"]:
            product_counts[chave_produto]["imagem_url"] = imagem_url
        if pais and not product_counts[chave_produto]["pais"]:
            product_counts[chave_produto]["pais"] = pais
        
        # Contar registros
        product_counts[chave_produto]["Total_Registros"] += 1
        
        if status in unique_statuses:
            product_counts[chave_produto][status] += 1
        
        # Contar delivered
        if status.lower() in ['entregue', 'delivered', 'finalizado']:
            product_counts[chave_produto]["Delivered_Count"] += 1
    
    # Converter para formato final
    result_data = []
    for chave_produto, counts in product_counts.items():
        total_registros = counts["Total_Registros"]
        delivered = counts["Delivered_Count"]
        
        row = {}
        
        # Adicionar coluna País se necessário (primeira coluna)
        if incluir_pais:
            row["País"] = counts["pais"]
        
        row.update({
            "Imagem": counts["imagem_url"],
            "Produto": counts.get("produto_nome", chave_produto),  # Nome limpo do produto
            "Total": total_registros,
        })
        
        # Adicionar cada status
        for status in unique_statuses:
            row[status] = counts[status]
        
        result_data.append(row)
    
    # Ordenar por total de registros
    if result_data:
        result_data.sort(key=lambda x: x["Total"], reverse=True)
        
        # Adicionar linha de totais
        totals = {}
        if incluir_pais:
            totals["País"] = "Todos"
        totals.update({"Imagem": None, "Produto": "Total"})
        
        numeric_cols = ["Total"] + unique_statuses
        for col in numeric_cols:
            totals[col] = sum(row[col] for row in result_data)
        
        result_data.append(totals)
    
    # Estatísticas
    stats = {
        'total_registros': len(orders_data),
        'total_produtos': len(product_counts),
        'produtos_com_dados': len([p for p in product_counts.values() if p["Total_Registros"] > 0]),
        'tipo_visualizacao': 'total'
    }
    
    return result_data, stats

def process_effectiveness_optimized(orders_data, incluir_pais=False):
    """Processa dados com visualização OTIMIZADA - colunas agrupadas"""
    logger.info("Processando efetividade - Visualização OTIMIZADA...")
    
    product_counts = defaultdict(lambda: {
        "Total_Registros": 0, 
        "imagem_url": None,
        "pais": None,
        "produto_nome": None,
        # Contadores por status individual
        "delivered": 0,
        "returning": 0,
        "returned": 0,
        "cancelled": 0,
        "canceled": 0,
        "cancelado": 0,
        "out_for_delivery": 0,
        "preparing_for_shipping": 0,
        "ready_to_ship": 0,
        "with_courier": 0,
        "issue": 0,
        # Outros status dinâmicos
        "outros_status": defaultdict(int)
    })
    
    # Processar cada pedido
    for order in orders_data:
        produto = order.get('produto', 'Produto Desconhecido').strip()
        if not produto:
            produto = 'Produto Desconhecido'
        
        status = order.get('status', '').strip().lower()
        imagem_url = order.get('imagem_url')
        pais = order.get('pais', '')
        
        # CHAVE MODIFICADA: incluir país quando necessário
        if incluir_pais:
            chave_produto = f"{produto}|{pais}"  # Chave única por produto+país
        else:
            chave_produto = produto
        
        # Inicializar produto se não existe
        if chave_produto not in product_counts:
            product_counts[chave_produto] = {
                "Total_Registros": 0, "imagem_url": imagem_url, "pais": pais, "produto_nome": produto,
                "delivered": 0, "returning": 0, "returned": 0,
                "cancelled": 0, "canceled": 0, "cancelado": 0,
                "out_for_delivery": 0, "preparing_for_shipping": 0, 
                "ready_to_ship": 0, "with_courier": 0, "issue": 0,
                "outros_status": defaultdict(int)
            }
        
        # Guardar primeira imagem e país
        if imagem_url and not product_counts[chave_produto]["imagem_url"]:
            product_counts[chave_produto]["imagem_url"] = imagem_url
        if pais and not product_counts[chave_produto]["pais"]:
            product_counts[chave_produto]["pais"] = pais
        
        # Contar registros
        product_counts[chave_produto]["Total_Registros"] += 1
        
        # Contar status específicos
        known_statuses = ['delivered', 'returning', 'returned', 'cancelled', 'canceled', 'cancelado',
                         'out_for_delivery', 'preparing_for_shipping', 'ready_to_ship', 'with_courier', 'issue']
        
        if status in known_statuses:
            product_counts[chave_produto][status] += 1
        else:
            product_counts[chave_produto]["outros_status"][status] += 1
    
    # Converter para formato otimizado
    result_data = []
    for chave_produto, counts in product_counts.items():
        # Colunas agrupadas
        totais = counts["Total_Registros"]
        
        finalizados = counts["delivered"] + counts["issue"] + counts["returning"] + counts["returned"] + counts["cancelled"] + counts["canceled"] + counts["cancelado"]
        
        transito = (counts["out_for_delivery"] + counts["preparing_for_shipping"] + 
                   counts["ready_to_ship"] + counts["with_courier"])
        
        problemas = counts["issue"]
        
        devolucao = counts["returning"] + counts["returned"] + counts["issue"]
        
        cancelados = counts["cancelled"] + counts["canceled"] + counts["cancelado"]
        
        entregues = counts["delivered"]
        
        # Percentuais
        pct_transito = (transito / totais * 100) if totais > 0 else 0
        pct_devolvidos = (devolucao / totais * 100) if totais > 0 else 0
        
        # Efetividade parcial
        efetividade_parcial = (entregues / finalizados * 100) if finalizados > 0 else 0
        
        # Efetividade total
        efetividade_total = (entregues / totais * 100) if totais > 0 else 0
        
        row = {}
        
        # Adicionar coluna País se necessário (primeira coluna)
        if incluir_pais:
            row["País"] = counts["pais"]
        
        row.update({
            "Imagem": counts["imagem_url"],
            "Produto": counts.get("produto_nome", chave_produto),  # Nome limpo do produto
            "Totais": totais,
            "Finalizados": finalizados,
            "Transito": transito,
            "Problemas": problemas,
            "Devolucao": devolucao,
            "Cancelados": cancelados,
            "Entregues": entregues,
            "% A Caminho": f"{pct_transito:.1f}%",
            "% Devolvidos": f"{pct_devolvidos:.1f}%",
            "Efetividade_Parcial": f"{efetividade_parcial:.1f}%",
            "Efetividade_Total": f"{efetividade_total:.1f}%"
        })
        
        result_data.append(row)
    
    # Ordenar por efetividade total
    if result_data:
        result_data.sort(key=lambda x: float(x["Efetividade_Total"].replace('%', '')), reverse=True)
        
        # Adicionar linha de totais
        totals = {}
        if incluir_pais:
            totals["País"] = "Todos"
        totals.update({"Imagem": None, "Produto": "Total"})
        
        numeric_cols = ["Totais", "Finalizados", "Transito", 
                       "Problemas", "Devolucao", "Cancelados", "Entregues"]
        
        for col in numeric_cols:
            totals[col] = sum(row[col] for row in result_data)
        
        # Calcular percentuais totais
        total_pedidos = totals["Totais"]
        total_finalizados = totals["Finalizados"]
        total_entregues = totals["Entregues"]
        
        totals["% A Caminho"] = f"{(totals['Transito'] / total_pedidos * 100):.1f}%" if total_pedidos > 0 else "0%"
        totals["% Devolvidos"] = f"{(totals['Devolucao'] / total_pedidos * 100):.1f}%" if total_pedidos > 0 else "0%"
        totals["Efetividade_Parcial"] = f"{(total_entregues / total_finalizados * 100):.1f}%" if total_finalizados > 0 else "0%"
        totals["Efetividade_Total"] = f"{(total_entregues / total_pedidos * 100):.1f}% (Média)" if total_pedidos > 0 else "0%"
        
        result_data.append(totals)
    
    # Estatísticas
    stats = {
        'total_registros': len(orders_data),
        'total_produtos': len(product_counts),
        'tipo_visualizacao': 'otimizada'
    }
    
    return result_data, stats

@app.post("/api/pedidos-status-tracking/", response_model=TrackingResponse)
@limiter.limit("10/minute") if RATE_LIMITING_ENABLED else lambda f: f
async def pedidos_status_tracking(
    request_body: TrackingRequest,
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Endpoint específico para sistema de tracking de status de pedidos"""
    
    logger.info(f"🔍 Tracking de status: {request_body.data_inicio} - {request_body.data_fim}, País: {request_body.pais_id}")

    # Validação do país
    if request_body.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")
    
    driver = None
    try:
        headless = os.getenv("ENVIRONMENT") != "local"
        driver = create_driver(headless=headless)
        
        # Fazer login
        login_ecomhub(driver)
        
        # Extrair dados completos via API
        orders_data = extract_orders_for_tracking(driver, request_body.data_inicio, request_body.data_fim, request_body.pais_id)
        
        # Preparar resposta
        from datetime import datetime
        data_sincronizacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return TrackingResponse(
            status="success",
            pedidos=orders_data,
            total_pedidos=len(orders_data),
            data_sincronizacao=data_sincronizacao,
            pais_processado=PAISES_MAP[request_body.pais_id]
        )
        
    except Exception as e:
        logger.error(f"Erro no tracking: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na extração de dados: {str(e)}")
        
    finally:
        if driver:
            driver.quit()

@app.get("/api/auth", response_model=AuthResponse)
@limiter.limit("30/minute") if RATE_LIMITING_ENABLED else lambda f: f
async def get_auth_tokens(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Retorna os tokens de autenticação armazenados no banco de dados

    Os tokens são atualizados automaticamente a cada 2 minutos pela thread de sincronização.
    Este endpoint apenas lê os tokens já disponíveis no banco, sem fazer novo login.

    Returns:
        AuthResponse com os tokens atuais ou erro se não houver tokens disponíveis
    """
    try:
        logger.info("📖 Lendo tokens do banco de dados...")

        # Importar e usar o banco de dados
        try:
            from token_sync.database import get_database
            db = get_database()
        except Exception as e:
            logger.error(f"❌ Erro ao acessar banco de dados: {e}")
            raise HTTPException(
                status_code=503,
                detail="Sistema de tokens temporariamente indisponível"
            )

        # Obter tokens do banco
        tokens_data = db.get_tokens()

        if not tokens_data:
            logger.warning("⚠️ Nenhum token disponível no banco")
            raise HTTPException(
                status_code=503,
                detail="Tokens não disponíveis. Aguarde a sincronização automática (executa a cada 2 minutos)"
            )

        # Verificar se tokens ainda são válidos
        if not tokens_data.get('is_valid', False):
            logger.warning("⚠️ Tokens expirados no banco")
            raise HTTPException(
                status_code=503,
                detail=f"Tokens expirados. Última atualização: {tokens_data.get('updated_at')}. Aguarde nova sincronização."
            )

        # Preparar cookies dict
        cookies = tokens_data.get('cookies', {})
        if not cookies:
            # Se não tiver cookies completos, montar com os tokens individuais
            cookies = {
                'token': tokens_data.get('token', ''),
                'e_token': tokens_data.get('e_token', ''),
                'refresh_token': tokens_data.get('refresh_token', '')
            }

        # Criar cookie string
        cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])

        # Headers padrão para usar com a API
        headers = {
            "Accept": "*/*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://go.ecomhub.app",
            "Referer": "https://go.ecomhub.app/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json"
        }

        logger.info(f"✅ Tokens lidos com sucesso. Expira em: {tokens_data.get('expires_in')} segundos")

        return AuthResponse(
            success=True,
            cookies=cookies,
            cookie_string=cookie_string,
            headers=headers,
            timestamp=tokens_data.get('updated_at', datetime.utcnow().isoformat()),
            expires_in=tokens_data.get('expires_in', 0),
            expires_at=tokens_data.get('expires_at', ''),
            message=f"Tokens válidos. Expira em {tokens_data.get('expires_in', 0)} segundos"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao obter tokens: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao obter tokens: {str(e)}"
        )

@app.get("/api/auth/status")
@limiter.limit("30/minute") if RATE_LIMITING_ENABLED else lambda f: f
async def get_auth_status(request: Request, api_key: str = Depends(verify_api_key)):
    """
    Retorna o status do sistema de sincronização de tokens

    Mostra informações sobre:
    - Se há tokens disponíveis
    - Última atualização
    - Tempo até expirar
    - Status da sincronização
    """
    try:
        try:
            from token_sync.database import get_database
            db = get_database()
            # Obter status do banco
            status = db.get_status()
        except Exception as e:
            logger.error(f"Erro ao acessar banco de dados: {e}")
            status = {
                'status': 'database_error',
                'has_tokens': False,
                'db_available': False,
                'error': str(e)
            }

        # Adicionar informações da thread se estiver rodando
        if os.getenv("TOKEN_SYNC_ENABLED", "false").lower() == "true":
            status['sync_enabled'] = True
            status['sync_interval'] = "2 minutos"
        else:
            status['sync_enabled'] = False
            status['message'] = "Sincronização automática desabilitada. Configure TOKEN_SYNC_ENABLED=true"

        return status

    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'has_tokens': False
        }

@app.get("/")
async def root():
    """Redireciona para documentação Swagger"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/docs")

@app.get("/api-ecomhub-docs", response_class=HTMLResponse)
async def ecomhub_api_docs():
    """Documentação completa da API EcomHub"""
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Documentação API EcomHub</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: #f5f7fa;
                padding: 20px;
                line-height: 1.6;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                border-bottom: 3px solid #3498db;
                padding-bottom: 15px;
                margin-bottom: 30px;
            }
            h2 {
                color: #34495e;
                margin-top: 40px;
                margin-bottom: 20px;
                padding-left: 10px;
                border-left: 4px solid #3498db;
            }
            h3 {
                color: #555;
                margin-top: 25px;
                margin-bottom: 15px;
            }
            .endpoint {
                background: #ecf0f1;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #27ae60;
            }
            .method {
                display: inline-block;
                background: #27ae60;
                color: white;
                padding: 5px 15px;
                border-radius: 5px;
                font-weight: bold;
                margin-right: 10px;
            }
            code {
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
                font-size: 0.9em;
            }
            pre {
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 20px;
                border-radius: 8px;
                overflow-x: auto;
                margin: 15px 0;
            }
            pre code {
                background: none;
                padding: 0;
            }
            .warning {
                background: #fff3cd;
                border-left: 4px solid #ffc107;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            .info {
                background: #d1ecf1;
                border-left: 4px solid #17a2b8;
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background: #34495e;
                color: white;
            }
            tr:hover {
                background: #f5f5f5;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #3498db;
                text-decoration: none;
                font-weight: bold;
            }
            .back-link:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <a href="/" class="back-link">← Voltar</a>

            <h1>📚 Documentação API EcomHub</h1>

            <div class="info">
                <strong>ℹ️ Importante:</strong> Esta documentação explica como usar a API da EcomHub
                DEPOIS de obter os tokens de autenticação através do endpoint <code>/api/auth</code>
                deste serviço.
            </div>

            <h2>🔗 Endpoint Principal</h2>
            <div class="endpoint">
                <span class="method">GET</span>
                <code>https://api.ecomhub.app/api/orders</code>
            </div>
            <p><strong>Descrição:</strong> Retorna lista de pedidos com filtros e paginação.</p>

            <h2>🔐 Autenticação</h2>
            <p>A API EcomHub usa autenticação baseada em cookies. Você precisa incluir os cookies obtidos do endpoint <code>/api/auth</code> nas suas requisições.</p>

            <h3>Headers Necessários</h3>
            <pre><code>Accept: */*
Accept-Language: pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7
Origin: https://go.ecomhub.app
Referer: https://go.ecomhub.app/
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
X-Requested-With: XMLHttpRequest
Content-Type: application/json
Cookie: token=...; e_token=...; refresh_token=...</code></pre>

            <h2>📋 Parâmetros da Requisição</h2>

            <table>
                <thead>
                    <tr>
                        <th>Parâmetro</th>
                        <th>Tipo</th>
                        <th>Obrigatório</th>
                        <th>Descrição</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>offset</code></td>
                        <td>integer</td>
                        <td>Sim</td>
                        <td><strong>Paginação:</strong> Qual página buscar. Use 0 para primeira página, 1 para segunda, etc. Cada página retorna até 48 pedidos.</td>
                    </tr>
                    <tr>
                        <td><code>orderBy</code></td>
                        <td>string</td>
                        <td>Sim</td>
                        <td><strong>Ordenação:</strong> Campo para ordenar (ex: "date", "price"). Use <code>"null"</code> (string) para ordem padrão da EcomHub.</td>
                    </tr>
                    <tr>
                        <td><code>orderDirection</code></td>
                        <td>string</td>
                        <td>Sim</td>
                        <td><strong>Direção:</strong> "asc" (crescente) ou "desc" (decrescente). Use <code>"null"</code> (string) para padrão.</td>
                    </tr>
                    <tr>
                        <td><code>conditions</code></td>
                        <td>JSON string</td>
                        <td>Sim</td>
                        <td><strong>Filtros:</strong> JSON stringificado com filtros de data e país. Veja estrutura abaixo.</td>
                    </tr>
                    <tr>
                        <td><code>search</code></td>
                        <td>string</td>
                        <td>Não</td>
                        <td><strong>Busca:</strong> Termo para buscar nos pedidos (número do pedido, nome do cliente, etc). Deixe vazio <code>""</code> se não usar.</td>
                    </tr>
                </tbody>
            </table>

            <div class="info" style="margin-top: 20px;">
                <strong>💡 Dica:</strong> Para uso básico, sempre use:
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li><code>offset</code> = 0 (primeira página)</li>
                    <li><code>orderBy</code> = "null" (ordem padrão)</li>
                    <li><code>orderDirection</code> = "null" (ordem padrão)</li>
                    <li><code>search</code> = "" (sem busca)</li>
                    <li><code>conditions</code> = defina apenas data e país</li>
                </ul>
            </div>

            <h3>Estrutura do <code>conditions</code></h3>
            <p>O parâmetro <code>conditions</code> é um <strong>JSON convertido em string</strong> que define os filtros da busca:</p>

            <pre><code>{
  "orders": {
    "date": {
      "start": "2025-08-01",   // Data início (formato YYYY-MM-DD)
      "end": "2025-08-20"      // Data fim (formato YYYY-MM-DD)
    },
    "shippingCountry_id": [164, 41, 66]  // Array com IDs dos países
  }
}</code></pre>

            <div class="info" style="margin-top: 15px;">
                <strong>⚠️ Importante:</strong>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>O <code>conditions</code> deve ser uma <strong>string</strong>, não um objeto JSON direto</li>
                    <li>No n8n, use aspas duplas dentro do JSON: <code>{"orders":{"date":{...}}}</code></li>
                    <li>O período de datas inclui ambos os dias (início e fim)</li>
                    <li>Você pode filtrar por um país <code>[164]</code> ou vários <code>[164, 82, 66]</code></li>
                </ul>
            </div>

            <h4 style="margin-top: 25px;">Exemplo no n8n:</h4>
            <p>No campo <strong>Query Parameters</strong> do nó HTTP Request:</p>
            <pre><code>conditions: {"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164]}}</code></pre>

            <h3>IDs de Países Suportados</h3>
            <table>
                <thead>
                    <tr>
                        <th>País</th>
                        <th>ID</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>🇪🇸 Espanha</td><td>164</td></tr>
                    <tr><td>🇭🇷 Croácia</td><td>41</td></tr>
                    <tr><td>🇬🇷 Grécia</td><td>66</td></tr>
                    <tr><td>🇮🇹 Itália</td><td>82</td></tr>
                    <tr><td>🇷🇴 Romênia</td><td>142</td></tr>
                    <tr><td>🇨🇿 República Tcheca</td><td>44</td></tr>
                    <tr><td>🇵🇱 Polônia</td><td>139</td></tr>
                </tbody>
            </table>

            <h2>📄 Estrutura da Resposta</h2>
            <p>A API retorna um array JSON com até <strong>48 pedidos</strong> por página.</p>

            <h3>Campos Principais</h3>
            <pre><code>[
  {
    "id": 12345,
    "shopifyOrderName": "#1041",
    "status": "delivered",
    "date": "2025-08-01T10:00:00Z",
    "price": "29.99",
    "revenueReleaseDate": "2025-08-15",
    "revenueReleaseWindow": 7,

    "customerName": "João Silva",
    "customerEmail": "joao@example.com",
    "shippingCountry": "Portugal",
    "shippingCountry_id": 164,

    "currencies": {
      "code": "EUR"
    },

    "ordersItems": [
      {
        "productsVariants": {
          "products": {
            "name": "Nome do Produto",
            "featuredImage": "/path/to/image.jpg"
          }
        }
      }
    ]
  }
]</code></pre>

            <h3>Campos Financeiros Importantes</h3>
            <table>
                <thead>
                    <tr>
                        <th>Campo</th>
                        <th>Descrição</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><code>price</code></td>
                        <td>Valor do pedido</td>
                    </tr>
                    <tr>
                        <td><code>revenueReleaseDate</code></td>
                        <td>Data prevista de liberação do pagamento</td>
                    </tr>
                    <tr>
                        <td><code>revenueReleaseWindow</code></td>
                        <td>Janela de liberação em dias (2, 4 ou 7 dias)</td>
                    </tr>
                    <tr>
                        <td><code>currencies.code</code></td>
                        <td>Código da moeda (RON, CZK, EUR, PLN)</td>
                    </tr>
                </tbody>
            </table>

            <h3>Status de Pedidos</h3>
            <ul style="margin-left: 30px; margin-top: 10px;">
                <li><code>delivered</code> - Entregue</li>
                <li><code>out_for_delivery</code> - Em entrega</li>
                <li><code>returning</code> - Em devolução</li>
                <li><code>returned</code> - Devolvido</li>
                <li><code>pending</code> - Pendente</li>
                <li><code>cancelled</code> - Cancelado</li>
            </ul>

            <h2>🔄 Paginação - Como Buscar Todos os Pedidos</h2>

            <p>A API EcomHub retorna no <strong>máximo 48 pedidos por requisição</strong>. Para buscar todos os pedidos de um período, você precisa fazer múltiplas requisições.</p>

            <div class="info">
                <p><strong>📝 Passo a passo:</strong></p>
                <ol style="margin-left: 20px; margin-top: 10px; line-height: 1.8;">
                    <li>Faça a primeira requisição com <code>offset=0</code></li>
                    <li>Se receber 48 pedidos, há mais dados. Faça nova requisição com <code>offset=1</code></li>
                    <li>Continue incrementando o offset (2, 3, 4...) até a API retornar:
                        <ul style="margin-left: 20px;">
                            <li>Array vazio <code>[]</code>, ou</li>
                            <li>Menos de 48 pedidos (significa que é a última página)</li>
                        </ul>
                    </li>
                </ol>
            </div>

            <h3>Exemplo Visual:</h3>
            <pre><code>Requisição 1: offset=0 → Retorna 48 pedidos → Continuar
Requisição 2: offset=1 → Retorna 48 pedidos → Continuar
Requisição 3: offset=2 → Retorna 35 pedidos → Última página (menos de 48)
Total: 131 pedidos</code></pre>

            <div class="warning">
                <strong>⚠️ Dica:</strong> No n8n, use um loop para buscar automaticamente todas as páginas até receber array vazio.
            </div>

            <h2>💻 Exemplo Prático (n8n)</h2>

            <h3>1. Obter Autenticação</h3>
            <p>Faça um POST para <code>/api/auth</code> para obter cookies</p>

            <h3>2. Buscar Pedidos de Agosto na Espanha</h3>
            <pre><code>GET https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions={"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164]}}&search=</code></pre>

            <h3>3. Múltiplos Países</h3>
            <pre><code>GET https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions={"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164,82,66]}}&search=</code></pre>

            <h2>⚠️ Avisos Importantes</h2>
            <div class="warning">
                <ul style="margin-left: 20px;">
                    <li><strong>Tokens expiram:</strong> Os tokens de autenticação podem expirar. Se receber erro 401, obtenha novos tokens.</li>
                    <li><strong>Rate limiting:</strong> Não faça requisições muito rápidas. Adicione delays entre chamadas.</li>
                    <li><strong>Limite de dados:</strong> Para grandes volumes, implemente controle de paginação adequado.</li>
                    <li><strong>Formato de data:</strong> Sempre use formato YYYY-MM-DD para datas.</li>
                </ul>
            </div>

            <h2>📞 Suporte</h2>
            <p>Para dúvidas sobre autenticação, consulte a <a href="/docs">documentação da API de Auth</a>.</p>

            <div style="margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; text-align: center; color: #7f8c8d;">
                <p>Documentação atualizada em Novembro 2025</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

def safe_driver_operation(driver_func):
    """Decorator para operações seguras com retry em caso de falha de sessão"""
    def wrapper(*args, **kwargs):
        max_retries = 2
        for attempt in range(max_retries):
            try:
                return driver_func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["session", "disconnected", "chrome", "invalid"]):
                    if attempt < max_retries - 1:
                        logger.warning(f"🔄 Tentativa {attempt + 1} - Erro de sessão detectado: {e}")
                        time.sleep(3)
                        continue
                raise e
        return None
    return wrapper

@app.post("/api/processar-ecomhub/", response_model=ProcessResponse)
@limiter.limit("5/minute") if RATE_LIMITING_ENABLED else lambda f: f
async def processar_ecomhub(
    request_body: ProcessRequest,
    request: Request,
    api_key: str = Depends(verify_api_key)
):
    """Endpoint principal - COM SUPORTE A TODOS OS PAÍSES + NOVOS PAÍSES"""

    logger.info(f"Processamento: {request_body.data_inicio} - {request_body.data_fim}, País: {request_body.pais_id}")
    
    # VALIDAÇÃO MODIFICADA: Aceitar "todos" ou países específicos (incluindo novos)
    if request_body.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")
    
    driver = None
    try:
        headless = os.getenv("ENVIRONMENT") != "local"
        
        @safe_driver_operation
        def _create_and_process():
            nonlocal driver
            driver = create_driver(headless=headless)
            
            # Fazer login com retry
            login_ecomhub(driver)
            
            # Extrair dados via API direta
            return extract_via_api(driver, request_body.data_inicio, request_body.data_fim, request_body.pais_id)
        
        orders_data = _create_and_process()
        
        if not orders_data:
            return ProcessResponse(
                status="success",
                dados_processados={"visualizacao_total": [], "visualizacao_otimizada": []},
                estatisticas={"total_registros": 0, "total_produtos": 0},
                message="Nenhum pedido encontrado"
            )
        
        # SEMPRE INCLUIR COLUNA PAÍS
        incluir_pais = True
        logger.info(f"Incluir coluna País: {incluir_pais}")
        
        # Retornar ambas as visualizações
        processed_data_total, stats_total = process_effectiveness_data(orders_data, incluir_pais)
        processed_data_otimizada, stats_otimizada = process_effectiveness_optimized(orders_data, incluir_pais)
        
        # Estrutura da resposta com ambos os tipos
        response_data = {
            "visualizacao_total": processed_data_total,
            "visualizacao_otimizada": processed_data_otimizada,
            "stats_total": stats_total,
            "stats_otimizada": stats_otimizada
        }
        
        logger.info(f"Processamento concluído: {stats_total['total_registros']} registros")
        
        return ProcessResponse(
            status="success",
            dados_processados=response_data,
            estatisticas=stats_total,
            message=f"Processados {stats_total['total_registros']} pedidos de {PAISES_MAP[request_body.pais_id]}"
        )
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na automação: {str(e)}")
        
    finally:
        if driver:
            driver.quit()

# ====================================
# ENDPOINT DE COMPATIBILIDADE (TEMPORÁRIO)
# ====================================
# Mantém compatibilidade com Chegou Hub até atualização do código lá
@app.post("/metricas/ecomhub/analises/processar_selenium/")
@limiter.limit("5/minute") if RATE_LIMITING_ENABLED else lambda f: f
async def processar_ecomhub_legacy(
    request_body: ProcessRequest,
    request: Request
):
    """
    ENDPOINT DE COMPATIBILIDADE (TEMPORÁRIO) - SEM AUTENTICAÇÃO

    ⚠️ Este endpoint NÃO requer autenticação para manter compatibilidade.
    ⚠️ IMPORTANTE: Este é um risco de segurança temporário!

    Este endpoint mantém compatibilidade com o código antigo do Chegou Hub.

    AÇÃO NECESSÁRIA: Atualizar o código do Chegou Hub para usar o novo endpoint:
    - URL: /api/processar-ecomhub/
    - Header: X-API-Key: sua-chave-api

    Após atualização, REMOVER ESTE ENDPOINT!
    """
    logger.warning("⚠️ [LEGACY ENDPOINT] /metricas/ecomhub/analises/processar_selenium/ (SEM AUTENTICAÇÃO)")
    logger.warning("⚠️ RISCO DE SEGURANÇA: Endpoint sem autenticação ativo")
    logger.warning("⚠️ AÇÃO NECESSÁRIA: Atualizar Chegou Hub e remover este endpoint")

    # Processar diretamente sem passar pela verificação de API key
    logger.info(f"Processamento: {request_body.data_inicio} - {request_body.data_fim}, País: {request_body.pais_id}")

    # VALIDAÇÃO: Aceitar "todos" ou países específicos
    if request_body.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")

    driver = None
    try:
        headless = os.getenv("ENVIRONMENT") != "local"

        @safe_driver_operation
        def _create_and_process():
            nonlocal driver
            driver = create_driver(headless=headless)
            login_ecomhub(driver)
            return extract_via_api(driver, request_body.data_inicio, request_body.data_fim, request_body.pais_id)

        orders_data = _create_and_process()

        if not orders_data:
            return ProcessResponse(
                status="success",
                dados_processados={"visualizacao_total": [], "visualizacao_otimizada": []},
                estatisticas={"total_registros": 0, "total_produtos": 0},
                message="Nenhum pedido encontrado"
            )

        # SEMPRE INCLUIR COLUNA PAÍS
        incluir_pais = True

        # Retornar ambas as visualizações
        processed_data_total, stats_total = process_effectiveness_data(orders_data, incluir_pais)
        processed_data_otimizada, stats_otimizada = process_effectiveness_optimized(orders_data, incluir_pais)

        response_data = {
            "visualizacao_total": processed_data_total,
            "visualizacao_otimizada": processed_data_otimizada,
            "stats_total": stats_total,
            "stats_otimizada": stats_otimizada
        }

        logger.info(f"Processamento concluído: {stats_total['total_registros']} registros")

        return ProcessResponse(
            status="success",
            dados_processados=response_data,
            estatisticas=stats_total,
            message=f"Processados {stats_total['total_registros']} pedidos de {PAISES_MAP[request_body.pais_id]}"
        )

    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na automação: {str(e)}")

    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import uvicorn

    # IMPORTANTE: Railway Cron tem limitação mínima de 5 minutos
    # Como tokens expiram em 3 minutos, precisamos usar thread em background
    if os.getenv("TOKEN_SYNC_ENABLED", "false").lower() == "true":
        logger.info("🔄 Iniciando serviço de sincronização de tokens...")
        try:
            from threading import Thread

            def safe_start_sync():
                """Função wrapper para proteger o início da sincronização"""
                try:
                    from token_sync.scheduler import start_background_sync
                    start_background_sync()
                except Exception as sync_error:
                    logger.error(f"❌ Erro na thread de sincronização: {sync_error}")
                    logger.warning("⚠️ Sincronização falhando, mas servidor continua funcionando")

            # Iniciar em thread separada para não bloquear o servidor
            sync_thread = Thread(target=safe_start_sync, daemon=True, name="TokenSyncThread")
            sync_thread.start()
            logger.info("✅ Serviço de sincronização iniciado em background (a cada 2 minutos)")
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar sincronização de tokens: {e}")
            logger.info("⚠️ Continuando sem sincronização automática...")

    # Iniciar servidor FastAPI normalmente
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)