import pytest
from app.services.ai_service import AIService


@pytest.fixture
def ai_service():
    return AIService()


class FakeOpenAIResponse:
    class Message:
        content = '{"intent": "create_pix_charge", "confidence": 0.95, "entities": {"amount": 150.0, "customer_name": "João", "description": "serviço do site"}, "response_suggestion": "Ok"}'

    def __init__(self):
        self.choices = [self.Choice()]

    class Choice:
        def __init__(self):
            self.message = FakeOpenAIResponse.Message()


async def fake_chat_completions_create(*args, **kwargs):
    return FakeOpenAIResponse()


@pytest.mark.asyncio
async def test_classify_create_pix_charge(ai_service, monkeypatch):
    monkeypatch.setattr(ai_service.client.chat.completions, "create", fake_chat_completions_create)
    result = await ai_service.classify_intent("Gere uma cobrança de R$ 150 para João referente ao serviço do site")
    assert result["intent"] == "create_pix_charge"
    assert result["entities"]["amount"] == 150.0
    assert result["entities"]["customer_name"] == "João"


def test_detect_confirmation_confirms(ai_service):
    assert ai_service.detect_confirmation("sim") == "confirm_pending_action"
    assert ai_service.detect_confirmation("confirmo") == "confirm_pending_action"
    assert ai_service.detect_confirmation("pode gerar") == "confirm_pending_action"
    assert ai_service.detect_confirmation("gera a cobrança") == "confirm_pending_action"


def test_detect_confirmation_cancels(ai_service):
    assert ai_service.detect_confirmation("não") == "cancel_pending_action"
    assert ai_service.detect_confirmation("cancela") == "cancel_pending_action"
    assert ai_service.detect_confirmation("deixa pra lá") == "cancel_pending_action"
    assert ai_service.detect_confirmation("nao quero") == "cancel_pending_action"


def test_detect_confirmation_unknown(ai_service):
    assert ai_service.detect_confirmation("talvez amanhã") is None
    assert ai_service.detect_confirmation("") is None


def test_extract_charge_entities(ai_service):
    entities = ai_service.extract_charge_entities(
        "Gere uma cobrança de R$ 150 para João referente ao serviço do site"
    )
    assert entities["amount"] == 150.0
    assert entities["customer_name"] == "João"
    assert "serviço do site" in entities["description"]


def test_extract_charge_entities_with_phone(ai_service):
    entities = ai_service.extract_charge_entities(
        "Cobrar R$ 200 para Maria (11999999999)"
    )
    assert entities["amount"] == 200.0
    assert entities["customer_name"] == "Maria"
    assert entities["customer_phone"] == "11999999999"
