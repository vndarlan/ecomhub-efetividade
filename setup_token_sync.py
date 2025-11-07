#!/usr/bin/env python
"""
Script de configuração rápida para Token Sync.

Este script ajuda a configurar o sistema de sincronização de tokens
de forma interativa e fácil.

Uso: python setup_token_sync.py
"""

import os
import sys
from pathlib import Path

def print_header():
    """Exibe header do setup."""
    print("\n" + "=" * 60)
    print("⚙️  CONFIGURAÇÃO DO TOKEN SYNC - ECOMHUB")
    print("=" * 60)
    print("\n📌 INFORMAÇÃO IMPORTANTE:")
    print("   Os tokens do EcomHub duram apenas 3 MINUTOS!")
    print("   Este sistema renovará automaticamente a cada 2 minutos.")
    print("-" * 60)

def check_dependencies():
    """Verifica se as dependências estão instaladas."""
    print("\n🔍 Verificando dependências...")

    missing = []

    try:
        import apscheduler
        print("   ✅ APScheduler instalado")
    except ImportError:
        print("   ❌ APScheduler não instalado")
        missing.append("apscheduler")

    try:
        import httpx
        print("   ✅ httpx instalado")
    except ImportError:
        print("   ⚠️ httpx não instalado (opcional)")

    try:
        import dotenv
        print("   ✅ python-dotenv instalado")
    except ImportError:
        print("   ❌ python-dotenv não instalado")
        missing.append("python-dotenv")

    if missing:
        print(f"\n❌ Dependências faltando: {', '.join(missing)}")
        print("   Execute: pip install -r requirements.txt")
        return False

    return True

def create_env_file():
    """Cria ou atualiza arquivo .env."""
    env_path = Path(".env")

    print("\n📝 Configurando arquivo .env...")

    # Ler configurações existentes
    existing_config = {}
    if env_path.exists():
        print("   ℹ️ Arquivo .env já existe - vamos atualizá-lo")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_config[key] = value

    # Configurações padrão
    config = {
        'ENVIRONMENT': existing_config.get('ENVIRONMENT', 'local'),
        'PORT': existing_config.get('PORT', '8001'),
    }

    print("\n🔐 CREDENCIAIS ECOMHUB")
    print("   (Pressione Enter para manter valores atuais)")

    # Email
    current_email = existing_config.get('ECOMHUB_EMAIL', '')
    if current_email:
        print(f"   Email atual: {current_email[:3]}***")
    email = input("   Email EcomHub: ").strip()
    if email:
        config['ECOMHUB_EMAIL'] = email
    elif current_email:
        config['ECOMHUB_EMAIL'] = current_email

    # Senha
    current_pass = existing_config.get('ECOMHUB_PASSWORD', '')
    if current_pass:
        print(f"   Senha atual: {'*' * len(current_pass)}")
    password = input("   Senha EcomHub: ").strip()
    if password:
        config['ECOMHUB_PASSWORD'] = password
    elif current_pass:
        config['ECOMHUB_PASSWORD'] = current_pass

    # Token Sync
    print("\n🔄 CONFIGURAÇÕES DE SINCRONIZAÇÃO")

    enable = input("   Habilitar sincronização automática? (S/n): ").strip().lower()
    config['TOKEN_SYNC_ENABLED'] = 'true' if enable != 'n' else 'false'

    # Duração fixa de 3 minutos
    config['TOKEN_DURATION_MINUTES'] = '3'
    config['SYNC_INTERVAL_MINUTES'] = '2'
    print("   ✅ Configurado: Tokens de 3 min, renovação a cada 2 min")

    # Chegou Hub
    print("\n🌐 INTEGRAÇÃO COM CHEGOU HUB")
    print("   (Deixe vazio se ainda não configurado)")

    webhook_url = input("   URL do Webhook: ").strip()
    if webhook_url:
        config['CHEGOU_HUB_WEBHOOK_URL'] = webhook_url

    api_key = input("   API Key: ").strip()
    if api_key:
        config['CHEGOU_HUB_API_KEY'] = api_key

    # Configurações avançadas
    print("\n⚙️ CONFIGURAÇÕES AVANÇADAS")
    use_defaults = input("   Usar valores padrão? (S/n): ").strip().lower()

    if use_defaults != 'n':
        config['MAX_RETRY_ATTEMPTS'] = '3'
        config['RETRY_DELAY_SECONDS'] = '5'
        config['VALIDATE_TOKENS_AFTER_FETCH'] = 'true'
        config['SYNC_ON_STARTUP'] = 'true'
        print("   ✅ Valores padrão aplicados")

    # Escrever arquivo
    print("\n💾 Salvando configurações...")

    with open(env_path, 'w') as f:
        f.write("# Configurações do Servidor\n")
        f.write(f"ENVIRONMENT={config.get('ENVIRONMENT', 'local')}\n")
        f.write(f"PORT={config.get('PORT', '8001')}\n")
        f.write("\n")

        f.write("# Credenciais EcomHub\n")
        if 'ECOMHUB_EMAIL' in config:
            f.write(f"ECOMHUB_EMAIL={config['ECOMHUB_EMAIL']}\n")
        if 'ECOMHUB_PASSWORD' in config:
            f.write(f"ECOMHUB_PASSWORD={config['ECOMHUB_PASSWORD']}\n")
        f.write("\n")

        f.write("# Token Sync - Configurações\n")
        f.write(f"TOKEN_SYNC_ENABLED={config.get('TOKEN_SYNC_ENABLED', 'false')}\n")
        f.write(f"TOKEN_DURATION_MINUTES={config.get('TOKEN_DURATION_MINUTES', '3')}\n")
        f.write(f"SYNC_INTERVAL_MINUTES={config.get('SYNC_INTERVAL_MINUTES', '2')}\n")
        f.write("\n")

        if 'CHEGOU_HUB_WEBHOOK_URL' in config:
            f.write("# Integração com Chegou Hub\n")
            f.write(f"CHEGOU_HUB_WEBHOOK_URL={config['CHEGOU_HUB_WEBHOOK_URL']}\n")
            if 'CHEGOU_HUB_API_KEY' in config:
                f.write(f"CHEGOU_HUB_API_KEY={config['CHEGOU_HUB_API_KEY']}\n")
            f.write("\n")

        if 'MAX_RETRY_ATTEMPTS' in config:
            f.write("# Configurações Avançadas\n")
            f.write(f"MAX_RETRY_ATTEMPTS={config['MAX_RETRY_ATTEMPTS']}\n")
            f.write(f"RETRY_DELAY_SECONDS={config['RETRY_DELAY_SECONDS']}\n")
            f.write(f"VALIDATE_TOKENS_AFTER_FETCH={config['VALIDATE_TOKENS_AFTER_FETCH']}\n")
            f.write(f"SYNC_ON_STARTUP={config['SYNC_ON_STARTUP']}\n")

    print("   ✅ Arquivo .env salvo com sucesso!")

    return config.get('TOKEN_SYNC_ENABLED') == 'true'

