from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.core.database import get_db
from app.core.config import settings
from app.core.logging import logger
from app.integrations.twilio_whatsapp import TwilioWhatsAppService
from app.services.ai_service import AIService
from app.services.transaction_service import TransactionService
from app.services.reminder_service import ReminderService
from app.services.report_service import ReportService
from app.services.charge_service import ChargeService
from app.services.pending_action_service import PendingActionService
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.transaction import TransactionCreate
from app.schemas.reminder import ReminderCreate
from app.schemas.conversation import ConversationLogCreate
from app.models.conversation_log import MessageRole
from app.models.transaction import TransactionType, PaymentMethod
from app.utils.rate_limiter import whatsapp_rate_limiter
from app.utils.webhook_rate_limiter import webhook_rate_limiter
from app.core.audit_logger import log_webhook_received
from app.services.plan_limit_service import PlanLimitService
from app.repositories.subscription_repository import SubscriptionRepository
from decimal import Decimal

router = APIRouter(prefix="/webhook", tags=["Webhook"])


@router.post("/whatsapp")
async def whatsapp_webhook(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MessageSid: Optional[str] = Form(None),
    NumMedia: Optional[str] = Form("0"),
    MediaUrl0: Optional[str] = Form(None),
    MediaContentType0: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    twilio_service = TwilioWhatsAppService()

    # Rate limit webhook by IP
    await webhook_rate_limiter.check(request, "twilio")

    # Log incoming webhook (safe metadata only)
    log_webhook_received("twilio", "whatsapp", MessageSid)

    # Validate Twilio signature — mandatory in production, optional bypass in dev
    if settings.ENVIRONMENT == "production" and not settings.TWILIO_VALIDATE_SIGNATURE:
        logger.critical("🚨 CRITICAL: TWILIO_VALIDATE_SIGNATURE is false in production — rejecting webhook")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Signature validation is mandatory in production"
        )

    if settings.TWILIO_VALIDATE_SIGNATURE:
        twilio_signature = request.headers.get("X-Twilio-Signature", "")
        url = str(request.url)

        form_data = await request.form()
        params = {key: value for key, value in form_data.items()}

        if not twilio_service.validate_request(url, params, twilio_signature):
            logger.warning(f"Invalid Twilio signature for webhook from {From}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid request signature"
            )
    else:
        logger.warning("Twilio signature validation is disabled - this should only be used in development")

    try:
        phone_number = twilio_service.extract_phone_number(From)
        logger.info(f"📞 Extracted phone number: {phone_number}")
        
        await whatsapp_rate_limiter.check_rate_limit(phone_number)
        
        num_media = int(NumMedia or "0")
        message_text = Body
        is_audio = False
        
        if num_media > 0 and MediaUrl0 and MediaContentType0:
            content_type = MediaContentType0.lower()
            logger.info(f"Received media from {phone_number}: type={content_type}, url={MediaUrl0}")
            
            if "audio" in content_type or "ogg" in content_type:
                is_audio = True
                from app.services.audio_transcription_service import AudioTranscriptionService
                audio_service = AudioTranscriptionService()
                
                try:
                    transcription = await audio_service.process_audio_message(
                        MediaUrl0, content_type
                    )
                    message_text = transcription
                    logger.info(f"Audio transcribed from {phone_number}: {transcription}")
                except Exception as e:
                    logger.error(f"Error transcribing audio: {str(e)}")
                    await twilio_service.send_message(
                        From,
                        "Desculpe, nao consegui entender o audio. Pode tentar novamente ou enviar por texto?"
                    )
                    return {"status": "error", "message": "Audio transcription failed"}
            else:
                await twilio_service.send_message(
                    From,
                    "No momento, aceito apenas mensagens de texto e audio. Envie sua mensagem por texto ou grave um audio!"
                )
                return {"status": "success", "message": "Unsupported media type"}
        
        if not message_text or not message_text.strip():
            return {"status": "success", "message": "Empty message"}
        
        logger.info(f"Processing WhatsApp message from {phone_number[:4]}***" +
                     (" [transcribed from audio]" if is_audio else ""))
        
        user_repo = UserRepository(db)
        user = await user_repo.get_by_phone(phone_number)
        logger.info(f"👤 User lookup for {phone_number}: {'Found' if user else 'Not found'}")
        
        if not user:
            response_message = (
                "👋 Olá! Seja bem-vindo(a) ao *PayFlow AI*!\n\n"
                "Vejo que você ainda não tem cadastro. Não se preocupe, é rápido e fácil!\n\n"
                "✨ *Com o PayFlow AI você pode:*\n"
                "💰 Registrar despesas e receitas por voz ou texto\n"
                "📲 Criar cobranças e links de pagamento pelo WhatsApp\n"
                "📊 Ver relatórios e gráficos detalhados\n"
                "🔔 Criar lembretes de pagamentos\n"
                "🤖 Conversar comigo aqui no WhatsApp 24/7\n"
                "📈 Acompanhar seu saldo em tempo real\n\n"
                "🚀 *Comece agora:*\n"
                f"{settings.FRONTEND_URL}/register\n\n"
                "Após o cadastro, é só me enviar uma mensagem e começamos! 😊"
            )

            await twilio_service.send_message(From, response_message)
            return {"status": "success", "message": "User not registered"}
        
        subscription_repo = SubscriptionRepository(db)
        subscription = await subscription_repo.get_by_user_id(user.id)
        
        if not subscription or subscription.status != "active":
            response_message = (
                "⚠️ Olá! Sua assinatura está inativa no momento.\n\n"
                "💡 *Para continuar aproveitando todos os recursos:*\n"
                "📱 Registro de transações ilimitadas\n"
                "📊 Relatórios detalhados\n"
                "🔔 Lembretes automáticos\n"
                "🤖 Assistente IA 24/7\n\n"
                "🎯 *Ative sua assinatura agora:*\n"
                f"{settings.FRONTEND_URL}/plans\n\n"
                "Escolha o plano ideal para você e volte a ter o controle total das suas finanças! 💪"
            )
            await twilio_service.send_message(From, response_message)
            return {"status": "success", "message": "Subscription inactive"}
        
        conversation_repo = ConversationRepository(db)
        ai_service = AIService()
        
        user_log = f"[Audio] {message_text}" if is_audio else message_text
        try:
            await conversation_repo.create(
                user_id=user.id,
                log_data=ConversationLogCreate(message=user_log, role=MessageRole.USER)
            )
        except Exception as e:
            logger.warning(f"Failed to save user message to conversation log: {str(e)}")
        
        context = await conversation_repo.get_context(user.id, limit=5)

        classification = await ai_service.classify_intent(message_text, context)
        intent = classification.get("intent")
        entities = classification.get("entities", {})

        # Fast-path for confirmation/cancellation when a pending action exists.
        if intent in ("help", "confirm_pending_action", "cancel_pending_action") or not intent:
            detected = ai_service.detect_confirmation(message_text)
            if detected:
                intent = detected

        # Fallback local extraction for charge entities when AI misses values.
        if intent == "create_pix_charge" and (not entities.get("amount") or not entities.get("customer_name")):
            local_entities = ai_service.extract_charge_entities(message_text)
            entities = {**local_entities, **entities}

        if intent in ("register_expense", "register_income"):
            plan_service = PlanLimitService(db)
            allowed, limit_message = await plan_service.check_transaction_limit(user.id)
            if not allowed:
                await twilio_service.send_message(From, limit_message)
                return {"status": "success", "message": "Transaction limit reached"}
            if limit_message:
                pass
        
        response_message = await process_intent(
            intent, entities, user.id, db, ai_service, context
        )
        
        if intent in ("register_expense", "register_income"):
            try:
                plan_service = PlanLimitService(db)
                _, warning_message = await plan_service.check_transaction_limit(user.id)
                if warning_message:
                    response_message += f"\n\n{warning_message}"
            except Exception:
                pass
        
        if is_audio:
            response_message = f'Entendi seu audio: "{message_text}"\n\n{response_message}'
        
        try:
            await conversation_repo.create(
                user_id=user.id,
                log_data=ConversationLogCreate(message=response_message, role=MessageRole.ASSISTANT)
            )
        except Exception as e:
            logger.warning(f"Failed to save assistant message to conversation log: {str(e)}")
        
        await twilio_service.send_message(From, response_message)
        
        logger.info(f"Processed WhatsApp message for user {user.id}, intent: {intent}, audio: {is_audio}")
        return {"status": "success", "intent": intent, "audio": is_audio}
        
    except Exception as e:
        logger.error(f"Error processing WhatsApp webhook: {str(e)}", exc_info=True)
        
        error_message = "Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente."
        try:
            await twilio_service.send_message(From, error_message)
        except:
            pass
        
        return {"status": "error", "message": str(e)}


