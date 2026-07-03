"""
Fake Open Finance read provider — Sprint 16.

Generates realistic fake/demo financial data for development and testing.
NEVER connects to a real bank. All data is marked is_demo_data=True.

Security:
- No real API calls
- No real access tokens or refresh tokens
- No real bank connections
- All data is clearly fake/demo
- No payment initiation
"""
import uuid
from datetime import datetime, timezone, timedelta, date
from decimal import Decimal
from typing import Any, Optional
import random
import logging

logger = logging.getLogger(__name__)


_FAKE_INSTITUTIONS = [
    {"code": "nubank", "name": "Nubank"},
    {"code": "itau", "name": "Itaú Unibanco"},
    {"code": "bradesco", "name": "Bradesco"},
    {"code": "santander", "name": "Santander"},
    {"code": "inter", "name": "Banco Inter"},
]

_FAKE_MERCHANTS = [
    "Supermercado Extra", "Farmácia Pague Menos", "Posto Shell",
    "Amazon Brasil", "iFood", "Uber", "Netflix Brasil",
    "Mercado Livre", "Casas Bahia", "Magazine Luiza",
    "Padaria São João", "Academia Smart Fit", "Claro",
    "Vivo", "Algar Telecom", "Lojas Renner", "C&A",
    "Burger King", "McDonald's", "Spoleto",
    "Petz", "Cobasi", "Leroy Merlin", "Casa & Video",
    "Shopee Brasil", "Shein", "AliExpress",
]

_FAKE_CATEGORIES = [
    {"name": "Alimentação", "type": "expense", "color": "#FF6B6B", "icon": "🍔"},
    {"name": "Transporte", "type": "expense", "color": "#4ECDC4", "icon": "🚗"},
    {"name": "Moradia", "type": "expense", "color": "#45B7D1", "icon": "🏠"},
    {"name": "Saúde", "type": "expense", "color": "#96CEB4", "icon": "💊"},
    {"name": "Lazer", "type": "expense", "color": "#FFEAA7", "icon": "🎮"},
    {"name": "Educação", "type": "expense", "color": "#DDA0DD", "icon": "📚"},
    {"name": "Compras", "type": "expense", "color": "#98D8C8", "icon": "🛍️"},
    {"name": "Assinaturas", "type": "expense", "color": "#F7DC6F", "icon": "📱"},
    {"name": "Salário", "type": "income", "color": "#27AE60", "icon": "💰"},
    {"name": "Freelance", "type": "income", "color": "#2ECC71", "icon": "💼"},
    {"name": "Investimentos", "type": "income", "color": "#3498DB", "icon": "📈"},
    {"name": "Reembolso", "type": "income", "color": "#1ABC9C", "icon": "↩️"},
]

_FAKE_DESCRIPTIONS = {
    "Alimentação": ["Compra no supermercado", "Almoço", "Lanche", "Delivery de comida", "Café"],
    "Transporte": ["Combustível", "Uber", "Ônibus", "Estacionamento", "Pedágio"],
    "Moradia": ["Aluguel", "Conta de luz", "Conta de água", "Internet", "Gás"],
    "Saúde": ["Compra de medicamentos", "Consulta médica", "Exame", "Fisioterapia"],
    "Lazer": ["Cinema", "Streaming", "Jogo", "Show", "Parque"],
    "Educação": ["Curso online", "Livro", "Mensalidade", "Material escolar"],
    "Compras": ["Compra online", "Roupas", "Eletrônicos", "Casa"],
    "Assinaturas": ["Mensalidade streaming", "Software", "Academia", "Clube"],
    "Salário": ["Salário mensal", "Pagamento de salário"],
    "Freelance": ["Projeto freelance", "Consultoria", "Serviço prestado"],
    "Investimentos": ["Dividendos", "Rendimento poupança", "Rendimento CDB"],
    "Reembolso": ["Reembolso de despesa", "Estorno", "Devolução"],
}


def _random_amount(min_val: float, max_val: float) -> Decimal:
    val = round(random.uniform(min_val, max_val), 2)
    return Decimal(str(val))


def _generate_fake_accounts(org_id: int, consent_id: str) -> list[dict[str, Any]]:
    """Generate 2 fake connected accounts."""
    now = datetime.now(timezone.utc)
    accounts = []

    institutions = random.sample(_FAKE_INSTITUTIONS, 2)

    for i, inst in enumerate(institutions):
        balance_available = _random_amount(500, 15000)
        balance_current = balance_available + _random_amount(0, 2000)
        accounts.append({
            "external_account_id": f"fake_acc_{uuid.uuid4().hex[:12]}",
            "institution_name": inst["name"],
            "institution_code": inst["code"],
            "account_type": "checking" if i == 0 else "savings",
            "account_subtype": "personal",
            "account_number_masked": f"****{random.randint(1000, 9999)}",
            "currency": "BRL",
            "balance_available": balance_available,
            "balance_current": balance_current,
            "balance_updated_at": now.isoformat(),
            "status": "active",
            "is_demo_data": True,
            "consent_id": consent_id,
            "provider_name": "fake",
        })

    return accounts


