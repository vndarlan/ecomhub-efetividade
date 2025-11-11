"""
Script para obter pedido real via servidor Railway
"""

import sys
import json
import requests
from datetime import datetime, timedelta

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# URL do servidor Railway
RAILWAY_URL = "https://ecomhub-selenium-production.up.railway.app"
ENDPOINT = "/api/processar-ecomhub/"

def get_order_from_railway():
    """Faz requisição para o servidor Railway e obtém pedidos"""
    print("="*70)
    print("OBTENDO PEDIDO REAL VIA RAILWAY")
    print("="*70)

    # Datas: últimos 7 dias
    data_fim = datetime.now()
    data_inicio = data_fim - timedelta(days=7)
    data_inicio_str = data_inicio.strftime("%Y-%m-%d")
    data_fim_str = data_fim.strftime("%Y-%m-%d")

    print(f"\nPeriodo: {data_inicio_str} ate {data_fim_str}")
    print(f"Pais: Espanha (164)")
    print(f"\nChamando: {RAILWAY_URL}{ENDPOINT}")

    # Dados da requisição
    payload = {
        "data_inicio": data_inicio_str,
        "data_fim": data_fim_str,
        "pais_id": "164"
    }

    try:
        # Fazer requisição
        response = requests.post(
            f"{RAILWAY_URL}{ENDPOINT}",
            json=payload,
            timeout=180  # 3 minutos
        )

        print(f"\nStatus Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\nResposta recebida com sucesso!")

            # A resposta contém dados processados, não o pedido raw da API
            # Vamos salvar mesmo assim para análise
            output_file = "resposta_railway.json"
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            print(f"Dados salvos em: {output_file}")

            # Mostrar estrutura
            print("\n" + "="*70)
            print("ESTRUTURA DA RESPOSTA")
            print("="*70)
            print(f"Status: {data.get('status')}")
            print(f"Message: {data.get('message')}")

            if 'dados_processados' in data:
                print(f"\nDados processados disponiveis:")
                print(f"  - visualizacao_total: {len(data['dados_processados'].get('visualizacao_total', []))} registros")
                print(f"  - visualizacao_otimizada: {len(data['dados_processados'].get('visualizacao_otimizada', []))} registros")

                # Mostrar um exemplo
                if data['dados_processados'].get('visualizacao_total'):
                    print("\nExemplo de registro (visualizacao_total):")
                    exemplo = data['dados_processados']['visualizacao_total'][0]
                    print(json.dumps(exemplo, indent=2, ensure_ascii=False))

            if 'estatisticas' in data:
                print(f"\nEstatisticas:")
                for key, value in data['estatisticas'].items():
                    print(f"  - {key}: {value}")

            print("\n" + "="*70)
            print("NOTA: Esta resposta contém dados PROCESSADOS.")
            print("Para obter o pedido RAW da API EcomHub, precisamos")
            print("acessar diretamente a API com os tokens.")
            print("="*70)

            return data

        else:
            print(f"Erro: {response.status_code}")
            print(f"Response: {response.text}")
            return None

    except Exception as e:
        print(f"\nErro: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    get_order_from_railway()
