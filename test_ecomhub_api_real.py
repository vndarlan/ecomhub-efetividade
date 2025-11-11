"""
Script para obter um pedido real da API EcomHub e mapear todos os campos.

Uso: ENVIRONMENT=local python test_ecomhub_api_real.py
"""

import os
import sys
import json
import requests

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Configurações
LOGIN_URL = "https://go.ecomhub.app/login"
API_URL = "https://api.ecomhub.app/api/orders"

# Tentar obter credenciais do ambiente ou usar padrão
LOGIN_EMAIL = os.getenv("ECOMHUB_EMAIL", "saviomendesalvess@gmail.com")
LOGIN_PASSWORD = os.getenv("ECOMHUB_PASSWORD", "Chegou123!")

def create_driver():
    """Cria driver do Chrome para ambiente local"""
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(10)

    return driver

def login_ecomhub(driver):
    """Faz login no EcomHub e retorna cookies"""
    print("🔐 Fazendo login no EcomHub...")

    driver.get(LOGIN_URL)

    # Aguardar e preencher email
    email_input = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "email"))
    )
    email_input.clear()
    email_input.send_keys(LOGIN_EMAIL)
    print("✅ Email preenchido")

    # Preencher senha
    password_input = driver.find_element(By.ID, "password")
    password_input.clear()
    password_input.send_keys(LOGIN_PASSWORD)
    print("✅ Senha preenchida")

    # Clicar no botão de login
    login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
    login_button.click()
    print("✅ Botão de login clicado")

    # Aguardar redirecionamento
    WebDriverWait(driver, 30).until(
        EC.url_contains("dashboard")
    )
    print("✅ Login realizado com sucesso!")

    # Extrair cookies
    cookies = {}
    for cookie in driver.get_cookies():
        cookies[cookie['name']] = cookie['value']

    print(f"📦 Cookies obtidos: {list(cookies.keys())}")

    return cookies

def get_order_from_api(cookies):
    """Faz requisição para API e obtém 1 pedido dos últimos 7 dias"""
    print("\n🔍 Fazendo requisição para API da EcomHub...")

    # Datas: últimos 7 dias
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=7)

    data_inicio_str = data_inicio.strftime("%Y-%m-%d")
    data_fim_str = data_fim.strftime("%Y-%m-%d")

    print(f"📅 Período: {data_inicio_str} até {data_fim_str}")
    print(f"🌍 País: Espanha (164)")

    # Montar conditions
    conditions = {
        "orders": {
            "date": {
                "start": data_inicio_str,
                "end": data_fim_str
            },
            "shippingCountry_id": [164]  # Espanha
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

    # Headers
    headers = {
        "Accept": "*/*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://go.ecomhub.app",
        "Referer": "https://go.ecomhub.app/",
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": "application/json"
    }

    # Criar sessão com cookies
    session = requests.Session()
    session.headers.update(headers)
    session.cookies.update(cookies)

    # Fazer requisição
    print(f"🚀 Chamando: {API_URL}")
    response = session.get(API_URL, params=params, timeout=60)

    print(f"📡 Status Code: {response.status_code}")

    if response.status_code == 200:
        orders = response.json()
        print(f"✅ {len(orders)} pedidos retornados")

        if orders and len(orders) > 0:
            # Pegar apenas o primeiro pedido
            order = orders[0]
            return order
        else:
            print("⚠️ Nenhum pedido encontrado no período")
            return None
    else:
        print(f"❌ Erro na requisição: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def main():
    """Função principal"""
    print("=" * 70)
    print("🔬 TESTE DE API DA ECOMHUB - CAPTURA DE PEDIDO REAL")
    print("=" * 70)

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("❌ Erro: ECOMHUB_EMAIL e ECOMHUB_PASSWORD devem estar configurados")
        return

    driver = None

    try:
        # 1. Criar driver e fazer login
        driver = create_driver()
        cookies = login_ecomhub(driver)

        # 2. Obter pedido da API
        order = get_order_from_api(cookies)

        if order:
            # 3. Salvar em arquivo
            output_file = "pedido_exemplo.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(order, f, indent=2, ensure_ascii=False)

            print(f"\n✅ Pedido salvo em: {output_file}")

            # 4. Imprimir resumo
            print("\n" + "=" * 70)
            print("📦 RESUMO DO PEDIDO")
            print("=" * 70)
            print(f"ID: {order.get('id')}")
            print(f"Número: {order.get('shopifyOrderNumber')}")
            print(f"Status: {order.get('status')}")
            print(f"Data: {order.get('date')}")
            print(f"País: {order.get('shippingCountry')}")
            print(f"Cliente: {order.get('customerName')}")
            print(f"Preço: {order.get('price')} {order.get('currencies', {}).get('code', '')}")

            if order.get('ordersItems') and len(order.get('ordersItems')) > 0:
                item = order['ordersItems'][0]
                product_name = item.get('productsVariants', {}).get('products', {}).get('name', 'N/A')
                print(f"Produto: {product_name}")

            # 5. Contar campos
            print(f"\n📊 Total de campos no nível raiz: {len(order.keys())}")
            print(f"📋 Campos disponíveis: {', '.join(sorted(order.keys())[:20])}...")

            # 6. Imprimir JSON completo formatado
            print("\n" + "=" * 70)
            print("📄 JSON COMPLETO (primeiras 100 linhas):")
            print("=" * 70)
            json_str = json.dumps(order, indent=2, ensure_ascii=False)
            lines = json_str.split('\n')
            for line in lines[:100]:
                print(line)

            if len(lines) > 100:
                print(f"\n... (mais {len(lines) - 100} linhas)")
                print(f"\nVeja o arquivo {output_file} para o JSON completo")

            print("\n✅ SUCESSO! Pedido capturado e salvo.")

        else:
            print("\n❌ Não foi possível obter pedido da API")

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            print("\n🔒 Fechando navegador...")
            driver.quit()
            print("✅ Navegador fechado")

if __name__ == "__main__":
    main()
