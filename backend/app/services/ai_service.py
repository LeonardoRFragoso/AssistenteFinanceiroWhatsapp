from openai import AsyncOpenAI
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import re
from app.core.config import settings
from app.core.logging import logger


class AIService:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=30.0  # 30 segundos
        )
        self.model = settings.OPENAI_MODEL
    
    async def classify_intent(self, message: str, context: str = "") -> Dict[str, Any]:
        today = datetime.now().strftime('%Y-%m-%d')
        system_prompt = f"""Você é um assistente financeiro inteligente via WhatsApp.
Sua função é classificar a intenção do usuário e extrair informações relevantes.

INTENTS POSSÍVEIS:
- register_expense: Usuário quer registrar uma despesa
- register_income: Usuário quer registrar uma receita
- create_reminder: Usuário quer criar um lembrete/compromisso
- financial_report: Usuário quer ver relatórios, saldo, resumo financeiro
- list_transactions: Usuário quer ver lista de transações
- create_pix_charge: Usuário quer criar uma cobrança/pix/link de pagamento para outra pessoa
- confirm_pending_action: Usuário confirma uma ação pendente (ex: "confirmo", "sim", "pode gerar", "pode criar")
- cancel_pending_action: Usuário cancela uma ação pendente (ex: "cancela", "não", "deixa pra lá", "desiste")
- list_charges: Usuário quer listar cobranças criadas
- list_pending_charges: Usuário quer listar apenas cobranças pendentes
- list_paid_charges: Usuário quer listar apenas cobranças pagas
- check_charge_status: Usuário quer saber se uma cobrança específica foi paga
- cancel_charge: Usuário quer cancelar uma cobrança já criada (ex: "cancela a cobrança do João", "cancela a última cobrança")
- send_charge_link: Usuário quer enviar o link de pagamento para o cliente (ex: "envia o link para o cliente", "manda o link para ele", "sim, envia")
- help: Usuário precisa de ajuda ou não entendeu

EXTRAÇÃO DE ENTIDADES:
Para cobranças (create_pix_charge), extraia:
- amount (valor numérico, obrigatório)
- customer_name (nome do cliente devedor, obrigatório)
- customer_phone (telefone do cliente, se informado)
- description (descrição do serviço/produto, se informado)
- due_date (data de vencimento no formato YYYY-MM-DD, se informado; se não informado, deixe null)

Para despesas/receitas, extraia:
- amount (valor numérico)
- category (categoria como: alimentação, transporte, saúde, lazer, salário, freelance, etc)
- description (descrição opcional)
- payment_method (método de pagamento, valores possíveis: conta_corrente, cartao_credito, cartao_debito, pix, dinheiro, outros)
  Exemplos de detecção: "no cartão", "no crédito", "cartão de crédito" = cartao_credito; "no débito" = cartao_debito; "pix" = pix; "dinheiro", "espécie" = dinheiro; "conta", "transferência", "Nubank", "banco" = conta_corrente; se não mencionado, use conta_corrente
- cash_withdrawal (boolean, apenas quando payment_method=dinheiro): true se o usuário mencionar que sacou da conta, saque, caixa eletrônico, ATM. false se pagou com dinheiro que já tinha em mãos. Se não mencionado, use false.
- date (data no formato YYYY-MM-DD, se não especificada use a data de HOJE que é {today})

REGRAS DE IMPACTO NO SALDO DA CONTA CORRENTE:
- conta_corrente: altera saldo diretamente
- cartao_credito: NAO altera saldo da conta corrente (vai para fatura)
- cartao_debito: altera saldo diretamente
- pix: altera saldo diretamente
- dinheiro: só altera saldo se for saque da conta (cash_withdrawal=true)

Para lembretes, extraia:
- title (título do lembrete)
- due_date (data e hora no formato YYYY-MM-DD HH:MM:SS)

Para relatórios, extraia:
- period (hoje, semana, mês, ano, ou datas específicas)
- start_date e end_date se especificado

Para cancel_charge, extraia:
- customer_name (nome do cliente mencionado, se houver)
- amount (valor mencionado, se houver)
- reference: "latest" se o usuário disse "última cobrança", ou null

IMPORTANTE:
- Entenda português informal e gírias
- Valores podem estar como "50 reais", "R$ 50", "cinquenta reais"
- Datas podem ser "hoje", "amanhã", "segunda", "próxima semana"
- Seja tolerante com erros de digitação

Responda APENAS com JSON válido no formato:
{{
    "intent": "nome_do_intent",
    "confidence": 0.95,
    "entities": {{
        "campo1": "valor1",
        "campo2": "valor2"
    }},
    "response_suggestion": "Sugestão de resposta amigável para o usuário"
}}"""

        user_prompt = f"""Contexto da conversa:
{context if context else "Nenhum contexto anterior"}

Mensagem atual do usuário:
{message}

Classifique a intenção e extraia as entidades."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"AI Classification: {result['intent']} (confidence: {result.get('confidence', 0)})")
            return result
            
        except Exception as e:
            logger.error(f"Error in AI classification: {str(e)}")
            return {
                "intent": "help",
                "confidence": 0.0,
                "entities": {},
                "response_suggestion": "Desculpe, não entendi. Pode reformular?"
            }
    
    def detect_confirmation(self, message: str) -> Optional[str]:
        """Local, fast-path detection for confirmation/cancellation messages."""
        text = message.lower().strip()
        confirmation_words = ["confirmo", "confirma", "sim", "pode gerar", "pode criar", "gera", "cria", "fechar", "fecha"]
        cancellation_words = ["cancela", "cancelar", "não", "nao", "deixa pra lá", "deixa para la", "desiste", "não quero", "nao quero"]

        for word in cancellation_words:
            if word in text:
                return "cancel_pending_action"
        for word in confirmation_words:
            if word in text:
                return "confirm_pending_action"
        return None

    def extract_charge_entities(self, message: str) -> Dict[str, Any]:
        """Fallback local extraction for charge entities."""
        entities = {}
        amount = self._extract_amount(message)
        if amount:
            entities["amount"] = amount

        # Simple customer name extraction: look for "para" / "pra" / "do" / "da"
        # followed by a capitalized name. This is intentionally heuristic.
        name_match = re.search(r'(?:para|pra|pro|do|da)\s+([A-ZÀ-ÿ][a-zà-ÿ]+(?:\s+[A-ZÀ-ÿ][a-zà-ÿ]+)?)', message)
        if name_match:
            entities["customer_name"] = name_match.group(1).strip()

        # Description: common patterns after "referente", "de" or "por"
        # Avoid capturing just a numeric value (e.g., "R$ 150").
        desc_match = re.search(
            r'(?:referente|referente a|referente ao|de|do|da|por)\s+((?:(?!\bR\$\b|\d{1,3}(?:\.\d{3})*,\d{2})\S+\s?)+?)(?:\s+(?:para|pra|pro|vencimento|vence|até|ate|cliente)\s+|$)',
            message,
            re.IGNORECASE
        )
        if desc_match:
            entities["description"] = desc_match.group(1).strip()[:1000]

        phone_match = re.search(r'(?:\+?55\s?)?\(?\d{2}\)?\s?\d{4,5}-?\d{4}', message)
        if phone_match:
            phone = phone_match.group(0).strip()
            phone = re.sub(r'[\(\)\s\-]', '', phone)
            if phone.startswith('55'):
                phone = phone[2:]
            entities["customer_phone"] = phone

        return entities

    async def generate_response(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: str = "",
        additional_data: Optional[Dict[str, Any]] = None
    ) -> str:
        system_prompt = """Você é um assistente financeiro amigável e profissional.