def test_configuration():
    """Testa a configuração."""
    print("\n🧪 Testando configuração...")

    try:
        # Importar e testar
        from dotenv import load_dotenv
        load_dotenv()

        # Verificar variáveis críticas
        email = os.getenv('ECOMHUB_EMAIL')
        password = os.getenv('ECOMHUB_PASSWORD')
        enabled = os.getenv('TOKEN_SYNC_ENABLED', 'false').lower() == 'true'

        if not email or not password:
            print("   ⚠️ Credenciais não configuradas")
            return False

        print(f"   ✅ Credenciais configuradas")
        print(f"   ✅ Sincronização: {'Habilitada' if enabled else 'Desabilitada'}")
        print(f"   ✅ Intervalo: 2 minutos")

        # Testar importação do módulo
        try:
            from token_sync import token_scheduler
            print("   ✅ Módulo token_sync carregado")
        except ImportError as e:
            print(f"   ❌ Erro ao carregar módulo: {e}")
            return False

        return True

    except Exception as e:
        print(f"   ❌ Erro: {e}")
        return False

def main():
    """Função principal do setup."""
    print_header()

    # Verificar dependências
    if not check_dependencies():
        print("\n❌ Por favor, instale as dependências primeiro.")
        sys.exit(1)

    # Configurar .env
    sync_enabled = create_env_file()

    # Testar configuração
    if test_configuration():
        print("\n" + "=" * 60)
        print("✅ CONFIGURAÇÃO CONCLUÍDA COM SUCESSO!")
        print("=" * 60)

        if sync_enabled:
            print("\n📌 PRÓXIMOS PASSOS:")
            print("   1. Execute: python main.py")
            print("   2. O Token Sync iniciará automaticamente")
            print("   3. Tokens serão renovados a cada 2 minutos")
        else:
            print("\n📌 Para habilitar a sincronização:")
            print("   1. Edite .env e mude TOKEN_SYNC_ENABLED=true")
            print("   2. Execute: python main.py")

        print("\n💡 DICAS:")
        print("   - Para testar isoladamente: python run_token_sync.py")
        print("   - Para verificar logs: tail -f token_sync.log")
        print("   - Endpoint /api/auth continua funcionando normalmente")

    else:
        print("\n⚠️ Configuração concluída mas com avisos.")
        print("   Verifique os erros acima.")

    print("\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Setup cancelado pelo usuário")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}")
        sys.exit(1)