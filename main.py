# main.py
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

app = FastAPI(title="EcomHub Selenium Automation", version="1.0.0")

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Models
class ProcessRequest(BaseModel):
    data_inicio: str  # YYYY-MM-DD
    data_fim: str     # YYYY-MM-DD
    pais_id: str      # 164=Espanha, 41=Croácia

class ProcessResponse(BaseModel):
    status: str
    dados_processados: list
    estatisticas: dict
    message: str

# Configurações
ECOMHUB_URL = "https://go.ecomhub.app/login"
LOGIN_EMAIL = "saviomendesalvess@gmail.com"
LOGIN_PASSWORD = "Chegou123!"

PAISES_MAP = {
    "164": "Espanha",
    "41": "Croácia"
}

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
        # Não usar webdriver-manager em produção
        driver = webdriver.Chrome(options=options)
        logger.info("✅ ChromeDriver criado para Railway")
        
        # Configurar timeouts
        driver.implicitly_wait(10)
        driver.set_page_load_timeout(30)
        
        return driver
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar driver Railway: {e}")
        raise HTTPException(status_code=500, detail=f"Erro Chrome Railway: {str(e)}")

def login_ecomhub(driver):
    """Faz login no EcomHub - VERSÃO CORRIGIDA"""
    logger.info("Fazendo login no EcomHub...")
    
    driver.get(ECOMHUB_URL)
    
    # Aguardar página carregar
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    time.sleep(3)  # Aguardar JavaScript carregar
    
    try:
        # Campo de email - usar ID específico
        email_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "input-email"))
        )
        email_field.clear()
        email_field.send_keys(LOGIN_EMAIL)
        logger.info("✅ Email preenchido")
        
        # Campo de senha - usar ID específico  
        password_field = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "input-password"))
        )
        password_field.clear()
        password_field.send_keys(LOGIN_PASSWORD)
        logger.info("✅ Senha preenchida")
        
        time.sleep(1)  # Pequena pausa
        
        # Botão de login - usar seletor específico
        login_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[role='button'].btn.tone-default"))
        )
        
        # Scroll para o botão se necessário
        driver.execute_script("arguments[0].scrollIntoView();", login_button)
        time.sleep(0.5)
        
        # Clicar no botão
        login_button.click()
        logger.info("✅ Botão de login clicado")
        
        # Aguardar redirecionamento (verificar se saiu da página de login)
        WebDriverWait(driver, 20).until(
            lambda d: "login" not in d.current_url.lower() or 
                     len(d.find_elements(By.ID, "input-email")) == 0
        )
        
        logger.info("✅ Login realizado com sucesso!")
        logger.info(f"🔗 URL atual: {driver.current_url}")
        
    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        logger.error(f"🔗 URL atual: {driver.current_url}")
        
        # Debug: capturar screenshot se possível
        try:
            driver.save_screenshot("login_error.png")
            logger.info("📸 Screenshot salvo: login_error.png")
        except:
            pass
            
        raise e

import requests
import urllib.parse
import json

def get_auth_cookies(driver):
    """Obter cookies de autenticação após login"""
    cookies = driver.get_cookies()
    session_cookies = {}
    
    for cookie in cookies:
        session_cookies[cookie['name']] = cookie['value']
    
    logger.info(f"✅ Cookies obtidos: {list(session_cookies.keys())}")
    return session_cookies