def _generate_fake_transactions(accounts: list[dict[str, Any]], count: int = 30) -> list[dict[str, Any]]:
    """Generate 20-40 fake bank transactions across accounts."""
    transactions = []
    now = datetime.now(timezone.utc)
    num_tx = random.randint(20, 40) if count == 30 else count

    for _ in range(num_tx):
        account = random.choice(accounts)
        category = random.choice(_FAKE_CATEGORIES)
        merchant = random.choice(_FAKE_MERCHANTS)
        descriptions = _FAKE_DESCRIPTIONS.get(category["name"], ["Transação"])
        description = random.choice(descriptions)

        days_ago = random.randint(0, 45)
        tx_date = now - timedelta(days=days_ago, hours=random.randint(0, 23))

        if category["type"] == "income":
            amount = _random_amount(100, 8000)
            tx_type = "credit"
        else:
            amount = _random_amount(10, 800)
            amount = -abs(amount)
            tx_type = "debit"

        transactions.append({
            "external_transaction_id": f"fake_tx_{uuid.uuid4().hex[:12]}",
            "transaction_type": tx_type,
            "amount": amount,
            "currency": "BRL",
            "description": description,
            "merchant_name": merchant,
            "category": category["name"],
            "subcategory": category["type"],
            "transaction_date": tx_date.date().isoformat(),
            "posted_at": tx_date.isoformat(),
            "status": "posted",
            "is_demo_data": True,
            "provider_name": "fake",
            "external_account_id": account["external_account_id"],
            "raw_data_sanitized": {
                "sandbox": True,
                "demo": True,
                "category_type": category["type"],
            },
        })

    transactions.sort(key=lambda t: t["transaction_date"], reverse=True)
    return transactions


def get_fake_categories() -> list[dict[str, Any]]:
    """Return the list of fake financial categories."""
    return [
        {
            "name": c["name"],
            "type": c["type"],
            "color": c["color"],
            "icon": c["icon"],
            "is_system": True,
        }
        for c in _FAKE_CATEGORIES
    ]


class FakeOpenFinanceReadProvider:
    """
    Fake Open Finance read provider for Sprint 16.

    All methods return fake/demo data. No real bank connections.
    All data is marked is_demo_data=True.
    """

    @property
    def name(self) -> str:
        return "fake"

    @property
    def is_real(self) -> bool:
        return False

    async def create_consent(self, org_id: int, user_id: int, institution_id: str = "fake_bank") -> dict[str, Any]:
        """Create a fake Open Finance consent."""
        consent_id = f"fake_consent_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        logger.info(f"Fake Open Finance consent created for org {org_id}: {consent_id}")
        return {
            "consent_id": consent_id,
            "status": "authorized",
            "authorization_url": f"https://fake.openfinance.payflow.ai/authorize/{consent_id}",
            "expires_at": (now + timedelta(days=365)).isoformat(),
            "institution_id": institution_id,
            "is_demo": True,
        }

    async def list_accounts(self, org_id: int, consent_id: str) -> list[dict[str, Any]]:
        """List fake connected accounts."""
        accounts = _generate_fake_accounts(org_id, consent_id)
        logger.info(f"Fake Open Finance: {len(accounts)} accounts for org {org_id}")
        return accounts

    async def get_balances(self, account_id: str) -> dict[str, Any]:
        """Get fake account balances."""
        return {
            "account_id": account_id,
            "balance_available": _random_amount(500, 15000),
            "balance_current": _random_amount(500, 17000),
            "currency": "BRL",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "is_demo": True,
        }

    async def list_transactions(self, account_id: str, start_date: Optional[date] = None,
                                 end_date: Optional[date] = None) -> list[dict[str, Any]]:
        """List fake transactions for an account."""
        fake_account = {"external_account_id": account_id}
        transactions = _generate_fake_transactions([fake_account], count=20)
        logger.info(f"Fake Open Finance: {len(transactions)} transactions for account {account_id}")
        return transactions

    async def sync_transactions(self, org_id: int, accounts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Sync fake transactions across all accounts."""
        all_transactions = _generate_fake_transactions(accounts, count=30)
        logger.info(f"Fake Open Finance: synced {len(all_transactions)} transactions for org {org_id}")
        return all_transactions

    async def revoke_consent(self, consent_id: str) -> bool:
        """Revoke a fake consent."""
        logger.info(f"Fake Open Finance consent revoked: {consent_id}")
        return True

    def get_categories(self) -> list[dict[str, Any]]:
        """Return fake financial categories."""
        return get_fake_categories()
