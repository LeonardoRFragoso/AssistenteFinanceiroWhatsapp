"""
Script para padronizar números de telefone no formato Twilio
Executa: python -m backend.fix_phone_numbers
"""
import asyncio
import re
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.logging import logger


def normalize_phone(phone: str) -> str:
    """Normaliza número de telefone para formato Twilio (+5521XXXXXXXXX)"""
    # Remove caracteres não numéricos exceto +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Se não tem +, assume Brasil e adiciona +55
    if not cleaned.startswith('+'):
        # Remove zero inicial do DDD se existir
        if cleaned.startswith('0'):
            cleaned = cleaned[1:]
        cleaned = f'+55{cleaned}'
    
    return cleaned


async def fix_phone_numbers():
    """Corrige todos os números de telefone no banco de dados"""
    async with AsyncSessionLocal() as db:
        try:
            # Buscar todos os usuários
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            updated_count = 0
            
            for user in users:
                original_phone = user.phone_number
                normalized_phone = normalize_phone(original_phone)
                
                if original_phone != normalized_phone:
                    logger.info(f"Updating user {user.id} ({user.email}): {original_phone} -> {normalized_phone}")
                    user.phone_number = normalized_phone
                    updated_count += 1
                else:
                    logger.info(f"User {user.id} ({user.email}) already has correct format: {original_phone}")
            
            if updated_count > 0:
                await db.commit()
                logger.info(f"✅ Successfully updated {updated_count} phone numbers")
            else:
                logger.info("✅ All phone numbers are already in correct format")
                
        except Exception as e:
            await db.rollback()
            logger.error(f"❌ Error fixing phone numbers: {str(e)}", exc_info=True)
            raise


if __name__ == "__main__":
    print("🔧 Starting phone number normalization...")
    asyncio.run(fix_phone_numbers())
    print("✅ Done!")
