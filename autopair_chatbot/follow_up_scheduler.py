# File: follow_up_scheduler.py
from datetime import datetime, timedelta
from autopair_chatbot.config import logger
from autopair_chatbot.utils import now_in_toronto, send_sms, format_phone_number
from autopair_chatbot.hubspot import fetch_lead_details, update_lead_in_hubspot
import requests

HOURS_THRESHOLD = 6

def fetch_unresponsive_leads():
    """Fetch leads from HubSpot that are awaiting question response for more than 6 hours."""
    url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
    from autopair_chatbot.config import HUBSPOT_API_KEY

    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_KEY}",
        "Content-Type": "application/json"
    }

    filter_time = int((now_in_toronto() - timedelta(hours=HOURS_THRESHOLD)).timestamp() * 1000)

    body = {
        "filterGroups": [{
            "filters": [
                {"propertyName": "autopair_status", "operator": "EQ", "value": "Awaiting Question"},
                {"propertyName": "autopair_last_response", "operator": "LT", "value": str(filter_time)}
            ]
        }],
        "properties": [
            "firstname", "vehicle_year", "vehicle_make", "vehicle_model", "phone", "autopair_status", "autopair_last_response"
        ],
        "limit": 10
    }

    try:
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        logger.error(f"❌ Failed to fetch unresponsive leads: {e}")
        return []


def send_follow_up(lead):
    props = lead.get("properties", {})
    phone = format_phone_number(props.get("phone", ""))
    if not phone:
        logger.warning(f"⚠️ Invalid phone for lead {lead.get('id')}")
        return False

    follow_up_msg = f"""Hi {props.get('firstname', 'there')}, just wanted to follow up regarding your Autopair Warranty inquiry.

Based on the information you submitted, your {props.get('vehicle_year')} {props.get('vehicle_make')} {props.get('vehicle_model')} qualifies for coverage and we’d love to help protect it.

If you’re still interested, we can walk you through the options, answer any questions, or schedule a quick call at your convenience.

Would you like:
1️⃣ Our warranty specialist to give you a call now  
2️⃣ Schedule a time to speak to our warranty specialist  
3️⃣ Ask a few questions first

Please reply with 1, 2, or 3, and I’ll assist you right away. Looking forward to helping you protect your vehicle!
"""

    logger.info(f"📩 Sending follow-up to {phone}")
    success = send_sms(phone, follow_up_msg)

    if success:
        update_lead_in_hubspot(lead["id"], {
            "properties": {
                "autopair_last_response": int(now_in_toronto().timestamp() * 1000)
            }
        })

    return success


def run_follow_up_scheduler():
    leads = fetch_unresponsive_leads()
    if not leads:
        print("✅ No unresponsive leads found.")
    for lead in leads:
        send_follow_up(lead)
