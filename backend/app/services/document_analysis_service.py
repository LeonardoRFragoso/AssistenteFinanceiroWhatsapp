from typing import Dict, Any, Optional
from datetime import datetime
import re
import httpx
from app.core.config import settings
from app.core.logging import logger


class DocumentAnalysisService:
    """Assistive OCR service for extracting data from documents.

    This service analyzes images/PDFs sent by users and extracts financial
    data to create drafts (reminders, charges, annotations).

    IMPORTANT: This service NEVER executes payments. It only extracts data
    and returns a draft that requires explicit user confirmation.
    """

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_CONTENT_TYPES = {
        "image/png", "image/jpeg", "image/jpg", "image/webp",
        "application/pdf",
    }

    async def analyze_media_url(self, media_url: str, content_type: str) -> Dict[str, Any]:
        """Download and analyze a media file from a URL (e.g. Twilio media)."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(media_url)
                response.raise_for_status()
                content = response.content

            if len(content) > self.MAX_FILE_SIZE:
                return {
                    "document_type": "unknown",
                    "error": "File too large (max 5MB)",
                    "confidence": 0.0,
                    "suggested_action": "none",
                    "requires_confirmation": False,
                }

            return await self.analyze_content(content, content_type)
        except Exception as e:
            logger.error(f"Error downloading/analyzing media: {str(e)}")
            return {
                "document_type": "unknown",
                "error": "Could not download or analyze the document",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

    async def analyze_content(self, content: bytes, content_type: str) -> Dict[str, Any]:
        """Analyze document content bytes and extract financial data.

        Uses OpenAI Vision API for image analysis when available.
        Falls back to basic pattern matching for text-like content.
        """
        ct = content_type.lower().strip()

        if ct not in self.ALLOWED_CONTENT_TYPES:
            return {
                "document_type": "unknown",
                "error": f"Unsupported file type: {ct}. Allowed: PNG, JPG, WebP, PDF",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

        if len(content) > self.MAX_FILE_SIZE:
            return {
                "document_type": "unknown",
                "error": "File too large (max 5MB)",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

        try:
            if ct.startswith("image/"):
                return await self._analyze_image(content, ct)
            elif ct == "application/pdf":
                return await self._analyze_pdf(content)
            else:
                return {
                    "document_type": "unknown",
                    "error": "Unsupported file type",
                    "confidence": 0.0,
                    "suggested_action": "none",
                    "requires_confirmation": False,
                }
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            return {
                "document_type": "unknown",
                "error": "Analysis failed. Please try again or send the data as text.",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

    async def _analyze_image(self, content: bytes, content_type: str) -> Dict[str, Any]:
        """Analyze an image using OpenAI Vision API."""
        import base64
        from openai import AsyncOpenAI

        b64 = base64.b64encode(content).decode("utf-8")
        media_type = content_type  # e.g. "image/png"

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=30.0)

        prompt = """Analise esta imagem e extraia dados financeiros se houver.

Identifique:
- Tipo de documento: boleto, comprovante, nota, recibo, conta, ou unknown
- Valor (amount): valor numérico se visível
- Vencimento (due_date): formato YYYY-MM-DD se visível
- Descrição (description): descrição curta do documento
- Nome do recebedor/pagador (recipient_name): se visível

Responda APENAS com JSON válido:
{
    "document_type": "boleto_or_receipt",
    "amount": "150.00",
    "due_date": "2026-07-15",
    "description": "Conta detectada no documento",
    "recipient_name": "Empresa XYZ",
    "confidence": 0.85
}

