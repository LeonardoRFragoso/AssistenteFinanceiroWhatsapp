#!/usr/bin/env python3
"""
Script para validar a configuração do ambiente.
Uso: python scripts/validate_environment.py
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir / "backend"))

def check_secret_key():
    """Verifica se SECRET_KEY está configurada adequadamente."""
    secret_key = os.getenv("SECRET_KEY", "")
    
    print("🔐 Verificando SECRET_KEY...")
    
    if not secret_key:
        print("   ❌ SECRET_KEY não está definida!")
        return False
    
    if secret_key == "your-secret-key-change-in-production":
        print("   ⚠️  SECRET_KEY está usando o valor padrão do exemplo!")
        print("   ⚠️  ALTERE para uma chave segura antes de usar em produção!")
        return False
    
    if len(secret_key) < 32:
        print(f"   ❌ SECRET_KEY muito curta ({len(secret_key)} caracteres)")
        print("   ⚠️  Mínimo recomendado: 32 caracteres")
        return False
    
    if len(secret_key) < 64:
        print(f"   ⚠️  SECRET_KEY tem {len(secret_key)} caracteres")
        print("   ⚠️  Recomendado: 64+ caracteres para máxima segurança")
        print("   ✅ Mas está aceitável para desenvolvimento")
        return True
    
    print(f"   ✅ SECRET_KEY configurada adequadamente ({len(secret_key)} caracteres)")
    return True

def check_database_url():
    """Verifica se DATABASE_URL está configurada."""
    db_url = os.getenv("DATABASE_URL", "")
    
    print("\n🗄️  Verificando DATABASE_URL...")
    
    if not db_url:
        print("   ❌ DATABASE_URL não está definida!")
        return False
    
    if "postgresql" not in db_url:
        print("   ⚠️  DATABASE_URL não parece ser PostgreSQL")
        return False
    
    print("   ✅ DATABASE_URL configurada")
    return True

def check_redis_url():
    """Verifica se REDIS_URL está configurada."""
    redis_url = os.getenv("REDIS_URL", "")
    
    print("\n📦 Verificando REDIS_URL...")
    
    if not redis_url:
        print("   ❌ REDIS_URL não está definida!")
        return False
    
    if "redis" not in redis_url:
        print("   ⚠️  REDIS_URL não parece ser válida")
        return False
    
    print("   ✅ REDIS_URL configurada")
    return True

def check_api_keys():
    """Verifica se as API keys essenciais estão configuradas."""
    print("\n🔑 Verificando API Keys...")
    
    checks = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", ""),
        "TWILIO_ACCOUNT_SID": os.getenv("TWILIO_ACCOUNT_SID", ""),
        "TWILIO_AUTH_TOKEN": os.getenv("TWILIO_AUTH_TOKEN", ""),
    }
    
    all_ok = True
    for key, value in checks.items():
        if not value or value.startswith("your_"):
            print(f"   ⚠️  {key} não configurada ou usando valor padrão")
            all_ok = False
        else:
            print(f"   ✅ {key} configurada")
    
    return all_ok

def check_env_file():
    """Verifica se o arquivo .env existe."""
    print("\n📄 Verificando arquivo .env...")
    
    env_file = root_dir / ".env"
    
    if not env_file.exists():
        print("   ❌ Arquivo .env não encontrado!")
        print("   ℹ️  Copie .env.example para .env e configure as variáveis")
        return False
    
    print("   ✅ Arquivo .env encontrado")
    return True

def main():
    """Executa todas as verificações."""
    print("=" * 80)
    print("VALIDAÇÃO DO AMBIENTE - Assistente Financeiro WhatsApp")
    print("=" * 80)
    
    # Tentar carregar .env se existir
    try:
        from dotenv import load_dotenv
        env_file = root_dir / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            print("\n✅ Arquivo .env carregado com sucesso\n")
    except ImportError:
        print("\n⚠️  python-dotenv não instalado, pulando carregamento do .env\n")
    
    results = []
    
    # Executar verificações
    results.append(("Arquivo .env", check_env_file()))
    results.append(("SECRET_KEY", check_secret_key()))
    results.append(("DATABASE_URL", check_database_url()))
    results.append(("REDIS_URL", check_redis_url()))
    results.append(("API Keys", check_api_keys()))
    
    # Resumo
    print("\n" + "=" * 80)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{check_name:.<50} {status}")
    
    print("=" * 80)
    print(f"Resultado: {passed}/{total} verificações passaram")
    print("=" * 80)
    
    if passed == total:
        print("\n🎉 Ambiente configurado corretamente!")
        return 0
    else:
        print("\n⚠️  Algumas verificações falharam. Revise a configuração.")
        print("\nPara corrigir:")
        print("1. Copie .env.example para .env: cp .env.example .env")
        print("2. Gere SECRET_KEY segura: python scripts/generate_secret_key.py")
        print("3. Configure as variáveis necessárias no arquivo .env")
        return 1

if __name__ == "__main__":
    sys.exit(main())
