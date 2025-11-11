"""
Script simples que reusa as funções do main.py para obter um pedido real.
"""

import os
import sys
import json
from datetime import datetime, timedelta

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Importar funções do main.py
from main import create_driver, login_ecomhub, get_auth_cookies, extract_via_api

def main():
    print("="*70)
    print("CAPTURANDO PEDIDO REAL DA API ECOMHUB")
    print("="*70)

    driver = None

    try:
        # Datas: últimos 7 dias
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=7)
        data_inicio_str = data_inicio.strftime("%Y-%m-%d")
        data_fim_str = data_fim.strftime("%Y-%m-%d")

        print(f"\nPeriodo: {data_inicio_str} ate {data_fim_str}")
        print("Pais: Espanha (164)")
        print("\nAbrindo navegador...")

        # Criar driver
        headless = os.getenv("ENVIRONMENT") != "local"
        driver = create_driver(headless=headless)

        print("Fazendo login...")
        login_ecomhub(driver)

        print("Obtendo dados da API...")
        orders_data = extract_via_api(driver, data_inicio_str, data_fim_str, "164")

        if orders_data and len(orders_data) > 0:
            # Pegar apenas o primeiro pedido
            order = orders_data[0]

            # Salvar em arquivo
            output_file = "pedido_exemplo.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(order, f, indent=2, ensure_ascii=False)

            print(f"\nSUCESSO! Pedido salvo em: {output_file}")
            print(f"Total de pedidos encontrados: {len(orders_data)}")

            # Imprimir resumo
            print("\n" + "="*70)
            print("RESUMO DO PEDIDO")
            print("="*70)
            print(f"ID: {order.get('id')}")
            print(f"Numero: {order.get('shopifyOrderNumber')}")
            print(f"Status: {order.get('status')}")
            print(f"Data: {order.get('date')}")
            print(f"Pais: {order.get('shippingCountry')}")
            print(f"Cliente: {order.get('customerName')}")
            print(f"Preco: {order.get('price')}")

            if order.get('ordersItems') and len(order.get('ordersItems')) > 0:
                item = order['ordersItems'][0]
                product_name = item.get('productsVariants', {}).get('products', {}).get('name', 'N/A')
                print(f"Produto: {product_name}")

            # Contar campos
            print(f"\nTotal de campos no nivel raiz: {len(order.keys())}")
            print(f"Campos: {', '.join(sorted(order.keys())[:15])}...")

            # Primeiras linhas do JSON
            print("\n" + "="*70)
            print("PRIMEIRAS 100 LINHAS DO JSON:")
            print("="*70)
            json_str = json.dumps(order, indent=2, ensure_ascii=False)
            lines = json_str.split('\n')
            for line in lines[:100]:
                print(line)

            if len(lines) > 100:
                print(f"\n... (mais {len(lines) - 100} linhas)")
                print(f"\nVeja o arquivo {output_file} para o JSON completo")

        else:
            print("\nNenhum pedido encontrado no periodo")

    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if driver:
            print("\nFechando navegador...")
            driver.quit()
            print("Pronto!")

if __name__ == "__main__":
    main()