Se não conseguir identificar algum campo, use null.
Se não for um documento financeiro, retorne confidence 0.0 e document_type "unknown"."""

        try:
            response = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{b64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            import json
            result = json.loads(response.choices[0].message.content)
            return self._build_analysis_result(result)
        except Exception as e:
            logger.error(f"OpenAI Vision analysis failed: {str(e)}")
            return {
                "document_type": "unknown",
                "error": "Could not analyze image with AI. Please send the data as text.",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

    async def _analyze_pdf(self, content: bytes) -> Dict[str, Any]:
        """Analyze a PDF by extracting text and looking for financial patterns."""
        try:
            import io
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""
            except ImportError:
                return {
                    "document_type": "unknown",
                    "error": "PDF analysis not available. Please send an image instead.",
                    "confidence": 0.0,
                    "suggested_action": "none",
                    "requires_confirmation": False,
                }

            if not text.strip():
                return {
                    "document_type": "unknown",
                    "error": "Could not extract text from PDF. It may be a scanned image.",
                    "confidence": 0.0,
                    "suggested_action": "none",
                    "requires_confirmation": False,
                }

            return self._extract_from_text(text)
        except Exception as e:
            logger.error(f"PDF analysis failed: {str(e)}")
            return {
                "document_type": "unknown",
                "error": "Could not analyze PDF. Please try sending an image.",
                "confidence": 0.0,
                "suggested_action": "none",
                "requires_confirmation": False,
            }

    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """Extract financial data from text using pattern matching."""
        result = {
            "document_type": "unknown",
            "amount": None,
            "due_date": None,
            "description": None,
            "recipient_name": None,
            "confidence": 0.0,
        }

        # Extract amount
        amount_patterns = [
            r'R\$\s*(\d+(?:[.,]\d{2})?)',
            r'(\d+(?:[.,]\d{2})?)\s*reais?',
            r'valor[:\s]+R\$\s*(\d+(?:[.,]\d{2})?)',
            r'total[:\s]+R\$\s*(\d+(?:[.,]\d{2})?)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '.')
                try:
                    result["amount"] = f"{float(amount_str):.2f}"
                    result["confidence"] = max(result["confidence"], 0.5)
                    break
                except ValueError:
                    continue

        # Extract due date
        date_patterns = [
            r'vencimento[:\s]+(\d{2}/\d{2}/\d{4})',
            r'vence[:\s]+(\d{2}/\d{2}/\d{4})',
            r'(\d{2}/\d{2}/\d{4})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    parsed = datetime.strptime(date_str, "%d/%m/%Y")
                    result["due_date"] = parsed.strftime("%Y-%m-%d")
                    result["confidence"] = max(result["confidence"], 0.5)
                    break
                except ValueError:
                    continue

        # Detect document type
        text_lower = text.lower()
        if "boleto" in text_lower:
            result["document_type"] = "boleto"
            result["confidence"] = max(result["confidence"], 0.6)
        elif "comprovante" in text_lower or "comprov" in text_lower:
            result["document_type"] = "comprovante"
            result["confidence"] = max(result["confidence"], 0.6)
        elif "recibo" in text_lower:
            result["document_type"] = "recibo"
            result["confidence"] = max(result["confidence"], 0.6)
        elif "nota fiscal" in text_lower or "nf" in text_lower:
            result["document_type"] = "nota_fiscal"
            result["confidence"] = max(result["confidence"], 0.6)
        elif result["amount"] or result["due_date"]:
            result["document_type"] = "conta"
            result["confidence"] = max(result["confidence"], 0.4)

        if result["amount"] and result["due_date"]:
            result["confidence"] = max(result["confidence"], 0.7)

        result["description"] = f"Documento detectado: {result['document_type']}"

        return self._build_analysis_result(result)

    def _build_analysis_result(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Build the final analysis result with suggested action."""
        confidence = float(raw.get("confidence", 0.0))
        doc_type = raw.get("document_type", "unknown")
        amount = raw.get("amount")
        due_date = raw.get("due_date")

        if confidence < 0.3 or doc_type == "unknown":
            suggested_action = "manual_review"
        elif amount and due_date:
            suggested_action = "create_reminder"
        elif amount:
            suggested_action = "create_reminder"
        else:
            suggested_action = "manual_review"

        return {
            "document_type": doc_type,
            "amount": amount,
            "due_date": due_date,
            "description": raw.get("description"),
            "recipient_name": raw.get("recipient_name"),
            "confidence": confidence,
            "suggested_action": suggested_action,
            "requires_confirmation": True,
        }

    def format_whatsapp_response(self, analysis: Dict[str, Any]) -> str:
        """Format the analysis result as a WhatsApp message."""
        if analysis.get("error"):
            return f"❌ {analysis['error']}"

        if analysis["confidence"] < 0.3:
            return "Recebi seu documento, mas não consegui identificar informações financeiras claras. Pode enviar os dados por texto?"

        doc_type_label = {
            "boleto": "Boleto",
            "comprovante": "Comprovante",
            "recibo": "Recibo",
            "nota_fiscal": "Nota Fiscal",
            "conta": "Conta",
            "unknown": "Documento",
        }.get(analysis["document_type"], "Documento")

        message = f"📄 Encontrei um possível *{doc_type_label}*:\n\n"

        if analysis.get("amount"):
            message += f"💰 Valor: R$ {analysis['amount']}\n"
        if analysis.get("due_date"):
            try:
                parsed = datetime.strptime(analysis["due_date"], "%Y-%m-%d")
                message += f"📅 Vencimento: {parsed.strftime('%d/%m/%Y')}\n"
            except ValueError:
                message += f"📅 Vencimento: {analysis['due_date']}\n"
        if analysis.get("description"):
            message += f"📝 Descrição: {analysis['description']}\n"
        if analysis.get("recipient_name"):
            message += f"👤 Recebedor: {analysis['recipient_name']}\n"

        confidence_pct = int(analysis["confidence"] * 100)
        message += f"\n🎯 Confiança: {confidence_pct}%\n"

        if analysis["suggested_action"] == "create_reminder":
            message += '\nDeseja criar um lembrete para essa data?\nResponda "sim" para confirmar ou "não" para cancelar.'
        elif analysis["suggested_action"] == "manual_review":
            message += "\nRecomendo revisar os dados manualmente. Pode enviar as informações por texto?"

        return message
