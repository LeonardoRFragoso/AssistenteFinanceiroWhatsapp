from twilio.rest import Client
from twilio.request_validator import RequestValidator
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class TwilioWhatsAppService:
    def __init__(self):
        auth_token = settings.TWILIO_AUTH_TOKEN or "dummy-token-for-init"
        account_sid = settings.TWILIO_ACCOUNT_SID or "dummy-sid"
        self.client = Client(account_sid, auth_token)
        self.validator = RequestValidator(auth_token)
        self.whatsapp_number = settings.TWILIO_WHATSAPP_NUMBER
    
    def validate_request(self, url: str, params: dict, signature: str) -> bool:
        try:
            return self.validator.validate(url, params, signature)
        except Exception as e:
            logger.error(f"Error validating Twilio request: {str(e)}")
            return False
    
    async def send_message(self, to_number: str, message: str) -> bool:
        try:
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            message_obj = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_number
            )
            
            logger.info(f"Message sent to {to_number}: {message_obj.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            return False
    
    async def send_template_message(
        self, 
        to_number: str, 
        template_name: str, 
        variables: Optional[dict] = None
    ) -> bool:
        try:
            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"
            
            message_obj = self.client.messages.create(
                from_=self.whatsapp_number,
                to=to_number,
                content_sid=template_name,
                content_variables=variables or {}
            )
            
            logger.info(f"Template message sent to {to_number}: {message_obj.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending template message: {str(e)}")
            return False
    
    def extract_phone_number(self, whatsapp_from: str) -> str:
        return whatsapp_from.replace("whatsapp:", "")
    
    def format_phone_number(self, phone: str) -> str:
        if not phone.startswith("+"):
            phone = f"+{phone}"
        return phone.replace(" ", "").replace("-", "")
