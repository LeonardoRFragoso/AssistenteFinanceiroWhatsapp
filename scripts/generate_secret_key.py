#!/usr/bin/env python3
"""
Script para gerar SECRET_KEY segura para a aplicação.
Uso: python scripts/generate_secret_key.py
"""
import secrets

def generate_secret_key(length: int = 64) -> str:
    """
    Gera uma SECRET_KEY segura usando secrets.token_urlsafe.
    
    Args:
        length: Número de bytes para gerar (padrão: 64)
        
    Returns:
        String segura codificada em base64 URL-safe
    """
    return secrets.token_urlsafe(length)

if __name__ == "__main__":
    print("=" * 80)
    print("GERADOR DE SECRET_KEY SEGURA")
    print("=" * 80)
    print()
    
    # Gerar chave de 64 bytes (recomendado)
    secret_key = generate_secret_key(64)
    
    print(f"SECRET_KEY gerada ({len(secret_key)} caracteres):")
    print()
    print(secret_key)
    print()
    print("=" * 80)
    print("INSTRUÇÕES:")
    print("=" * 80)
    print("1. Copie a chave acima")
    print("2. Adicione ao arquivo .env:")
    print(f"   SECRET_KEY={secret_key}")
    print("3. NUNCA compartilhe esta chave ou faça commit dela no Git")
    print("4. Use uma chave diferente para cada ambiente (dev, staging, prod)")
    print("=" * 80)
