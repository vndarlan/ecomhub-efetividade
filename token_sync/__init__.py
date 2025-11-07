"""
Token Sync Module - Sincronização Automática de Tokens EcomHub

Este módulo é responsável por:
- Obter tokens de autenticação via Selenium automaticamente
- Renovar tokens antes que expirem
- Enviar tokens atualizados para o Chegou Hub
- Manter compatibilidade com o endpoint /api/auth para uso via n8n

Autor: Claude AI Assistant
Data: 2024-11-07
"""

from .scheduler import token_scheduler, start_background_sync

__version__ = "1.0.0"
__all__ = ["token_scheduler", "start_background_sync"]