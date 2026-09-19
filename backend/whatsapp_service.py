"""
whatsapp_service.py
Handles all outbound communication with the Meta WhatsApp Cloud API.

============================================================
  >>> INSERT YOUR META DEVELOPER CREDENTIALS BELOW <<<
  Get these from https://developers.facebook.com/apps -> your app
  -> WhatsApp -> API Setup.
  It's strongly recommended to load these from environment
  variables (.env) rather than hardcoding them.
============================================================
"""
import os
import logging
import time
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("whatsapp_service")

# ---------------------------------------------------------------
# PLACEHOLDER CREDENTIALS - replace via .env file
# ---------------------------------------------------------------
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v19.0")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "YOUR_PHONE_NUMBER_ID_HERE")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "YOUR_PERMANENT_ACCESS_TOKEN_HERE")

WHATSAPP_API_URL = (
    f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
    f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
)


def is_simulation_mode() -> bool:
    """Check whether we should simulate message sending (e.g. In local development without Meta keys)."""
    return (
        WHATSAPP_ACCESS_TOKEN in ("YOUR_PERMANENT_ACCESS_TOKEN_HERE", "", None)
        or os.getenv("SIMULATE_WHATSAPP", "false").lower() in ("true", "1", "yes")
    )


def clean_phone_number(to_number: str) -> str:
    """Normalize phone numbers by stripping '+' and any non-digit characters."""
    return "".join(ch for ch in str(to_number or "") if ch.isdigit())


def send_whatsapp_text_message(to_number: str, message_text: str) -> dict:
    """
    Sends a freeform text WhatsApp message via Meta Cloud API.
    If the access token is the default placeholder, delivers in simulation mode.

    Args:
        to_number: Recipient's phone in E.164 without '+' (e.g. "919876543210").
        message_text: The freeform text message body.

    Returns:
        dict: {"success": bool, "status_code": int, "response": dict|str, "simulated": bool}
    """
    to_number = clean_phone_number(to_number)
    if is_simulation_mode():
        logger.info(
            "[WhatsApp Simulation] Sent text message to %s: %s",
            to_number,
            message_text[:60] + "..." if len(message_text) > 60 else message_text,
        )
        return {
            "success": True,
            "status_code": 200,
            "response": {
                "messages": [{"id": f"wamid.SIM_{to_number}_{int(time.time())}"}],
                "note": "Delivered in Demo/Simulation mode (set real Meta token in .env for live WhatsApp)",
            },
            "simulated": True,
        }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to_number,
        "type": "text",
        "text": {"preview_url": False, "body": message_text},
    }

    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        logger.info("WhatsApp text message sent to %s", to_number)
        return {"success": True, "status_code": response.status_code, "response": response.json(), "simulated": False}
    except requests.exceptions.HTTPError as http_err:
        logger.error("WhatsApp API HTTP error for %s: %s", to_number, http_err)
        return {
            "success": False,
            "status_code": getattr(response, "status_code", 500),
            "response": getattr(response, "text", str(http_err)),
            "simulated": False,
        }
    except requests.exceptions.RequestException as req_err:
        logger.error("WhatsApp API request failed for %s: %s", to_number, req_err)
        return {"success": False, "status_code": 500, "response": str(req_err), "simulated": False}


def send_whatsapp_template_message(
    to_number: str,
    template_name: str,
    language_code: str = "en_US",
    parameters: list[str] | None = None,
) -> dict:
    """
    Sends a pre-approved WhatsApp template message via the Meta Cloud API.

    Args:
        to_number: Recipient's number in E.164 format without '+' (e.g. "919876543210").
        template_name: Name of the approved template in Meta Business Manager
                        (e.g. "gst_reminder").
        language_code: Template language code (default "en_US").
        parameters: Ordered list of strings to fill the template's {{1}}, {{2}}... placeholders.

    Returns:
        dict: {"success": bool, "status_code": int, "response": dict|str, "simulated": bool}
    """
    to_number = clean_phone_number(to_number)
    if is_simulation_mode():
        logger.info(
            "[WhatsApp Simulation] Sent template '%s' to %s with params %s",
            template_name,
            to_number,
            parameters,
        )
        return {
            "success": True,
            "status_code": 200,
            "response": {
                "messages": [{"id": f"wamid.SIM_{to_number}_{int(time.time())}"}],
                "note": f"Template '{template_name}' simulated (set real Meta token in .env for live WhatsApp)",
            },
            "simulated": True,
        }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    components = []
    if parameters:
        components.append(
            {
                "type": "body",
                "parameters": [{"type": "text", "text": p} for p in parameters],
            }
        )

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
            "components": components,
        },
    }

    try:
        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        logger.info("WhatsApp message sent to %s using template '%s'", to_number, template_name)
        return {"success": True, "status_code": response.status_code, "response": response.json(), "simulated": False}
    except requests.exceptions.HTTPError as http_err:
        logger.error("WhatsApp API HTTP error for %s: %s", to_number, http_err)
        return {
            "success": False,
            "status_code": getattr(response, "status_code", 500),
            "response": getattr(response, "text", str(http_err)),
            "simulated": False,
        }
    except requests.exceptions.RequestException as req_err:
        logger.error("WhatsApp API request failed for %s: %s", to_number, req_err)
        return {"success": False, "status_code": 500, "response": str(req_err), "simulated": False}


def send_gst_reminder(to_number: str, business_name: str, days_left: int, due_date: str) -> dict:
    """Convenience wrapper for a GST reminder template message."""
    return send_whatsapp_template_message(
        to_number=to_number,
        template_name="gst_reminder",  # must match an approved template name in Meta
        parameters=[business_name, str(days_left), due_date],
    )


def send_document_request(to_number: str, business_name: str, doc_description: str) -> dict:
    """Convenience wrapper for a document-request template message."""
    return send_whatsapp_template_message(
        to_number=to_number,
        template_name="document_request",
        parameters=[business_name, doc_description],
    )


def send_billing_notification(to_number: str, business_name: str, invoice_number: str, amount: str) -> dict:
    """Convenience wrapper for a billing/invoice notification template message."""
    return send_whatsapp_template_message(
        to_number=to_number,
        template_name="billing_notification",
        parameters=[business_name, invoice_number, amount],
    )
