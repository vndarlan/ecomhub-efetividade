import requests
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import time

def test_api_complete():
    """Teste completo da API EcomHub com análise de estrutura"""
    
    # Login via Selenium
    options = Options()
    options.add_argument("--no-sandbox")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        # Login
        driver.get("https://go.ecomhub.app/login")
        time.sleep(3)
        
        driver.find_element(By.ID, "input-email").send_keys("saviomendesalvess@gmail.com")
        driver.find_element(By.ID, "input-password").send_keys("Chegou123!")
        driver.find_element(By.CSS_SELECTOR, "a[role='button'].btn.tone-default").click()
        time.sleep(5)
        
        # Pegar cookies
        cookies = {}
        for cookie in driver.get_cookies():
            cookies[cookie['name']] = cookie['value']
        
        print(f"✅ Login OK. Cookies: {len(cookies)}")
        
        # API call
        conditions = {
            "orders": {
                "date": {
                    "start": "2025-07-10",
                    "end": "2025-07-17"
                },
                "shippingCountry_id": 164
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
        
        response = requests.get("https://api.ecomhub.app/api/orders", 
                              params=params, headers=headers, cookies=cookies)
        
        print(f"📡 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📊 Tipo resposta: {type(data)}")
            print(f"📊 Total pedidos: {len(data) if isinstance(data, list) else 'não é lista'}")
            
            if isinstance(data, list) and len(data) > 0:
                # Analisar primeiro pedido
                order = data[0]
                print(f"\n🔍 ESTRUTURA DO PRIMEIRO PEDIDO:")
                print(f"Keys disponíveis: {list(order.keys())}")
                
                print(f"\n📦 DADOS PRINCIPAIS:")
                print(f"  ID: {order.get('id')}")
                print(f"  Number: {order.get('shopifyOrderNumber')}")
                print(f"  Name: {order.get('shopifyOrderName')}")  
                print(f"  Status: {order.get('status')}")
                print(f"  Price: {order.get('price')}")
                print(f"  Created: {order.get('createdAt')}")
                
                # Procurar produtos/itens
                print(f"\n🛍️ PROCURANDO PRODUTOS:")
                if 'items' in order:
                    items = order['items']
                    print(f"  Items encontrados: {len(items) if items else 0}")
                    if items:
                        for i, item in enumerate(items):
                            print(f"    Item {i}: {item}")
                else:
                    print("  ❌ Campo 'items' não encontrado")
                
                # Verificar outros campos relacionados a produto
                product_fields = ['product', 'productName', 'title', 'name', 'sku']
                for field in product_fields:
                    if field in order:
                        print(f"  {field}: {order[field]}")
                
                # Mostrar pedido completo
                print(f"\n📋 PEDIDO COMPLETO:")
                print(json.dumps(order, indent=2))
                
        else:
            print(f"❌ Erro: {response.text}")
            
    finally:
        driver.quit()

if __name__ == "__main__":
    test_api_complete()