def extract_via_api(driver, data_inicio, data_fim, pais_id):
    """Extrai dados via API direta do EcomHub"""
    logger.info("🚀 Extraindo via API direta...")
    
    # Obter cookies após login
    cookies = get_auth_cookies(driver)
    
    # Construir parâmetros da API (igual à API real)
    conditions = {
        "orders": {
            "date": {
                "start": data_inicio,
                "end": data_fim
            },
            "shippingCountry_id": int(pais_id)  # NÚMERO, não string
        }
    }
    
    # URL da API
    api_url = "https://api.ecomhub.app/api/orders"
    params = {
        "offset": 0,
        "orderBy": "null",
        "orderDirection": "null", 
        "conditions": json.dumps(conditions),
        "search": ""
    }
    
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Content-Type": "application/json",
        "Origin": "https://go.ecomhub.app",
        "Referer": "https://go.ecomhub.app/",
        "Sec-Ch-Ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors", 
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }
    
    logger.info(f"🔍 Conditions JSON: {json.dumps(conditions)}")
    logger.info(f"🔍 Params: {params}")
    
    all_orders = []
    offset = 0
    
    while True:
        params["offset"] = offset
        
        try:
            logger.info(f"📡 Chamando API offset={offset}...")
            
            # Testar primeiro sem cookies
            response_test = requests.get(api_url, params=params, headers=headers)
            logger.info(f"🧪 Teste SEM cookies - Status: {response_test.status_code}")
            
            response = requests.get(api_url, params=params, headers=headers, cookies=cookies, timeout=60)
            
            logger.info(f"🔍 Status Code: {response.status_code}")
            logger.info(f"🔍 Encoding: {response.encoding}")
            
            if response.status_code != 200:
                logger.error(f"❌ API erro {response.status_code}")
                break
            
            try:
                # Forçar decodificação correta
                response.encoding = 'utf-8'
                content = response.text
                
                # Se ainda estiver comprimido, usar content
                if not content or content.startswith(('�', '\x00')):
                    import gzip
                    import io
                    content = gzip.decompress(response.content).decode('utf-8')
                    logger.info("🔧 Decompressão manual aplicada")
                
                orders = json.loads(content)
                logger.info(f"✅ JSON decodificado: {len(orders)} itens")
                
            except Exception as e:
                logger.error(f"❌ Erro JSON: {e}")
                # Fallback: tentar response.json() direto
                try:
                    orders = response.json()
                    logger.info("✅ Fallback JSON funcionou")
                except:
                    logger.error("❌ Fallback também falhou")
                    break
            
            if not orders:
                logger.info("📡 Sem mais dados - parando")
                break
                
            logger.info(f"📡 Recebidos {len(orders)} pedidos")
            
            # Processar pedidos da API
            for order in orders:
                try:
                    # Extrair produto do caminho correto
                    produto = "Produto Desconhecido"
                    
                    # Caminho: ordersItems[0].productsVariants.products.name
                    orders_items = order.get("ordersItems", [])
                    if orders_items and len(orders_items) > 0:
                        variants = orders_items[0].get("productsVariants", {})
                        products = variants.get("products", {})
                        produto = products.get("name", produto)
                    
                    order_data = {
                        'numero_pedido': order.get('shopifyOrderNumber', ''),
                        'produto': produto,
                        'data': order.get('createdAt', ''),
                        'pais': order.get('shippingCountry', ''),
                        'preco': order.get('price', ''),
                        'status': order.get('status', ''),
                        'loja': order.get('stores', {}).get('name', '')
                    }
                    
                    all_orders.append(order_data)
                    
                except Exception as e:
                    logger.warning(f"Erro ao processar pedido API: {e}")
                    continue
            
            offset += len(orders)
            
            # Limite de segurança
            if offset > 10000:
                logger.warning("⚠️ Limite de 10k pedidos atingido")
                break
                
        except Exception as e:
            logger.error(f"❌ Erro na chamada API: {e}")
            break
    
    logger.info(f"✅ Total extraído via API: {len(all_orders)} pedidos")
    return all_orders

