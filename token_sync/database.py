"""
Módulo de banco de dados para armazenamento de tokens
Usa SQLite para persistência simples e eficiente
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
import logging
from typing import Optional, Dict

logger = logging.getLogger(__name__)

class TokenDatabase:
    def __init__(self, db_path: str = "tokens.db"):
        """Inicializa conexão com banco SQLite"""
        self.db_path = Path(db_path)
        self.init_database()

    def init_database(self):
        """Cria tabela de tokens se não existir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tokens (
                        id INTEGER PRIMARY KEY,
                        token TEXT,
                        e_token TEXT,
                        refresh_token TEXT,
                        cookies TEXT,
                        expires_at TEXT,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Garante que existe pelo menos um registro
                conn.execute("""
                    INSERT OR IGNORE INTO tokens (id, token, e_token, refresh_token)
                    VALUES (1, NULL, NULL, NULL)
                """)
                conn.commit()
                logger.info(f"✅ Banco de dados inicializado: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco: {e}")
            raise

    def save_tokens(self, token: str, e_token: str, refresh_token: str,
                   cookies: Optional[Dict] = None, expires_in: int = 180):
        """
        Salva ou atualiza tokens no banco

        Args:
            token: Token principal
            e_token: Token extra
            refresh_token: Token de refresh
            cookies: Dict com todos os cookies (opcional)
            expires_in: Tempo de expiração em segundos
        """
        try:
            expires_at = datetime.now().timestamp() + expires_in
            cookies_json = json.dumps(cookies) if cookies else None

            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tokens
                    SET token = ?,
                        e_token = ?,
                        refresh_token = ?,
                        cookies = ?,
                        expires_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """, (token, e_token, refresh_token, cookies_json, expires_at))
                conn.commit()

                logger.info("✅ Tokens salvos no banco de dados")
                return True
        except Exception as e:
            logger.error(f"❌ Erro ao salvar tokens: {e}")
            return False

    def get_tokens(self) -> Optional[Dict]:
        """
        Recupera tokens do banco

        Returns:
            Dict com tokens e metadados ou None se não houver
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT token, e_token, refresh_token, cookies,
                           expires_at, updated_at
                    FROM tokens
                    WHERE id = 1
                """)
                row = cursor.fetchone()

                if row and row['token']:
                    # Calcula tempo restante
                    expires_at = float(row['expires_at']) if row['expires_at'] else 0
                    now = datetime.now().timestamp()
                    time_remaining = max(0, int(expires_at - now))

                    return {
                        'token': row['token'],
                        'e_token': row['e_token'],
                        'refresh_token': row['refresh_token'],
                        'cookies': json.loads(row['cookies']) if row['cookies'] else None,
                        'expires_in': time_remaining,
                        'expires_at': datetime.fromtimestamp(expires_at).isoformat() if expires_at else None,
                        'updated_at': row['updated_at'],
                        'is_valid': time_remaining > 0
                    }
                return None
        except Exception as e:
            logger.error(f"❌ Erro ao recuperar tokens: {e}")
            return None

    def clear_tokens(self):
        """Limpa todos os tokens (útil para forçar novo login)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE tokens
                    SET token = NULL,
                        e_token = NULL,
                        refresh_token = NULL,
                        cookies = NULL,
                        expires_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """)
                conn.commit()
                logger.info("✅ Tokens limpos do banco")
                return True
        except Exception as e:
            logger.error(f"❌ Erro ao limpar tokens: {e}")
            return False

    def get_status(self) -> Dict:
        """Retorna status do sistema de tokens"""
        tokens = self.get_tokens()
        if tokens:
            return {
                'status': 'active' if tokens['is_valid'] else 'expired',
                'has_tokens': True,
                'expires_in': tokens['expires_in'],
                'last_update': tokens['updated_at']
            }
        return {
            'status': 'no_tokens',
            'has_tokens': False,
            'expires_in': 0,
            'last_update': None
        }

# Instância global (singleton)
_db_instance = None

def get_database() -> TokenDatabase:
    """Retorna instância singleton do banco"""
    global _db_instance
    if _db_instance is None:
        _db_instance = TokenDatabase()
    return _db_instance