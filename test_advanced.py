import requests
import time
import json

def test_server_connection():
    """Testa se o servidor está rodando"""
    try:
        print("🔍 Testando conexão...")
        response = requests.get("http://localhost:8001", timeout=5)
        if response.status_code == 200:
            print("✅ Servidor rodando!")
            return True
        else:
            print(f"❌ Status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Servidor não rodando na porta 8001")
        print("💡 Execute: python main.py")
        return False

def test_api_automation():
    """Testa automação via API"""
    print("\n🚀 Testando automação híbrida (Selenium + API)...")
    
    data = {
        "data_inicio": "2025-07-14", 
        "data_fim": "2025-07-17",
        "pais_id": "164"
    }
    
    print(f"📋 Dados: {json.dumps(data, indent=2)}")
    print("⏳ Processando (login + API)...")
    
    try:
        response = requests.post(
            "http://localhost:8001/api/processar-ecomhub/", 
            json=data,
            timeout=300
        )
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCESSO!")
            print(f"Status: {result['status']}")
            print(f"Mensagem: {result['message']}")
            
            dados = result.get('dados_processados', [])
            stats = result.get('estatisticas', {})
            
            print(f"\n📊 Estatísticas:")
            print(f"   Total: {stats.get('total_registros', 0)} pedidos")
            print(f"   Produtos: {stats.get('total_produtos', 0)}")
            
            if dados:
                print(f"\n📋 Primeiros 3 produtos:")
                for i, item in enumerate(dados[:3]):
                    produto = item.get('Produto', 'N/A')[:30]
                    efetividade = item.get('Efetividade', 'N/A')
                    print(f"   {i+1}. {produto} - {efetividade}")
            
            return True
        else:
            print(f"❌ Erro {response.status_code}")
            try:
                error = response.json()
                print(f"Detalhes: {error}")
            except:
                print(f"Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ Timeout! Demorou mais de 5 minutos")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    print("🤖 TESTE AUTOMAÇÃO ECOMHUB - API HÍBRIDA")
    print("=" * 50)
    
    if not test_server_connection():
        return
    
    print("=" * 50)
    success = test_api_automation()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TESTE PASSOU!")
        print("✅ API híbrida funcionando")
    else:
        print("❌ TESTE FALHOU")

if __name__ == "__main__":
    main()