async def process_intent(
    intent: str,
    entities: dict,
    user_id: int,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        if intent == "register_expense":
            return await handle_register_expense(user_id, entities, db, ai_service, context)
        
        elif intent == "register_income":
            return await handle_register_income(user_id, entities, db, ai_service, context)
        
        elif intent == "create_reminder":
            return await handle_create_reminder(user_id, entities, db, ai_service, context)
        
        elif intent == "financial_report":
            return await handle_financial_report(user_id, entities, db, ai_service, context)
        
        elif intent == "list_transactions":
            return await handle_list_transactions(user_id, entities, db, ai_service, context)

        elif intent == "create_pix_charge":
            return await handle_create_pix_charge(user_id, entities, db, ai_service, context)

        elif intent == "confirm_pending_action":
            return await handle_confirm_pending_action(user_id, entities, db, ai_service, context)

        elif intent == "cancel_pending_action":
            return await handle_cancel_pending_action(user_id, entities, db, ai_service, context)

        elif intent == "list_charges":
            return await handle_list_charges(user_id, entities, db, ai_service, context)

        elif intent == "list_pending_charges":
            return await handle_list_pending_charges(user_id, entities, db, ai_service, context)

        elif intent == "list_paid_charges":
            return await handle_list_paid_charges(user_id, entities, db, ai_service, context)

        elif intent == "cancel_charge":
            return await handle_cancel_charge(user_id, entities, db, ai_service, context)

        elif intent == "send_charge_link":
            return await handle_send_charge_link(user_id, entities, db, ai_service, context)

        elif intent == "check_charge_status":
            return await handle_check_charge_status(user_id, entities, db, ai_service, context)

        else:
            return await handle_help(ai_service, context)
    
    except Exception as e:
        logger.error(f"Error processing intent {intent}: {str(e)}")
        return "Desculpe, não consegui processar sua solicitação. Pode tentar novamente?"


PAYMENT_METHOD_LABELS = {
    PaymentMethod.CONTA_CORRENTE: "Conta Corrente",
    PaymentMethod.CARTAO_CREDITO: "Cartão de Crédito",
    PaymentMethod.CARTAO_DEBITO: "Cartão de Débito",
    PaymentMethod.PIX: "PIX",
    PaymentMethod.DINHEIRO: "Dinheiro",
    PaymentMethod.OUTROS: "Outros",
}


def parse_payment_method(value: str) -> PaymentMethod:
    try:
        return PaymentMethod(value)
    except ValueError:
        return PaymentMethod.CONTA_CORRENTE


def get_affects_balance(payment_method: PaymentMethod, is_cash_withdrawal: bool = False) -> bool:
    if payment_method == PaymentMethod.CARTAO_CREDITO:
        return False
    if payment_method == PaymentMethod.DINHEIRO:
        return is_cash_withdrawal
    if payment_method == PaymentMethod.OUTROS:
        return False
    return True


def get_balance_note(payment_method: PaymentMethod, affects: bool) -> str:
    if payment_method == PaymentMethod.CARTAO_CREDITO:
        return "\n\nObs: Gasto no cartao de credito. Nao altera saldo da conta corrente."
    if payment_method == PaymentMethod.DINHEIRO and not affects:
        return "\n\nObs: Gasto em dinheiro (sem saque da conta)."
    if payment_method == PaymentMethod.DINHEIRO and affects:
        return "\n\nObs: Saque da conta corrente. Saldo da conta atualizado."
    return ""


async def handle_register_expense(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        amount = entities.get("amount")
        category = entities.get("category", "outros")
        description = entities.get("description", "")
        date_str = entities.get("date", datetime.now().strftime("%Y-%m-%d"))
        payment_method = parse_payment_method(entities.get("payment_method", "conta_corrente"))
        is_cash_withdrawal = entities.get("cash_withdrawal", False)
        affects_balance = get_affects_balance(payment_method, is_cash_withdrawal)
        
        if not amount:
            return "Por favor, informe o valor da despesa. Exemplo: 'Gastei R$ 50 com almoço'"
        
        transaction_data = TransactionCreate(
            type=TransactionType.EXPENSE,
            amount=Decimal(str(amount)),
            category=category,
            description=description,
            payment_method=payment_method,
            affects_balance=affects_balance,
            date=datetime.strptime(date_str, "%Y-%m-%d").date()
        )
        
        transaction_service = TransactionService(db)
        transaction = await transaction_service.create_transaction(user_id, transaction_data)
        
        pm_label = PAYMENT_METHOD_LABELS.get(transaction.payment_method, "Conta Corrente")
        balance_note = get_balance_note(transaction.payment_method, transaction.affects_balance)
        return f"""✅ Despesa registrada com sucesso!

💸 Valor: R$ {float(transaction.amount):.2f}
📁 Categoria: {transaction.category}
💳 Pagamento: {pm_label}
📅 Data: {transaction.date.strftime('%d/%m/%Y')}
{f'📝 Descrição: {transaction.description}' if transaction.description else ''}{balance_note}"""
    
    except Exception as e:
        logger.error(f"Error registering expense: {str(e)}")
        return "Erro ao registrar despesa. Verifique os dados e tente novamente."


async def handle_register_income(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        amount = entities.get("amount")
        category = entities.get("category", "outros")
        description = entities.get("description", "")
        date_str = entities.get("date", datetime.now().strftime("%Y-%m-%d"))
        
        if not amount:
            return "Por favor, informe o valor da receita. Exemplo: 'Recebi R$ 3000 de salário'"
        
        payment_method = parse_payment_method(entities.get("payment_method", "conta_corrente"))
        affects_balance = get_affects_balance(payment_method, is_cash_withdrawal=True)
        
        transaction_data = TransactionCreate(
            type=TransactionType.INCOME,
            amount=Decimal(str(amount)),
            category=category,
            description=description,
            payment_method=payment_method,
            affects_balance=affects_balance,
            date=datetime.strptime(date_str, "%Y-%m-%d").date()
        )
        
        transaction_service = TransactionService(db)
        transaction = await transaction_service.create_transaction(user_id, transaction_data)
        
        pm_label = PAYMENT_METHOD_LABELS.get(transaction.payment_method, "Conta Corrente")
        return f"""✅ Receita registrada com sucesso!

💰 Valor: R$ {float(transaction.amount):.2f}
📁 Categoria: {transaction.category}
💳 Destino: {pm_label}
📅 Data: {transaction.date.strftime('%d/%m/%Y')}
{f'📝 Descrição: {transaction.description}' if transaction.description else ''}"""
    
    except Exception as e:
        logger.error(f"Error registering income: {str(e)}")
        return "Erro ao registrar receita. Verifique os dados e tente novamente."


async def handle_create_reminder(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        title = entities.get("title")
        due_date_str = entities.get("due_date")
        
        if not title:
            return "Por favor, informe o que deseja lembrar. Exemplo: 'Lembrar de pagar conta amanhã'"
        
        if not due_date_str:
            due_date_str = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d %H:%M:%S")
        
        reminder_data = ReminderCreate(
            title=title,
            due_date=due_date
        )
        
        reminder_service = ReminderService(db)
        reminder = await reminder_service.create_reminder(user_id, reminder_data)
        
        return f"""✅ Lembrete criado com sucesso!

📌 {reminder.title}
📅 Data: {reminder.due_date.strftime('%d/%m/%Y às %H:%M')}"""
    
    except Exception as e:
        logger.error(f"Error creating reminder: {str(e)}")
        return "Erro ao criar lembrete. Tente novamente."


async def handle_financial_report(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        report_service = ReportService(db)
        summary = await report_service.get_current_month_summary(user_id)
        
        transaction_service = TransactionService(db)
        account_balance = await transaction_service.get_account_balance(user_id)
        credit_card_total = await transaction_service.get_credit_card_total(user_id)
        
        report = f"""📊 Resumo Financeiro - {summary['period']}

💰 Receitas: R$ {summary['total_income']:.2f}
💸 Despesas totais: R$ {summary['total_expenses']:.2f}

🏦 Saldo Conta Corrente: R$ {float(account_balance):.2f}
💳 Fatura Cartao de Credito: R$ {float(credit_card_total):.2f}

📈 Total de transacoes: {summary['transaction_count']}"""
        
        return report
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return "Erro ao gerar relatório. Tente novamente."


async def handle_list_transactions(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        transaction_service = TransactionService(db)
        transactions = await transaction_service.get_user_transactions(user_id, limit=5)
        
        if not transactions:
            return "Você ainda não tem transações registradas."
        
        message = "📋 Últimas transações:\n\n"
        
        for t in transactions:
            emoji = "💸" if t.type == TransactionType.EXPENSE else "💰"
            pm_label = PAYMENT_METHOD_LABELS.get(t.payment_method, "Conta Corrente")
            message += f"{emoji} R$ {float(t.amount):.2f} - {t.category}\n"
            message += f"   💳 {pm_label} | {t.date.strftime('%d/%m/%Y')}\n\n"
        
        message += "Para ver todas as transações, acesse o dashboard web!"
        
        return message
    
    except Exception as e:
        logger.error(f"Error listing transactions: {str(e)}")
        return "Erro ao listar transações. Tente novamente."


async def handle_create_pix_charge(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        amount = entities.get("amount")
        customer_name = entities.get("customer_name")
        customer_phone = entities.get("customer_phone")
        description = entities.get("description")
        due_date = entities.get("due_date")

        if not amount or not customer_name:
            return "Para criar uma cobrança, informe o valor e o nome do cliente. Exemplo: 'Gere uma cobrança de R$ 150 para João'"

        pending_service = PendingActionService(db)
        action = await pending_service.create_charge_action(
            user_id=user_id,
            amount=float(amount),
            customer_name=customer_name,
            description=description,
            customer_phone=customer_phone,
            due_date=due_date
        )

        return pending_service.format_charge_summary(action)

    except Exception as e:
        logger.error(f"Error creating pending charge action: {str(e)}")
        return "Erro ao preparar cobrança. Verifique os dados e tente novamente."


async def handle_confirm_pending_action(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        pending_service = PendingActionService(db)
        action = await pending_service.get_pending_action(user_id)

        if not action:
            return "Não encontrei nenhuma ação pendente para confirmar."

        charge = await pending_service.confirm_and_execute(action.id, user_id)
        if not charge:
            return "Não consegui gerar a cobrança. Verifique os dados e tente novamente."

        message = (
            f"✅ *Cobrança criada com sucesso!*\n\n"
            f"👤 Cliente: {charge.customer_name}\n"
            f"💰 Valor: R$ {float(charge.amount):.2f}\n"
        )
        if charge.description:
            message += f"📝 Referente a: {charge.description}\n"
        if charge.payment_link:
            message += f"🔗 Link de pagamento: {charge.payment_link}\n"
        message += "\nVou te avisar assim que o pagamento for confirmado. 🔔"

        if charge.customer_phone:
            message += f"\n\n📱 O cliente tem telefone cadastrado ({charge.customer_phone}). Deseja que eu envie o link de pagamento para ele pelo WhatsApp? Responda *sim* ou *não*."

        return message

    except Exception as e:
        logger.error(f"Error confirming pending action: {str(e)}")
        return "Erro ao confirmar ação. Tente novamente."


async def handle_cancel_pending_action(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        pending_service = PendingActionService(db)
        action = await pending_service.cancel_latest_pending(user_id)

        if not action:
            return "Não encontrei nenhuma ação pendente para cancelar."

        return "🚫 Ação cancelada. Se precisar, é só pedir novamente!"

    except Exception as e:
        logger.error(f"Error cancelling pending action: {str(e)}")
        return "Erro ao cancelar ação. Tente novamente."


async def handle_list_charges(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        charge_service = ChargeService(db)
        charges = await charge_service.get_user_charges(user_id, limit=10)

        if not charges:
            return "Você ainda não tem cobranças criadas."

        message = "📋 *Suas últimas cobranças:*\n\n"
        for i, c in enumerate(charges, 1):
            derived = charge_service.get_derived_status(c)
            status_label = {
                "pending": "pendente",
                "paid": "pago",
                "overdue": "vencida",
                "cancelled": "cancelada",
                "expired": "expirada",
                "failed": "falhou"
            }.get(derived, derived)
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — {status_label}\n"

        summary = await charge_service.get_summary(user_id)
        message += f"\n*Resumo:*\n"
        message += f"A receber: R$ {float(summary.total_pending + summary.total_overdue):.2f}\n"
        message += f"Recebido: R$ {float(summary.total_paid):.2f}"

        return message

    except Exception as e:
        logger.error(f"Error listing charges: {str(e)}")
        return "Erro ao listar cobranças. Tente novamente."


async def handle_list_pending_charges(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        charge_service = ChargeService(db)
        charges = await charge_service.get_pending_charges(user_id)

        if not charges:
            return "✅ Você não tem cobranças pendentes."

        message = "⏳ *Cobranças pendentes:*\n\n"
        for i, c in enumerate(charges, 1):
            derived = charge_service.get_derived_status(c)
            status_label = "vencida" if derived == "overdue" else "pendente"
            due_str = c.due_date.strftime("%d/%m/%Y") if c.due_date else "sem vencimento"
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — {status_label} (vence: {due_str})\n"

        return message

    except Exception as e:
        logger.error(f"Error listing pending charges: {str(e)}")
        return "Erro ao listar cobranças pendentes. Tente novamente."


async def handle_list_paid_charges(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        charge_service = ChargeService(db)
        charges = await charge_service.get_paid_charges(user_id, limit=10)

        if not charges:
            return "Você ainda não tem cobranças pagas."

        message = "✅ *Cobranças pagas:*\n\n"
        for i, c in enumerate(charges, 1):
            paid_str = c.paid_at.strftime("%d/%m/%Y") if c.paid_at else "data não disponível"
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — paga em {paid_str}\n"

        return message

    except Exception as e:
        logger.error(f"Error listing paid charges: {str(e)}")
        return "Erro ao listar cobranças pagas. Tente novamente."


async def handle_cancel_charge(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        charge_service = ChargeService(db)
        customer_name = entities.get("customer_name")
        amount = entities.get("amount")
        reference = entities.get("reference")

        candidates: list = []

        if reference == "latest":
            latest = await charge_service.get_latest_charge(user_id)
            if latest:
                candidates = [latest]
        elif customer_name:
            candidates = await charge_service.find_charges_by_customer_name(user_id, customer_name)
            candidates = [c for c in candidates if c.status.value == "pending"]
        elif amount:
            from decimal import Decimal
            candidates = await charge_service.find_charges_by_amount(user_id, Decimal(str(amount)))
            candidates = [c for c in candidates if c.status.value == "pending"]

        if not candidates:
            return "Não encontrei nenhuma cobrança pendente com esses critérios para cancelar."

        if len(candidates) == 1:
            charge = candidates[0]
            if charge.status.value != "pending":
                return f"❌ A cobrança de R$ {float(charge.amount):.2f} para {charge.customer_name} já foi {charge.status.value} e não pode ser cancelada."
            cancelled = await charge_service.cancel_charge(charge.id, user_id)
            if cancelled:
                return f"🚫 Cobrança de R$ {float(cancelled.amount):.2f} para {cancelled.customer_name} cancelada com sucesso."
            return "Não consegui cancelar a cobrança. Tente novamente."

        message = "Encontrei mais de uma cobrança:\n\n"
        for i, c in enumerate(candidates, 1):
            message += f"{i}. {c.customer_name} — R$ {float(c.amount):.2f} — {c.status.value}\n"
        message += "\nQual você deseja cancelar? Responda com o número."
        return message

    except Exception as e:
        logger.error(f"Error cancelling charge: {str(e)}")
        return "Erro ao cancelar cobrança. Tente novamente."


async def handle_send_charge_link(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_delivery_service import ChargeDeliveryService

        charge_service = ChargeService(db)
        charge = await charge_service.get_latest_charge(user_id)

        if not charge:
            return "Você ainda não tem cobranças para enviar o link."

        if not charge.customer_phone:
            return "A cobrança mais recente não tem telefone do cliente cadastrado. Não é possível enviar o link."

        delivery_service = ChargeDeliveryService(db)
        result = await delivery_service.send_charge_link_to_customer(charge, user_id)

        if result["success"]:
            if result.get("simulated"):
                return (
                    f"📱 *Link enviado (simulado)*\n\n"
                    f"O link de pagamento foi simulado para {charge.customer_phone}.\n"
                    f"(Twilio não configurado — em produção, a mensagem seria enviada.)"
                )
            return (
                f"📱 *Link enviado com sucesso!*\n\n"
                f"O link de pagamento de R$ {float(charge.amount):.2f} foi enviado para "
                f"{charge.customer_name} ({charge.customer_phone})."
            )
        return f"❌ Não consegui enviar o link: {result['message']}"

    except Exception as e:
        logger.error(f"Error sending charge link: {str(e)}")
        return "Erro ao enviar link de pagamento. Tente novamente."


async def handle_check_charge_status(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        charge_service = ChargeService(db)
        charges = await charge_service.get_user_charges(user_id, limit=1)

        if not charges:
            return "Você ainda não tem cobranças para consultar."

        charge = charges[0]
        derived = charge_service.get_derived_status(charge)
        status_label = {
            "pending": "pendente",
            "paid": "paga",
            "overdue": "vencida",
            "cancelled": "cancelada",
            "expired": "expirada",
            "failed": "falhou"
        }.get(derived, derived)
        return f"A cobrança mais recente de *R$ {float(charge.amount):.2f}* para *{charge.customer_name}* está *{status_label}*."

    except Exception as e:
        logger.error(f"Error checking charge status: {str(e)}")
        return "Erro ao consultar status da cobrança. Tente novamente."


async def handle_help(ai_service: AIService, context: str) -> str:
    return """👋 Como posso ajudar?

Você pode:

💰 Registrar despesas
Exemplo: "Gastei R$ 50 com almoço"

💵 Registrar receitas
Exemplo: "Recebi R$ 3000 de salário"

📲 Criar cobranças
Exemplo: "Gere uma cobrança de R$ 150 para João referente ao serviço do site"

📊 Ver resumo financeiro
Exemplo: "Quanto gastei esse mês?"

📋 Ver transações
Exemplo: "Mostre minhas últimas transações"

📅 Criar lembretes
Exemplo: "Lembrar de pagar conta amanhã"

É só me enviar uma mensagem! 😊"""


from datetime import timedelta
