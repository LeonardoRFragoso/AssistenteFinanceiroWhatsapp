"""
Fake DDA provider — Sprint 17.

Generates realistic fake boletos/bills for demo and sandbox.
No real DDA access, no real API calls, no real bank credentials.
All data is marked is_demo_data=True.
"""
import random
import hashlib
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional


FAKE_BENEFICIARIES = [
    {"name": "Light Energia", "document_masked": "***.***.123-**", "category": "Energia", "bill_type": "utility"},
    {"name": "Águas do Rio", "document_masked": "***.***.456-**", "category": "Água", "bill_type": "utility"},
    {"name": "Vivo Empresas", "document_masked": "***.***.789-**", "category": "Telecomunicações", "bill_type": "service"},
    {"name": "Claro", "document_masked": "***.***.012-**", "category": "Telecomunicações", "bill_type": "service"},
    {"name": "MEI DAS", "document_masked": "**.***.345/0001-**", "category": "Impostos", "bill_type": "tax"},
    {"name": "Aluguel Escritório", "document_masked": "***.***.678-**", "category": "Aluguel", "bill_type": "rent"},
    {"name": "Contabilidade Express", "document_masked": "**.***.901/0001-**", "category": "Serviços", "bill_type": "service"},
    {"name": "Fornecedor XPTO", "document_masked": "**.***.234/0001-**", "category": "Fornecedores", "bill_type": "service"},
    {"name": "Internet Fibra Telecom", "document_masked": "***.***.567-**", "category": "Internet", "bill_type": "service"},
    {"name": "Software SaaS Pro", "document_masked": "**.***.890/0001-**", "category": "Software", "bill_type": "subscription"},
    {"name": "NEX Telecom", "document_masked": "***.***.111-**", "category": "Telecomunicações", "bill_type": "service"},
    {"name": "Limpeza Express", "document_masked": "**.***.222/0001-**", "category": "Serviços", "bill_type": "service"},
    {"name": "Seguro Empresarial BR", "document_masked": "**.***.333/0001-**", "category": "Seguros", "bill_type": "service"},
    {"name": "GNV Combustível", "document_masked": "***.***.444-**", "category": "Combustível", "bill_type": "utility"},
    {"name": "Mensalidade Contador", "document_masked": "***.***.555-**", "category": "Contabilidade", "bill_type": "service"},
]


def _fake_digitable_line() -> str:
    """Generate a fake digitable line (47 digits). NOT a real valid boleto line."""
    segments = []
    for _ in range(4):
        seg = "".join(random.choices("0123456789", k=11))
        segments.append(seg)
    return ".".join(segments[:3]) + " " + segments[3]


def _fake_barcode() -> str:
    """Generate a fake barcode (44 digits). NOT a real valid boleto barcode."""
    return "".join(random.choices("0123456789", k=44))


class FakeDDAProvider:
    """Fake DDA provider that generates demo boletos/bills."""

    def sync_bills(self, organization_id: int, user_id: int) -> list[dict]:
        """Generate fake bills for an organization."""
        return self.generate_demo_bills(organization_id, user_id)

    def generate_demo_bills(self, organization_id: int, user_id: int) -> list[dict]:
        """Generate 8-15 fake bills with varied due dates and statuses."""
        # Seed with org_id for deterministic/idempotent generation
        rng = random.Random(organization_id)
        count = rng.randint(8, 15)
        today = date.today()
        bills = []

        for i in range(count):
            beneficiary = rng.choice(FAKE_BENEFICIARIES)
            # Deterministic provider_bill_id for idempotency
            seed = f"{organization_id}:{beneficiary['name']}:{i}"
            bill_hash = hashlib.md5(seed.encode()).hexdigest()[:12]
            provider_bill_id = f"fake_dda_{bill_hash}"

            # Vary due dates: past, today, and future
            offset_days = rng.choice(
                [-15, -10, -7, -3, -1, 0, 0, 1, 2, 3, 5, 7, 10, 14, 21, 30]
            )
            due_date = today + timedelta(days=offset_days)

            # Determine status based on due date
            if offset_days < 0:
                status = "overdue"
            elif offset_days == 0:
                status = "due_today"
            else:
                status = "pending"

            # Some bills are already paid or ignored
            if rng.random() < 0.1:
                status = "paid_manual"
            elif rng.random() < 0.05:
                status = "ignored"

            amount = Decimal(str(round(rng.uniform(45.00, 2500.00), 2)))

            risk = "low"
            if amount > 1000:
                risk = "medium"
            if amount > 2000 and offset_days < 0:
                risk = "high"

            bill = {
                "organization_id": organization_id,
                "user_id": user_id,
                "provider_name": "fake",
                "provider_bill_id": provider_bill_id,
                "source": "fake_dda",
                "title": f"{beneficiary['name']} — {beneficiary['category']}",
                "beneficiary_name": beneficiary["name"],
                "beneficiary_document_masked": beneficiary["document_masked"],
                "payer_name": "Empresa Demo LTDA",
                "amount": str(amount),
                "currency": "BRL",
                "due_date": due_date.isoformat(),
                "issue_date": (due_date - timedelta(days=rng.randint(10, 30))).isoformat(),
                "barcode": _fake_barcode(),
                "digitable_line": _fake_digitable_line(),
                "bill_type": beneficiary["bill_type"],
                "category": beneficiary["category"],
                "status": status,
                "risk_level": risk,
                "is_demo_data": True,
                "raw_data_sanitized": {
                    "demo": True,
                    "provider": "fake_dda",
                    "note": "This is fake/demo data. Not a real boleto.",
                },
            }
            bills.append(bill)

        return bills

    def list_bills(self, organization_id: int) -> list[dict]:
        """List bills — in fake mode, this is a no-op (data is in DB)."""
        return []

    def get_bill(self, organization_id: int, bill_id: str) -> Optional[dict]:
        """Get a specific bill — in fake mode, this is a no-op."""
        return None
