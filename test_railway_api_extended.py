"""
Script para obter pedido real via servidor Railway - período estendido
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

def test_multiple_periods():
    """Testa diferentes períodos até encontrar dados"""
    print("="*70)
    print("BUSCANDO PEDIDOS - TENTATIVAS COM DIFERENTES PERIODOS")
    print("="*70)

    # Tentar diferentes períodos
    periods = [
        ("Últimos 30 dias", 30),
        ("Últimos 60 dias", 60),
        ("Últimos 90 dias", 90),
    ]

    for period_name, days in periods:
        data_fim = datetime.now()
        data_inicio = data_fim - timedelta(days=days)
        data_inicio_str = data_inicio.strftime("%Y-%m-%d")
        data_fim_str = data_fim.strftime("%Y-%m-%d")

        print(f"\n{'='*70}")
        print(f"TENTATIVA: {period_name}")
        print(f"Periodo: {data_inicio_str} ate {data_fim_str}")
        print(f"Pais: TODOS")
        print(f"{'='*70}")

        payload = {
            "data_inicio": data_inicio_str,
            "data_fim": data_fim_str,
            "pais_id": "todos"
        }

        try:
            print(f"Chamando API...")
            response = requests.post(
                f"{RAILWAY_URL}{ENDPOINT}",
                json=payload,
                timeout=180
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()

                total = data.get('estatisticas', {}).get('total_registros', 0)
                print(f"Registros encontrados: {total}")

                if total > 0:
                    print(f"\nSUCESSO! Encontrados {total} pedidos!")

                    # Salvar
                    output_file = f"resposta_railway_{days}days.json"
                    with open(output_file, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)

                    print(f"Dados salvos em: {output_file}")

                    # Mostrar exemplo
                    if data['dados_processados'].get('visualizacao_total'):
                        print("\n" + "="*70)
                        print("EXEMPLO DE PEDIDO PROCESSADO:")
                        print("="*70)
                        exemplo = data['dados_processados']['visualizacao_total'][0]
                        print(json.dumps(exemplo, indent=2, ensure_ascii=False))

                    # Mostrar estatísticas
                    print("\n" + "="*70)
                    print("ESTATISTICAS:")
                    print("="*70)
                    for key, value in data.get('estatisticas', {}).items():
                        print(f"  {key}: {value}")

                    return data
                else:
                    print("Nenhum pedido encontrado neste periodo")

            else:
                print(f"Erro: {response.status_code}")
                print(f"Response: {response.text[:500]}")

        except Exception as e:
            print(f"Erro: {e}")

    print("\n" + "="*70)
    print("NENHUM PEDIDO ENCONTRADO EM NENHUM PERIODO")
    print("="*70)
    return None

if __name__ == "__main__":
    test_multiple_periods()
