#!/usr/bin/env python
"""
Seed demo data for PayFlow AI.

Creates a demo user with varied charges and transactions.
Idempotent: running multiple times will not duplicate data.

Usage:
    cd backend
    python scripts/seed_demo_data.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, AsyncSessionLocal
from app.services.demo_service import DemoService
from app.core.logging import logger


async def main():
    logger.info("Starting demo data seed...")
    async with AsyncSessionLocal() as db:
        service = DemoService(db)
        result = await service.seed_all()
        logger.info(f"Seed result: {result}")
        print(f"\n{'='*50}")
        print(f"  Demo Data Seed Complete")
        print(f"{'='*50}")
        print(f"  Status:           {result['status']}")
        print(f"  Message:          {result['message']}")
        print(f"  Demo user email:  {result['user_email']}")
        if "charges_created" in result:
            print(f"  Charges created:  {result['charges_created']}")
        if "transactions_created" in result:
            print(f"  Transactions:     {result['transactions_created']}")
        if "charges_count" in result:
            print(f"  Charges existing: {result['charges_count']}")
        if "transactions_count" in result:
            print(f"  Transactions:     {result['transactions_count']}")
        print(f"{'='*50}")
        print(f"\n  Login: {result['user_email']}")
        print(f"  Password: PayFlowDemo123")
        print(f"  (or use POST /auth/demo-login if ENABLE_DEMO_MODE=true)\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
