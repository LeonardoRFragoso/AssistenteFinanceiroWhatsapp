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
from app.services.financial_query_service import FinancialQueryService
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
            elif "image" in content_type or "pdf" in content_type or "application/pdf" in content_type:
                from app.services.document_analysis_service import DocumentAnalysisService
                doc_service = DocumentAnalysisService()

                try:
                    analysis = await doc_service.analyze_media_url(MediaUrl0, content_type)
                    response = doc_service.format_whatsapp_response(analysis)
                    await twilio_service.send_message(From, response)
                    return {"status": "success", "message": "Document analyzed"}
                except Exception as e:
                    logger.error(f"Error analyzing document: {str(e)}")
                    await twilio_service.send_message(
                        From,
                        "Recebi sua imagem/documento, mas tive dificuldade na análise. Tente enviar por texto ou tente novamente."
                    )
                    return {"status": "error", "message": "Document analysis failed"}
            else:
                await twilio_service.send_message(
                    From,
                    "No momento, aceito mensagens de texto, audio, imagens e PDFs. Envie sua mensagem por texto, grave um audio ou envie uma imagem/PDF!"
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

        elif intent == "list_overdue_charges":
            return await handle_list_overdue_charges(user_id, entities, db, ai_service, context)

        elif intent == "search_charges":
            return await handle_search_charges(user_id, entities, db, ai_service, context)

        elif intent == "charge_summary":
            return await handle_charge_summary(user_id, entities, db, ai_service, context)

        elif intent == "customer_charge_history":
            return await handle_customer_charge_history(user_id, entities, db, ai_service, context)

        elif intent == "monthly_financial_summary":
            return await handle_monthly_financial_summary(user_id, entities, db, ai_service, context)

        elif intent == "top_overdue_customers":
            return await handle_top_overdue_customers(user_id, entities, db, ai_service, context)

        elif intent == "create_recurring_task":
            return await handle_create_recurring_task(user_id, entities, db, ai_service, context)

        elif intent == "list_recurring_tasks":
            return await handle_list_recurring_tasks(user_id, entities, db, ai_service, context)

        elif intent == "list_customers":
            return await handle_list_customers(user_id, entities, db, ai_service, context)

        elif intent == "customer_summary":
            return await handle_customer_summary(user_id, entities, db, ai_service, context)

        elif intent == "generate_collection_message":
            return await handle_generate_collection_message(user_id, entities, db, ai_service, context)

        elif intent == "prepare_overdue_followups":
            return await handle_prepare_overdue_followups(user_id, entities, db, ai_service, context)

        elif intent == "list_collection_rules":
            return await handle_list_collection_rules(user_id, entities, db, ai_service, context)

        elif intent == "create_collection_rule":
            return await handle_create_collection_rule(user_id, entities, db, ai_service, context)

        elif intent == "list_message_templates":
            return await handle_list_message_templates(user_id, entities, db, ai_service, context)

        elif intent == "analytics_overview":
            return await handle_analytics_overview(user_id, entities, db, ai_service, context)

        elif intent == "monthly_trends_summary":
            return await handle_monthly_trends_summary(user_id, entities, db, ai_service, context)

        elif intent == "aging_summary":
            return await handle_aging_summary(user_id, entities, db, ai_service, context)

        elif intent == "customer_performance_summary":
            return await handle_customer_performance_summary(user_id, entities, db, ai_service, context)

        elif intent == "collection_performance_summary":
            return await handle_collection_performance_summary(user_id, entities, db, ai_service, context)

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

🔍 Consultar cobranças
Exemplos: "quais cobranças estão vencidas?", "quem ainda não pagou?", "me mostra as cobranças do João"

📊 Resumo de cobranças
Exemplos: "quanto tenho a receber?", "me manda um resumo das cobranças"

📈 Resumo mensal
Exemplos: "quanto entrou em junho?", "resumo financeiro de julho"

🔁 Tarefas recorrentes
Exemplos: "todo dia 5 me lembra de cobrar o João", "toda sexta me lembra de revisar cobranças"

👥 Clientes
Exemplos: "quais clientes estão devendo?", "me mostra o histórico do João"

📝 Mensagens de cobrança
Exemplos: "gera uma mensagem educada para cobrar a Maria", "cobre os clientes vencidos"

📋 Régua de cobrança
Exemplos: "crie uma régua para lembrar 2 dias antes do vencimento", "quais templates de cobrança eu tenho?"

É só me enviar uma mensagem! 😊"""


async def handle_list_overdue_charges(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        query_service = FinancialQueryService(db)
        return await query_service.list_overdue_charges(user_id)
    except Exception as e:
        logger.error(f"Error listing overdue charges: {str(e)}")
        return "Erro ao listar cobranças vencidas. Tente novamente."


async def handle_search_charges(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        customer_name = entities.get("customer_name")
        if not customer_name:
            return "Qual cliente você quer buscar? Exemplo: 'me mostra as cobranças do João'"

        query_service = FinancialQueryService(db)
        return await query_service.search_charges_by_customer(user_id, customer_name)
    except Exception as e:
        logger.error(f"Error searching charges: {str(e)}")
        return "Erro ao buscar cobranças. Tente novamente."


async def handle_charge_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        query_service = FinancialQueryService(db)
        return await query_service.charge_summary(user_id)
    except Exception as e:
        logger.error(f"Error generating charge summary: {str(e)}")
        return "Erro ao gerar resumo de cobranças. Tente novamente."


async def handle_customer_charge_history(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        customer_name = entities.get("customer_name")
        if not customer_name:
            return "De qual cliente você quer ver o histórico? Exemplo: 'histórico do João'"

        query_service = FinancialQueryService(db)
        return await query_service.customer_charge_history(user_id, customer_name)
    except Exception as e:
        logger.error(f"Error getting customer history: {str(e)}")
        return "Erro ao buscar histórico do cliente. Tente novamente."


async def handle_monthly_financial_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from datetime import datetime
        now = datetime.now()
        month = entities.get("month")
        year = entities.get("year", now.year)

        if not month:
            return "De qual mês você quer o resumo? Exemplo: 'resumo financeiro de julho' ou 'quanto entrou em junho?'"

        try:
            month_int = int(month)
            year_int = int(year)
        except (ValueError, TypeError):
            return "Não consegui identificar o mês. Tente algo como 'resumo de julho' ou 'quanto entrou em junho?'"

        if not (1 <= month_int <= 12):
            return "O mês precisa estar entre 1 e 12."

        query_service = FinancialQueryService(db)
        return await query_service.monthly_financial_summary(user_id, year_int, month_int)
    except Exception as e:
        logger.error(f"Error generating monthly summary: {str(e)}")
        return "Erro ao gerar resumo mensal. Tente novamente."


async def handle_top_overdue_customers(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        query_service = FinancialQueryService(db)
        return await query_service.top_overdue_customers(user_id)
    except Exception as e:
        logger.error(f"Error listing top overdue customers: {str(e)}")
        return "Erro ao listar clientes com mais atrasos. Tente novamente."


async def handle_create_recurring_task(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.recurring_task_service import RecurringTaskService
        from app.schemas.recurring_task import RecurringTaskCreate
        from app.models.recurring_task import RecurrenceType

        title = entities.get("title")
        recurrence_type_str = entities.get("recurrence_type", "daily")

        if not title:
            return "Qual tarefa você quer criar? Exemplo: 'todo dia 5 me lembra de cobrar o João'"

        try:
            recurrence_type = RecurrenceType(recurrence_type_str)
        except ValueError:
            recurrence_type = RecurrenceType.DAILY

        day_of_week = entities.get("day_of_week")
        day_of_month = entities.get("day_of_month")

        if isinstance(day_of_week, str):
            day_of_week = int(day_of_week) if day_of_week else None
        if isinstance(day_of_month, str):
            day_of_month = int(day_of_month) if day_of_month else None

        task_data = RecurringTaskCreate(
            title=title,
            recurrence_type=recurrence_type,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )

        service = RecurringTaskService(db)
        task = await service.create_task(user_id, task_data)

        recurrence_label = {
            "daily": "diariamente",
            "weekly": "semanalmente",
            "monthly": "mensalmente",
        }.get(recurrence_type.value, recurrence_type.value)

        message = f"✅ Tarefa recorrente criada!\n\n"
        message += f"📌 {task.title}\n"
        message += f"🔁 Recorrência: {recurrence_label}\n"
        message += f"⏰ Próxima execução: {task.next_run_at.strftime('%d/%m/%Y às %H:%M')}\n\n"
        message += "Esta tarefa apenas envia lembretes. Nenhuma operação bancária será executada."

        return message
    except Exception as e:
        logger.error(f"Error creating recurring task: {str(e)}")
        return "Erro ao criar tarefa recorrente. Tente novamente."


async def handle_list_recurring_tasks(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.recurring_task_service import RecurringTaskService

        service = RecurringTaskService(db)
        tasks = await service.get_user_tasks(user_id)

        if not tasks:
            return "Você não tem tarefas recorrentes ativas."

        active_tasks = [t for t in tasks if t.active]
        if not active_tasks:
            return "Você não tem tarefas recorrentes ativas."

        message = f"🔁 *Suas tarefas recorrentes ({len(active_tasks)}):*\n\n"
        for i, t in enumerate(active_tasks, 1):
            recurrence_label = {
                "daily": "diária",
                "weekly": "semanal",
                "monthly": "mensal",
            }.get(t.recurrence_type.value, t.recurrence_type.value)
            message += f"{i}. {t.title} ({recurrence_label})\n"
            message += f"   Próxima: {t.next_run_at.strftime('%d/%m/%Y às %H:%M')}\n\n"

        return message
    except Exception as e:
        logger.error(f"Error listing recurring tasks: {str(e)}")
        return "Erro ao listar tarefas recorrentes. Tente novamente."


from datetime import timedelta


async def handle_list_customers(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.customer_service import CustomerService
        service = CustomerService(db)
        result = await service.list_customers(user_id, page=1, page_size=20)
        items = result["items"]
        if not items:
            return "Você ainda não tem clientes cadastrados."

        message = f"👥 *Seus clientes ({len(items)}):*\n\n"
        for i, c in enumerate(items, 1):
            status_label = {
                "good_payer": "✅ Bom pagador",
                "late_payer": "⚠️ Pagamento em atraso",
                "frequent_late": "🔴 Atrasa frequentemente",
                "new_customer": "🆕 Novo cliente",
                "inactive_customer": "💤 Inativo",
            }.get(c.get("operational_status", ""), c.get("operational_status", ""))
            message += f"{i}. {c['name']} — {status_label}\n"
            if c.get("has_overdue"):
                message += f"   ⚠️ Tem cobrança vencida\n"
            message += f"   Total pago: R$ {c.get('total_paid_amount', 0):.2f}\n\n"

        return message
    except Exception as e:
        logger.error(f"Error listing customers: {str(e)}")
        return "Erro ao listar clientes. Tente novamente."


async def handle_customer_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.customer_service import CustomerService
        customer_name = entities.get("customer_name")
        if not customer_name:
            return "De qual cliente você quer ver o resumo? Exemplo: 'me mostra o histórico do João'"

        service = CustomerService(db)
        result = await service.list_customers(user_id, search=customer_name, page=1, page_size=1)
        items = result["items"]
        if not items:
            return f"Não encontrei nenhum cliente chamado '{customer_name}'."

        c = items[0]
        status_label = {
            "good_payer": "✅ Bom pagador",
            "late_payer": "⚠️ Pagamento em atraso",
            "frequent_late": "🔴 Atrasa frequentemente",
            "new_customer": "🆕 Novo cliente",
            "inactive_customer": "💤 Inativo",
        }.get(c.get("operational_status", ""), c.get("operational_status", ""))

        message = f"👤 *Cliente: {c['name']}*\n\n"
        message += f"Status: {status_label}\n"
        message += f"Total de cobranças: {c.get('total_charges_count', 0)}\n"
        message += f"Total pago: R$ {c.get('total_paid_amount', 0):.2f}\n"
        message += f"Total pendente: R$ {c.get('total_pending_amount', 0):.2f}\n"
        message += f"Total vencido: R$ {c.get('total_overdue_amount', 0):.2f}\n"

        if c.get("has_overdue"):
            message += "\n⚠️ Este cliente tem cobranças vencidas. Quer gerar uma mensagem de cobrança? Diga 'gera uma mensagem para cobrar {c['name']}'."

        return message
    except Exception as e:
        logger.error(f"Error getting customer summary: {str(e)}")
        return "Erro ao buscar resumo do cliente. Tente novamente."


async def handle_generate_collection_message(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.customer_service import CustomerService
        from app.services.message_template_service import MessageTemplateService
        from app.services.collection_service import CollectionService
        from app.models.message_template import MessageTone

        customer_name = entities.get("customer_name")
        if not customer_name:
            return "Para qual cliente você quer gerar a mensagem? Exemplo: 'gera uma mensagem para cobrar a Maria'"

        tone_str = entities.get("tone", "neutral")
        try:
            tone = MessageTone(tone_str)
        except ValueError:
            tone = MessageTone.NEUTRAL

        customer_service = CustomerService(db)
        result = await customer_service.list_customers(user_id, search=customer_name, page=1, page_size=1)
        items = result["items"]
        if not items:
            return f"Não encontrei nenhum cliente chamado '{customer_name}'."

        customer = items[0]
        charges = await customer_service.get_customer_charges(customer["id"], user_id)

        overdue_charges = [
            c for c in charges
            if c.status.value == "pending" and c.due_date and c.due_date < datetime.now().date()
        ]

        if not overdue_charges:
            return f"O cliente {customer['name']} não tem cobranças vencidas."

        charge = overdue_charges[0]

        mt_service = MessageTemplateService(db)
        templates = await mt_service.list_templates(user_id, active_only=True)
        template = next((t for t in templates if t.tone == tone), templates[0] if templates else None)

        if template:
            ctx = {
                "customer_name": customer["name"],
                "amount": f"{float(charge.amount):.2f}",
                "description": charge.description or "cobrança",
                "due_date": charge.due_date.strftime("%d/%m/%Y") if charge.due_date else "",
                "payment_link": charge.payment_link or "",
                "qr_code_note": "Sandbox/Demo — não representa Pix real",
                "company_name": "PayFlow AI",
            }
            rendered = mt_service.render_template(template.template_text, ctx)
            template_name = template.name
        else:
            rendered = (
                f"Olá, {customer['name']}!\n\n"
                f"A cobrança de R$ {float(charge.amount):.2f} referente a "
                f"{charge.description or 'cobrança'} está em atraso.\n\n"
                f"Link: {charge.payment_link or 'N/A'}\n\n"
                f"Por favor, regularize o pagamento."
            )
            template_name = "Fallback (sem template)"

        collection_service = CollectionService(db)
        await collection_service.log_message(
            user_id=user_id,
            charge_id=charge.id,
            customer_id=customer["id"],
            template_id=template.id if template else None,
            message_preview=rendered,
            status="draft",
        )

        message = f"📝 *Rascunho de mensagem para {customer['name']}:*\n\n"
        message += f"Template: {template_name}\n\n"
        message += f"---\n{rendered}\n---\n\n"
        message += "⚠️ Esta é apenas uma sugestão. Nenhuma mensagem foi enviada.\n"
        message += "Para enviar, confirme explicitamente respondendo \"enviar\"."

        return message
    except Exception as e:
        logger.error(f"Error generating collection message: {str(e)}")
        return "Erro ao gerar mensagem de cobrança. Tente novamente."


async def handle_prepare_overdue_followups(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.collection_service import CollectionService
        service = CollectionService(db)
        result = await service.generate_followup_previews(user_id, limit=10)
        items = result["items"]

        if not items:
            return "✅ Nenhuma cobrança vencida encontrada. Tudo em dia!"

        message = f"📋 *Encontrei {len(items)} cobrança(s) vencida(s).*\n\n"
        for i, item in enumerate(items, 1):
            message += f"{i}. {item['customer_name']} — R$ {item['amount']:.2f} — venceu há {item['days_overdue']} dia(s)\n"

        message += f"\n{result['message']}\n\n"
        message += "⚠️ Nenhuma mensagem será enviada automaticamente. "
        message += "Para ver os rascunhos, acesse o dashboard ou peça 'gera uma mensagem para cobrar [nome]'."

        return message
    except Exception as e:
        logger.error(f"Error preparing overdue followups: {str(e)}")
        return "Erro ao preparar follow-ups. Tente novamente."


async def handle_list_collection_rules(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.collection_service import CollectionService
        service = CollectionService(db)
        rules = await service.list_rules(user_id)

        if not rules:
            return "Você não tem regras de cobrança configuradas. Exemplo: 'crie uma régua para lembrar 2 dias antes do vencimento'"

        message = f"📋 *Suas regras de cobrança ({len(rules)}):*\n\n"
        for i, r in enumerate(rules, 1):
            trigger_label = {
                "before_due": f"{r.days_offset} dia(s) antes do vencimento",
                "on_due": "no dia do vencimento",
                "after_due": f"{r.days_offset} dia(s) após o vencimento",
            }.get(r.trigger_type.value, r.trigger_type.value)
            message += f"{i}. {r.name} — {trigger_label}\n"

        message += "\n⚠️ As regras não enviam mensagens automaticamente. Elas apenas preparam rascunhos para confirmação."
        return message
    except Exception as e:
        logger.error(f"Error listing collection rules: {str(e)}")
        return "Erro ao listar regras de cobrança. Tente novamente."


async def handle_create_collection_rule(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.collection_service import CollectionService
        from app.schemas.collection_rule import CollectionRuleCreate
        from app.models.collection_rule import TriggerType

        name = entities.get("name")
        days_offset = entities.get("days_offset", 0)
        trigger_type_str = entities.get("trigger_type", "on_due")

        if not name:
            name = "Regra de cobrança"

        try:
            trigger_type = TriggerType(trigger_type_str)
        except ValueError:
            trigger_type = TriggerType.ON_DUE

        if isinstance(days_offset, str):
            days_offset = int(days_offset) if days_offset else 0

        data = CollectionRuleCreate(
            name=name,
            days_offset=days_offset,
            trigger_type=trigger_type,
        )

        service = CollectionService(db)
        rule = await service.create_rule(user_id, data)

        trigger_label = {
            "before_due": f"{rule.days_offset} dia(s) antes do vencimento",
            "on_due": "no dia do vencimento",
            "after_due": f"{rule.days_offset} dia(s) após o vencimento",
        }.get(rule.trigger_type.value, rule.trigger_type.value)

        message = f"✅ Regra de cobrança criada!\n\n"
        message += f"📌 {rule.name}\n"
        message += f"⏰ Gatilho: {trigger_label}\n\n"
        message += "⚠️ Esta regra não envia mensagens automaticamente. Ela apenas prepara rascunhos para confirmação explícita."

        return message
    except Exception as e:
        logger.error(f"Error creating collection rule: {str(e)}")
        return "Erro ao criar regra de cobrança. Tente novamente."


async def handle_list_message_templates(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.message_template_service import MessageTemplateService
        service = MessageTemplateService(db)
        templates = await service.list_templates(user_id, active_only=True)

        if not templates:
            return "Você não tem templates de mensagem. Acesse o dashboard para criar templates padrão."

        message = f"📝 *Seus templates de mensagem ({len(templates)}):*\n\n"
        for i, t in enumerate(templates, 1):
            tone_label = {
                "friendly": "amigável",
                "neutral": "neutro",
                "firm": "firme",
            }.get(t.tone.value, t.tone.value)
            message += f"{i}. {t.name} (tom: {tone_label})\n"

        return message
    except Exception as e:
        logger.error(f"Error listing message templates: {str(e)}")
        return "Erro ao listar templates. Tente novamente."


async def handle_analytics_overview(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_analytics_service import ChargeAnalyticsService
        service = ChargeAnalyticsService(db)
        overview = await service.get_overview(user_id)

        if overview["total_charges"] == 0:
            return "Você ainda não tem cobranças para analisar. Crie algumas cobranças para começar a acompanhar sua performance."

        message = "📊 *Visão Geral das Cobranças*\n\n"
        message += f"💰 Total cobrado: R$ {overview['total_billed']:.2f}\n"
        message += f"✅ Total recebido: R$ {overview['total_paid']:.2f}\n"
        message += f"⏳ Pendente: R$ {overview['total_pending']:.2f}\n"
        message += f"🔴 Vencido: R$ {overview['total_overdue']:.2f}\n\n"
        message += f"📈 Taxa de recebimento: {overview['collection_rate']:.1f}%\n"
        message += f"📉 Taxa de vencimento: {overview['overdue_rate']:.1f}%\n"

        if overview["average_payment_time_days"] is not None:
            message += f"⏱️ Tempo médio de pagamento: {overview['average_payment_time_days']:.0f} dia(s)\n"

        if overview["average_delay_days"] is not None:
            message += f"⚠️ Atraso médio: {overview['average_delay_days']:.0f} dia(s)\n"

        message += f"\n👥 Clientes ativos: {overview['active_customers']}\n"
        message += f"👥 Clientes com vencido: {overview['overdue_customers']}\n"

        if overview["followups_drafted"] > 0:
            message += f"\n📝 Rascunhos de cobrança: {overview['followups_drafted']}\n"

        return message
    except Exception as e:
        logger.error(f"Error in analytics overview: {str(e)}")
        return "Erro ao gerar visão geral. Tente novamente."


async def handle_monthly_trends_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_analytics_service import ChargeAnalyticsService
        service = ChargeAnalyticsService(db)
        trends = await service.get_monthly_trends(user_id, months=3)

        if not trends or all(t["billed_amount"] == 0 for t in trends):
            return "Ainda não há dados suficientes para mostrar tendências mensais."

        message = "📈 *Tendências Mensais (últimos 3 meses)*\n\n"
        for t in trends:
            message += f"📅 {t['month']}\n"
            message += f"   Cobrado: R$ {t['billed_amount']:.2f}\n"
            message += f"   Recebido: R$ {t['paid_amount']:.2f}\n"
            message += f"   Taxa: {t['collection_rate']:.1f}%\n\n"

        return message
    except Exception as e:
        logger.error(f"Error in monthly trends: {str(e)}")
        return "Erro ao gerar tendências mensais. Tente novamente."


async def handle_aging_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_analytics_service import ChargeAnalyticsService
        service = ChargeAnalyticsService(db)
        aging = await service.get_aging(user_id)

        if aging["total_overdue"] == 0:
            return "✅ Você não tem cobranças vencidas! Tudo em dia."

        message = f"⏰ *Aging de Cobranças Vencidas ({aging['total_overdue']} cobrança(s))*\n\n"
        for b in aging["buckets"]:
            if b["count"] > 0:
                message += f"📌 {b['bucket']}: {b['count']} cobrança(s) — R$ {b['amount']:.2f} ({b['percentage']:.1f}%)\n"

        message += f"\n💰 Total vencido: R$ {aging['total_overdue_amount']:.2f}"

        return message
    except Exception as e:
        logger.error(f"Error in aging summary: {str(e)}")
        return "Erro ao gerar aging. Tente novamente."


async def handle_customer_performance_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_analytics_service import ChargeAnalyticsService
        service = ChargeAnalyticsService(db)
        ranking = await service.get_customer_performance(user_id, limit=5)

        if not ranking:
            return "Você ainda não tem clientes com cobranças para analisar."

        message = "👥 *Top 5 Clientes — Performance*\n\n"
        for i, c in enumerate(ranking, 1):
            status_label = {
                "good_payer": "✅ Bom pagador",
                "late_payer": "⚠️ Atrasa",
                "frequent_late": "🔴 Atrasa muito",
                "new_customer": "🆕 Novo",
                "inactive_customer": "💤 Inativo",
            }.get(c.get("operational_status", ""), c.get("operational_status", ""))
            message += f"{i}. {c['customer_name']} — {status_label}\n"
            message += f"   Cobrado: R$ {c['total_billed']:.2f} | Pago: R$ {c['total_paid']:.2f}\n"
            if c["total_overdue"] > 0:
                message += f"   🔴 Vencido: R$ {c['total_overdue']:.2f}\n"
            message += f"   Sugestão: {c['suggested_action'].replace('_', ' ')}\n\n"

        return message
    except Exception as e:
        logger.error(f"Error in customer performance: {str(e)}")
        return "Erro ao gerar ranking de clientes. Tente novamente."


async def handle_collection_performance_summary(
    user_id: int,
    entities: dict,
    db: AsyncSession,
    ai_service: AIService,
    context: str
) -> str:
    try:
        from app.services.charge_analytics_service import ChargeAnalyticsService
        service = ChargeAnalyticsService(db)
        perf = await service.get_collection_performance(user_id)

        if perf["insufficient_data"]:
            return "Ainda não há dados suficientes sobre a régua de cobrança. Continue usando os rascunhos de cobrança para acumular histórico."

        message = "📋 *Performance da Régua de Cobrança*\n\n"
        message += f"📝 Total de rascunhos: {perf['total_drafts']}\n"
        message += f"👥 Clientes contatados: {perf['customers_contacted']}\n"
        message += f"📊 Rascunhos este mês: {perf['followups_this_month']}\n"
        message += f"🔗 Cobranças com follow-up: {perf['charges_with_followup']}\n"

        if perf["charges_paid_after_followup"] > 0:
            message += f"✅ Pagas após follow-up: {perf['charges_paid_after_followup']}\n"
            message += f"💰 Valor recuperado estimado: R$ {perf['estimated_recovered_amount']:.2f}\n"

        if perf["drafts_by_status"]:
            message += "\n📊 Por status:\n"
            for status, count in perf["drafts_by_status"].items():
                message += f"   {status}: {count}\n"

        message += "\n⚠️ Lembre-se: a régua não envia mensagens automaticamente. Tudo precisa de confirmação explícita."

        return message
    except Exception as e:
        logger.error(f"Error in collection performance: {str(e)}")
        return "Erro ao gerar performance de cobrança. Tente novamente."
