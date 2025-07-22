# main.py - COM SUPORTE A "TODOS OS PAÍSES" + REPÚBLICA CHECA E POLÔNIA
from fastapi import FastAPI, HTTPException
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

app = FastAPI(title="EcomHub Selenium Automation", version="1.0.0")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Configurações
ECOMHUB_URL = "https://go.ecomhub.app/login"
LOGIN_EMAIL = "saviomendesalvess@gmail.com"
LOGIN_PASSWORD = "Chegou123!"

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
    """Cria driver Chrome configurado - VERSÃO RAILWAY COMPATÍVEL"""
    options = Options()
    
    # Configurações básicas
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-features=VizDisplayCompositor")
    
    # Para ambiente local
    if os.getenv("ENVIRONMENT") == "local":
        headless = False
        logger.info("🔧 Modo LOCAL - Browser visível")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    
    # Para Railway (produção) - configuração específica
    logger.info("🔧 Modo PRODUÇÃO - Railway")
    options.add_argument("--headless=new")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.binary_location = "/usr/bin/google-chrome"
    
    try:
        driver = webdriver.Chrome(options=options)
        logger.info("✅ ChromeDriver criado para Railway")
        
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)
        
        return driver
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar driver Railway: {e}")
        raise HTTPException(status_code=500, detail=f"Erro Chrome Railway: {str(e)}")

def login_ecomhub(driver):
    """Faz login no EcomHub"""
    logger.info("Fazendo login no EcomHub...")
    
    driver.get(ECOMHUB_URL)
    
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    time.sleep(3)
    
    try:
        email_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "input-email"))
        )
        email_field.clear()
        email_field.send_keys(LOGIN_EMAIL)
        logger.info("✅ Email preenchido")
        
        password_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "input-password"))
        )
        password_field.clear()
        password_field.send_keys(LOGIN_PASSWORD)
        logger.info("✅ Senha preenchida")
        
        time.sleep(1)
        
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[role='button'].btn.tone-default"))
        )
        
        driver.execute_script("arguments[0].scrollIntoView();", login_button)
        time.sleep(0.5)
        
        login_button.click()
        logger.info("✅ Botão de login clicado")
        
        WebDriverWait(driver, 20).until(
            lambda d: "login" not in d.current_url.lower() or 
                     len(d.find_elements(By.ID, "input-email")) == 0
        )
        
        logger.info("✅ Login realizado com sucesso!")
        logger.info(f"🔗 URL atual: {driver.current_url}")
        
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
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

@app.get("/")
async def root():
    return {"message": "EcomHub Selenium Automation Server", "status": "running"}

@app.post("/api/processar-ecomhub/", response_model=ProcessResponse)
async def processar_ecomhub(request: ProcessRequest):
    """Endpoint principal - COM SUPORTE A TODOS OS PAÍSES + NOVOS PAÍSES"""
    
    logger.info(f"Processamento: {request.data_inicio} - {request.data_fim}, País: {request.pais_id}")
    
    # VALIDAÇÃO MODIFICADA: Aceitar "todos" ou países específicos (incluindo novos)
    if request.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")
    
    driver = None
    try:
        headless = os.getenv("ENVIRONMENT") != "local"
        driver = create_driver(headless=headless)
        
        # Fazer login
        login_ecomhub(driver)
        
        # Extrair dados via API direta
        orders_data = extract_via_api(driver, request.data_inicio, request.data_fim, request.pais_id)
        
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
            message=f"Processados {stats_total['total_registros']} pedidos de {PAISES_MAP[request.pais_id]}"
        )
        
    except Exception as e:
        logger.error(f"Erro no processamento: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na automação: {str(e)}")
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)