Gere respostas naturais, claras e objetivas em português brasileiro.
Use emojis quando apropriado para deixar a conversa mais amigável.
Seja conciso mas informativo."""

        user_prompt = f"""Intent: {intent}
Entidades extraídas: {json.dumps(entities, ensure_ascii=False)}
Dados adicionais: {json.dumps(additional_data or {}, ensure_ascii=False)}
Contexto: {context}

Gere uma resposta apropriada para o usuário."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=300
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return "Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente."
    
    async def extract_entities(self, message: str, intent: str) -> Dict[str, Any]:
        entities = {}
        message_lower = message.lower()
        
        if intent in ["register_expense", "register_income"]:
            amount = self._extract_amount(message)
            if amount:
                entities["amount"] = amount
            
            category = self._extract_category(message, intent)
            if category:
                entities["category"] = category
            
            entities["description"] = message[:200]
            entities["date"] = datetime.now().strftime("%Y-%m-%d")
        
        elif intent == "create_reminder":
            entities["title"] = message[:255]
            entities["due_date"] = self._extract_date(message)
        
        return entities
    
    def _extract_amount(self, text: str) -> Optional[float]:
        patterns = [
            r'R\$\s*(\d+(?:[.,]\d{2})?)',
            r'(\d+(?:[.,]\d{2})?)\s*reais?',
            r'(\d+(?:[.,]\d{2})?)\s*r\$',
            r'(\d+(?:[.,]\d{2})?)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    def _extract_category(self, text: str, intent: str) -> str:
        text_lower = text.lower()
        
        expense_categories = {
            "alimentação": ["comida", "almoço", "jantar", "lanche", "restaurante", "mercado", "supermercado"],
            "transporte": ["uber", "taxi", "ônibus", "metrô", "gasolina", "combustível", "estacionamento"],
            "saúde": ["médico", "remédio", "farmácia", "hospital", "consulta", "exame"],
            "lazer": ["cinema", "show", "festa", "viagem", "diversão", "entretenimento"],
            "educação": ["curso", "livro", "escola", "faculdade", "aula"],
            "moradia": ["aluguel", "condomínio", "luz", "água", "internet", "gás"],
            "outros": []
        }
        
        income_categories = {
            "salário": ["salário", "salario", "pagamento", "ordenado"],
            "freelance": ["freela", "freelance", "bico", "extra"],
            "investimento": ["investimento", "rendimento", "dividendo", "juros"],
            "outros": []
        }
        
        categories = expense_categories if intent == "register_expense" else income_categories
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        
        return "outros"
    
    def _extract_date(self, text: str) -> str:
        text_lower = text.lower()
        now = datetime.now()
        
        if "hoje" in text_lower:
            return now.strftime("%Y-%m-%d %H:%M:%S")
        elif "amanhã" in text_lower or "amanha" in text_lower:
            tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
            return tomorrow.strftime("%Y-%m-%d 09:00:00")
        
        return (now + timedelta(days=1)).strftime("%Y-%m-%d 09:00:00")


from datetime import timedelta