def extract_all_pages_data(driver, data_inicio, data_fim, pais_id):
    """Extrai dados de todas as páginas com produto real"""
    logger.info(f"Extraindo todos os pedidos: {data_inicio} até {data_fim}, País ID: {pais_id}")
    
    all_orders = []
    page = 0
    
    while True:
        orders_url = f"https://go.ecomhub.app/orders?conditions.orders.date.start={data_inicio}&conditions.orders.date.end={data_fim}&conditions.orders.shippingCountry_id={pais_id}&page={page}"
        
        logger.info(f"📄 Processando página {page}...")
        driver.get(orders_url)
        
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.has-rowAction")
        
        if len(rows) == 0:
            logger.info(f"📄 Página {page} vazia - parando busca")
            break
            
        logger.info(f"📄 Página {page}: {len(rows)} pedidos encontrados")
        
        page_orders = []
        for i, row in enumerate(rows):
            try:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if len(cells) >= 7:
                    # Pegar URL do pedido para extrair produto real
                    order_link = cells[0].find_element(By.TAG_NAME, "a")
                    order_url = order_link.get_attribute("href")
                    
                    order_data = {
                        'numero_pedido': cells[0].text.strip(),
                        'loja': cells[1].text.strip(),  # Esta é a loja
                        'data': cells[2].text.strip(),
                        'warehouse': cells[3].text.strip(),
                        'pais': cells[4].text.strip(),
                        'preco': cells[5].text.strip(),
                        'status': cells[6].text.strip(),
                        'pagina': page
                    }
                    
                    # Extrair produto real (mais lento)
                    if i < 5:  # Só primeiros 5 por página para teste
                        produto_real = extract_product_details(driver, order_url)
                        order_data['produto'] = produto_real
                        logger.info(f"   Produto extraído: {produto_real}")
                    else:
                        order_data['produto'] = order_data['loja']  # Fallback
                    
                    page_orders.append(order_data)
            except Exception as e:
                logger.warning(f"Erro ao extrair linha da página {page}: {e}")
                continue
        
        all_orders.extend(page_orders)
        logger.info(f"📄 Página {page}: {len(page_orders)} pedidos válidos extraídos")
        
        page += 1
        
        if page > 10:  # Limite reduzido por ser mais lento
            logger.warning("⚠️ Limite de 10 páginas atingido")
            break
    
    logger.info(f"✅ Total extraído: {len(all_orders)} pedidos de {page} páginas")
    return all_orders

def extract_orders_data(driver):
    """Extrai dados dos pedidos da tabela"""
    logger.info("Extraindo dados dos pedidos...")
    
    orders_data = []
    
    try:
        # Buscar todas as linhas da tabela
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.has-rowAction")
        
        logger.info(f"Encontradas {len(rows)} linhas de pedidos")
        
        for row in rows:
            try:
                # Extrair dados de cada coluna
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                
                if len(cells) >= 7:  # Verificar se tem colunas suficientes
                    order_data = {
                        'numero_pedido': cells[0].text.strip(),
                        'produto': cells[1].text.strip(),
                        'data': cells[2].text.strip(),
                        'warehouse': cells[3].text.strip(),
                        'pais': cells[4].text.strip(),
                        'preco': cells[5].text.strip(),
                        'status': cells[6].text.strip()
                    }
                    
                    # Extrair nome do produto do link se existir
                    link_element = cells[1].find_element(By.TAG_NAME, "a") if cells[1].find_elements(By.TAG_NAME, "a") else None
                    if link_element:
                        order_data['produto'] = link_element.text.strip()
                    
                    orders_data.append(order_data)
                    
            except Exception as e:
                logger.warning(f"Erro ao extrair dados da linha: {e}")
                continue
        
        logger.info(f"Extraídos {len(orders_data)} pedidos com sucesso")
        return orders_data
        
    except Exception as e:
        logger.error(f"Erro ao extrair dados: {e}")
        return []

