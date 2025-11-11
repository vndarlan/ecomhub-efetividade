# Token Sync - Sincronização Automática

Sistema interno que mantém tokens do EcomHub sempre válidos através de renovação automática.

## Como Funciona

**Thread em background** executa a cada 2 minutos:
1. Faz login via Selenium
2. Obtém tokens frescos
3. Salva no banco SQLite (`/tmp/tokens.db` no Railway)
4. Tokens ficam disponíveis para consulta via API

## Configuração

Variáveis de ambiente obrigatórias:

```env
TOKEN_SYNC_ENABLED=true
ECOMHUB_EMAIL=seu-email@exemplo.com
ECOMHUB_PASSWORD=sua-senha
API_SECRET_KEY=sua-chave-secreta
```

## Estrutura

```
token_sync/
├── database.py         # SQLite para persistência
├── sync_service.py     # Lógica de obtenção de tokens
├── scheduler.py        # Agendamento a cada 2 minutos
├── config.py          # Configurações
├── token_validator.py  # Validação de tokens
└── notifier.py        # Envio para sistemas externos
```

## Tokens

- **Duração**: 3 minutos
- **Renovação**: A cada 2 minutos
- **Margem**: 1 minuto de segurança
- **Armazenamento**: SQLite em `/tmp/tokens.db` (Railway) ou `tokens.db` (local)

## Uso

Tokens são consumidos via endpoints da API principal:
- `GET /api/auth` - Retorna tokens válidos do banco
- `GET /api/auth/status` - Status do sistema de sincronização

A thread inicia automaticamente com o servidor quando `TOKEN_SYNC_ENABLED=true`.