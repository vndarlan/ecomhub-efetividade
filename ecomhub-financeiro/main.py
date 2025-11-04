"""
Serviço de Autenticação EcomHub
================================

Este serviço fornece um endpoint para obter tokens de autenticação da EcomHub
automaticamente usando Selenium, além de documentação sobre como usar a API.

Endpoints:
- POST /api/auth - Retorna cookies e tokens de autenticação
- GET / - Página inicial
- GET /docs - Documentação Swagger da API de autenticação
- GET /api-ecomhub-docs - Documentação da API EcomHub
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import uvicorn

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
ECOMHUB_LOGIN_URL = "https://go.ecomhub.app/login"
LOGIN_EMAIL = os.getenv("ECOMHUB_EMAIL", "saviomendesalvess@gmail.com")
LOGIN_PASSWORD = os.getenv("ECOMHUB_PASSWORD", "Chegou123!")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
PORT = int(os.getenv("PORT", 8002))

# FastAPI app
app = FastAPI(
    title="EcomHub Auth Service",
    description="Serviço de autenticação automática para EcomHub API",
    version="1.0.0"
)


class AuthResponse(BaseModel):
    """Modelo de resposta de autenticação"""
    success: bool
    cookies: Dict[str, str]
    cookie_string: str
    headers: Dict[str, str]
    timestamp: str
    message: str


def create_chrome_driver(headless: bool = True):
    """
    Cria e configura o Chrome WebDriver

    Args:
        headless: Se True, roda Chrome em modo headless

    Returns:
        WebDriver configurado
    """
    options = Options()

    # Configurações comuns
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Modo headless para produção
    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--disable-background-timer-throttling")

    # Configurar service baseado no ambiente
    if ENVIRONMENT == "local":
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Produção (Railway)
        options.binary_location = "/usr/bin/google-chrome"
        driver = webdriver.Chrome(options=options)

    # Timeouts
    driver.implicitly_wait(15)
    driver.set_page_load_timeout(45)
    driver.set_script_timeout(30)

    # Remove detecção de webdriver
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    logger.info(f"✅ Chrome driver criado (headless={headless})")
    return driver


def login_ecomhub(driver) -> bool:
    """
    Faz login na EcomHub usando Selenium

    Args:
        driver: WebDriver do Chrome

    Returns:
        True se login bem-sucedido, False caso contrário
    """
    try:
        logger.info("🔐 Iniciando login na EcomHub...")

        # Navegar para página de login
        driver.get(ECOMHUB_LOGIN_URL)

        # Aguardar carregamento
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)

        # Verificar se já está logado
        if "login" not in driver.current_url.lower():
            logger.info("✅ Já autenticado")
            return True

        # Preencher email
        email_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "input-email"))
        )
        email_field.clear()
        email_field.send_keys(LOGIN_EMAIL)
        logger.info("📧 Email preenchido")

        # Preencher senha
        password_field = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "input-password"))
        )
        password_field.clear()
        password_field.send_keys(LOGIN_PASSWORD)
        logger.info("🔑 Senha preenchida")

        time.sleep(2)

        # Clicar no botão de login
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "a[role='button'].btn.tone-default")
            )
        )
        driver.execute_script("arguments[0].scrollIntoView();", login_button)
        time.sleep(1)
        login_button.click()
        logger.info("🖱️ Botão de login clicado")

        # Aguardar redirecionamento (confirma login bem-sucedido)
        WebDriverWait(driver, 30).until(
            lambda d: "login" not in d.current_url.lower() or
                     len(d.find_elements(By.ID, "input-email")) == 0
        )

        logger.info("✅ Login bem-sucedido!")
        return True

    except Exception as e:
        logger.error(f"❌ Erro no login: {e}")
        try:
            driver.save_screenshot("login_error.png")
            logger.info("📸 Screenshot salvo: login_error.png")
        except:
            pass
        return False


def get_auth_data(driver) -> Dict:
    """
    Extrai cookies e headers de autenticação

    Args:
        driver: WebDriver do Chrome

    Returns:
        Dicionário com cookies, headers e metadados
    """
    # Extrair todos os cookies
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']

    # Criar cookie string para uso em requisições
    cookie_string = "; ".join([f"{k}={v}" for k, v in cookies.items()])

    # Headers necessários para API EcomHub
    headers = {
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://go.ecomhub.app",
        "Referer": "https://go.ecomhub.app/",
        "User-Agent": driver.execute_script("return navigator.userAgent;"),
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json"
    }

    logger.info(f"✅ Cookies extraídos: {list(cookies.keys())}")

    return {
        "cookies": cookies,
        "cookie_string": cookie_string,
        "headers": headers,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/", response_class=HTMLResponse)
async def home():
    """Página inicial com informações sobre o serviço"""
    html = """
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EcomHub Auth Service</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 800px;
                width: 100%;
                padding: 40px;
            }
            h1 {
                color: #667eea;
                margin-bottom: 10px;
                font-size: 2.5em;
            }
            .subtitle {
                color: #666;
                margin-bottom: 30px;
                font-size: 1.1em;
            }
            .section {
                margin: 30px 0;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 10px;
                border-left: 4px solid #667eea;
            }
            h2 {
                color: #333;
                margin-bottom: 15px;
                font-size: 1.5em;
            }
            .links {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 20px;
            }
            .link-card {
                background: white;
                padding: 20px;
                border-radius: 10px;
                text-decoration: none;
                color: #333;
                transition: transform 0.2s, box-shadow 0.2s;
                border: 2px solid #e0e0e0;
            }
            .link-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
                border-color: #667eea;
            }
            .link-card h3 {
                color: #667eea;
                margin-bottom: 10px;
            }
            .link-card p {
                color: #666;
                font-size: 0.9em;
            }
            code {
                background: #2d2d2d;
                color: #f8f8f2;
                padding: 15px;
                border-radius: 5px;
                display: block;
                margin: 10px 0;
                overflow-x: auto;
                font-family: 'Courier New', monospace;
            }
            .endpoint {
                background: white;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
                border-left: 3px solid #28a745;
            }
            .endpoint-method {
                display: inline-block;
                background: #28a745;
                color: white;
                padding: 3px 10px;
                border-radius: 3px;
                font-weight: bold;
                margin-right: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔐 EcomHub Auth Service</h1>
            <p class="subtitle">Serviço de autenticação automática para EcomHub API</p>

            <div class="section">
                <h2>📋 Sobre</h2>
                <p>Este serviço fornece autenticação automática para a API da EcomHub, eliminando a necessidade de copiar tokens manualmente do navegador.</p>
            </div>

            <div class="section">
                <h2>🚀 Endpoint Principal</h2>
                <div class="endpoint">
                    <span class="endpoint-method">POST</span>
                    <strong>/api/auth</strong>
                </div>
                <p><strong>Retorna:</strong> Cookies e headers de autenticação em formato JSON</p>
                <code>{
  "success": true,
  "cookies": { "token": "...", "e_token": "..." },
  "cookie_string": "token=...; e_token=...",
  "headers": { ... },
  "timestamp": "2025-11-04T15:30:00Z"
}</code>
            </div>

            <div class="section">
                <h2>📚 Documentação</h2>
                <div class="links">
                    <a href="/docs" class="link-card">
                        <h3>📖 API Docs</h3>
                        <p>Documentação interativa Swagger</p>
                    </a>
                    <a href="/api-ecomhub-docs" class="link-card">
                        <h3>🌐 API EcomHub</h3>
                        <p>Como usar a API da EcomHub</p>
                    </a>
                </div>
            </div>

            <div class="section">
                <h2>💡 Exemplo de Uso (n8n)</h2>
                <p>1. Configure um nó HTTP Request</p>
                <p>2. Método: POST</p>
                <p>3. URL: <code style="display:inline;padding:2px 5px;">https://seu-servico.railway.app/api/auth</code></p>
                <p>4. Use os cookies retornados nas próximas requisições para api.ecomhub.app</p>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


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
                        <td>Número da página (0, 1, 2, ...)</td>
                    </tr>
                    <tr>
                        <td><code>orderBy</code></td>
                        <td>string</td>
                        <td>Não</td>
                        <td>Campo para ordenação (use "null" para padrão)</td>
                    </tr>
                    <tr>
                        <td><code>orderDirection</code></td>
                        <td>string</td>
                        <td>Não</td>
                        <td>Direção da ordenação (use "null" para padrão)</td>
                    </tr>
                    <tr>
                        <td><code>conditions</code></td>
                        <td>JSON string</td>
                        <td>Sim</td>
                        <td>Filtros de data e país (ver exemplos)</td>
                    </tr>
                    <tr>
                        <td><code>search</code></td>
                        <td>string</td>
                        <td>Não</td>
                        <td>Termo de busca (deixe vazio se não usar)</td>
                    </tr>
                </tbody>
            </table>

            <h3>Estrutura do <code>conditions</code></h3>
            <p>O parâmetro conditions deve ser um JSON stringificado com a seguinte estrutura:</p>
            <pre><code>{
  "orders": {
    "date": {
      "start": "2025-08-01",   // Data início (YYYY-MM-DD)
      "end": "2025-08-20"      // Data fim (YYYY-MM-DD)
    },
    "shippingCountry_id": [164, 41, 66]  // Array de IDs de países
  }
}</code></pre>

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

            <h2>🔄 Paginação</h2>
            <div class="info">
                <p><strong>Como funciona:</strong></p>
                <ul style="margin-left: 20px; margin-top: 10px;">
                    <li>Cada requisição retorna até 48 pedidos</li>
                    <li>Use <code>offset=0</code> para primeira página</li>
                    <li>Incremente o offset para próximas páginas (1, 2, 3...)</li>
                    <li>Continue até a API retornar array vazio</li>
                </ul>
            </div>

            <h2>💻 Exemplos Práticos</h2>

            <h3>Exemplo 1: Buscar Pedidos de Agosto na Espanha</h3>
            <pre><code>GET https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions={"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164]}}&search=</code></pre>

            <h3>Exemplo 2: Pedidos de Múltiplos Países</h3>
            <pre><code>GET https://api.ecomhub.app/api/orders?offset=0&orderBy=null&orderDirection=null&conditions={"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164,82,66]}}&search=</code></pre>

            <h3>Exemplo 3: Paginação (Segunda Página)</h3>
            <pre><code>GET https://api.ecomhub.app/api/orders?offset=1&orderBy=null&orderDirection=null&conditions={"orders":{"date":{"start":"2025-08-01","end":"2025-08-31"},"shippingCountry_id":[164]}}&search=</code></pre>

            <h2>🔧 Exemplo de Código Python</h2>
            <pre><code>import requests
import json

# 1. Obter autenticação
auth_response = requests.post("https://seu-servico.railway.app/api/auth")
auth_data = auth_response.json()

# 2. Preparar sessão com cookies
session = requests.Session()
session.cookies.update(auth_data["cookies"])
session.headers.update(auth_data["headers"])

# 3. Definir filtros
conditions = {
    "orders": {
        "date": {
            "start": "2025-08-01",
            "end": "2025-08-31"
        },
        "shippingCountry_id": [164]  # Espanha
    }
}

# 4. Buscar pedidos com paginação
page = 0
all_orders = []

while True:
    params = {
        "offset": page,
        "orderBy": "null",
        "orderDirection": "null",
        "conditions": json.dumps(conditions),
        "search": ""
    }

    response = session.get(
        "https://api.ecomhub.app/api/orders",
        params=params
    )

    orders = response.json()

    if not orders:
        break  # Fim dos dados

    all_orders.extend(orders)
    page += 1

print(f"Total de pedidos: {len(all_orders)}")</code></pre>

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


@app.post("/api/auth", response_model=AuthResponse)
async def authenticate():
    """
    Endpoint para obter autenticação da EcomHub

    Returns:
        AuthResponse com cookies, headers e metadados

    Raises:
        HTTPException: Se falhar no login
    """
    driver = None

    try:
        logger.info("🚀 Iniciando processo de autenticação...")

        # Criar driver (headless em produção, visível em local)
        headless = ENVIRONMENT != "local"
        driver = create_chrome_driver(headless=headless)

        # Fazer login
        login_success = login_ecomhub(driver)

        if not login_success:
            raise HTTPException(
                status_code=500,
                detail="Falha no login da EcomHub"
            )

        # Extrair dados de autenticação
        auth_data = get_auth_data(driver)

        logger.info("✅ Autenticação concluída com sucesso!")

        return AuthResponse(
            success=True,
            cookies=auth_data["cookies"],
            cookie_string=auth_data["cookie_string"],
            headers=auth_data["headers"],
            timestamp=auth_data["timestamp"],
            message="Autenticação bem-sucedida"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro na autenticação: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno: {str(e)}"
        )
    finally:
        # Fechar driver
        if driver:
            try:
                driver.quit()
                logger.info("🔒 Driver fechado")
            except:
                pass


@app.get("/health")
async def health():
    """Endpoint de healthcheck"""
    return {
        "status": "healthy",
        "service": "ecomhub-auth",
        "environment": ENVIRONMENT,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    logger.info(f"🚀 Iniciando EcomHub Auth Service na porta {PORT}")
    logger.info(f"📍 Ambiente: {ENVIRONMENT}")
    logger.info(f"📧 Email: {LOGIN_EMAIL}")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info"
    )