def process_effectiveness_data(orders_data):
    """Processa dados e calcula efetividade por produto"""
    logger.info("Processando efetividade por produto...")
    
    product_counts = defaultdict(lambda: {"Total_Registros": 0, "Delivered_Count": 0})
    
    # Obter status únicos
    unique_statuses = list(set([order['status'] for order in orders_data if order['status']]))
    unique_statuses = sorted([status.strip() for status in unique_statuses])
    
    # Processar cada pedido
    for order in orders_data:
        produto = order.get('produto', 'Produto Desconhecido').strip()
        if not produto:
            produto = 'Produto Desconhecido'
        
        status = order.get('status', '').strip()
        
        # Inicializar produto se não existe
        if produto not in product_counts:
            product_counts[produto] = {"Total_Registros": 0, "Delivered_Count": 0}
            for unique_status in unique_statuses:
                product_counts[produto][unique_status] = 0
        
        # Contar registros
        product_counts[produto]["Total_Registros"] += 1
        
        if status in unique_statuses:
            product_counts[produto][status] += 1
        
        # Contar delivered (assumindo que status "Entregue" ou similar = delivered)
        if status.lower() in ['entregue', 'delivered', 'finalizado']:
            product_counts[produto]["Delivered_Count"] += 1
    
    # Converter para formato final
    result_data = []
    for produto, counts in product_counts.items():
        total_registros = counts["Total_Registros"]
        delivered = counts["Delivered_Count"]
        
        if total_registros > 0:
            efetividade = (delivered / total_registros) * 100
        else:
            efetividade = 0
        
        row = {
            "Produto": produto,
            "Total": total_registros,
        }
        
        # Adicionar cada status
        for status in unique_statuses:
            row[status] = counts[status]
        
        row["Efetividade"] = f"{efetividade:.0f}%"
        result_data.append(row)
    
    # Ordenar por efetividade
    if result_data:
        result_data.sort(key=lambda x: float(x["Efetividade"].replace('%', '')), reverse=True)
        
        # Adicionar linha de totais
        totals = {"Produto": "Total"}
        numeric_cols = ["Total"] + unique_statuses
        for col in numeric_cols:
            totals[col] = sum(row[col] for row in result_data)
        
        total_registros = totals["Total"]
        total_delivered = sum(row["Delivered_Count"] for row in product_counts.values())
        
        if total_registros > 0:
            efetividade_media = (total_delivered / total_registros) * 100
            totals["Efetividade"] = f"{efetividade_media:.0f}% (Média)"
        else:
            totals["Efetividade"] = "0% (Média)"
        
        result_data.append(totals)
    
    # Estatísticas
    stats = {
        'total_registros': len(orders_data),
        'total_produtos': len(product_counts),
        'produtos_com_dados': len([p for p in product_counts.values() if p["Total_Registros"] > 0])
    }
    
    return result_data, stats

@app.get("/")
async def root():
    return {"message": "EcomHub Selenium Automation Server", "status": "running"}

@app.post("/api/processar-ecomhub/", response_model=ProcessResponse)
async def processar_ecomhub(request: ProcessRequest):
    """Endpoint principal para processar dados via Selenium"""
    
    logger.info(f"Iniciando processamento: {request.data_inicio} - {request.data_fim}, País: {request.pais_id}")
    
    # Validações
    if request.pais_id not in PAISES_MAP:
        raise HTTPException(status_code=400, detail="País não suportado")
    
    driver = None
    try:
        # Criar driver (headless=False para desenvolvimento local)
        headless = os.getenv("ENVIRONMENT") != "local"
        driver = create_driver(headless=headless)
        
        # Fazer login
        login_ecomhub(driver)
        
        # Extrair dados via API direta
        orders_data = extract_via_api(driver, request.data_inicio, request.data_fim, request.pais_id)
        
        if not orders_data:
            logger.warning("Nenhum pedido encontrado")
            return ProcessResponse(
                status="success",
                dados_processados=[],
                estatisticas={"total_registros": 0, "total_produtos": 0},
                message="Nenhum pedido encontrado para o período selecionado"
            )
        
        # Processar efetividade
        processed_data, stats = process_effectiveness_data(orders_data)
        
        logger.info(f"Processamento concluído: {stats['total_registros']} registros, {stats['total_produtos']} produtos")
        
        return ProcessResponse(
            status="success",
            dados_processados=processed_data,
            estatisticas=stats,
            message=f"Processados {stats['total_registros']} pedidos de {PAISES_MAP[request.pais_id]}"
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