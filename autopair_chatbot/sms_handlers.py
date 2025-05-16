# File: autopair_chatbot/sms_handlers.py
from flask import request, jsonify
from autopair_chatbot.utils import format_phone_number, is_schedule_text, get_ai_response, now_in_toronto, get_vehicle_info, send_sms
from autopair_chatbot.hubspot import find_lead_by_phone, update_lead_in_hubspot,create_call_task_in_hubspot

from datetime import time as dt_time
from autopair_chatbot.config import logger

def sms_webhook():
    from_number = request.form.get("From")
    body = request.form.get("Body", "").strip().lower()

    if not from_number:
        return jsonify({"status": "error", "message": "Missing phone"}), 400

    lead = find_lead_by_phone(from_number)
    if not lead:
        return jsonify({"status": "error", "message": "Lead not found"}), 404

    props = lead.get("properties", {})
    current_status = props.get("autopair_status", "")

    if body in ["1", "call now"]:
        return handle_call_request(lead)
    elif body in ["2", "schedule call"]:
        return handle_schedule_request(lead)
    elif body in ["3", "questions"]:
        return handle_question_request(lead)
    elif current_status == "Awaiting Schedule":
        if is_schedule_text(body):
            return handle_schedule_submission(lead, body)
        else:
            return handle_question_submission(lead, body)
    elif current_status == "Awaiting Question":
        return handle_question_submission(lead, body)
    else:
        return handle_question_submission(lead, body)


def handle_call_request(lead):
    props = lead.get("properties", {})
    phone = format_phone_number(props.get("phone", ""))
    first_name = props.get("firstname", "there")

    if not phone:
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400

    now = now_in_toronto()
    is_weekday = now.weekday() < 5  # Monday to Friday
    is_within_hours = dt_time(9, 0) <= now.time() <= dt_time(20, 0)  # 9 AM to 8 PM EST

    if is_weekday and is_within_hours:
        # ✅ Within business hours — confirm and create HubSpot Task
        send_sms(phone, "Great! One of our warranty specialists will give you a call shortly. Please keep your phone handy.")

        update_lead_in_hubspot(lead["id"], {
            "properties": {
                "autopair_status": "Call Requested",
                "autopair_last_response": now.isoformat()
            }
        })

        # Create HubSpot Task
        create_call_task_in_hubspot(lead, now.strftime("%A %I:%M %p"))

        return jsonify({"status": "success", "action": "Call task created"})

    else:
        # ❌ Outside business hours — prompt to schedule
        send_sms(phone,
            "Thanks for your interest! Our team has gone home for the day. "
            "We operate Monday to Friday from 9:00 AM to 8:00 PM (EST Toronto time).\n\n"
            "Would you like us to give you a call tomorrow during those hours?\n"
            "If yes, let us know what time works best for you.\n"
            "If not, tell us what day of the week works better for you."
        )

        update_lead_in_hubspot(lead["id"], {
            "properties": {
                "autopair_status": "Awaiting Schedule",
                "autopair_last_response": now.isoformat()
            }
        })

        return jsonify({"status": "awaiting_schedule"})


def handle_schedule_request(lead):
    phone = format_phone_number(lead.get("properties", {}).get("phone"))
    send_sms(phone, "Sure! Please let me know what date and time you'd like to speak with a warranty specialist.\nWe're available Monday to Friday, from 9:00 AM to 8:00 PM (EST Toronto time). Just reply with a time that works best for you.")
    update_lead_in_hubspot(lead["id"], {
        "properties": {
            "autopair_status": "Awaiting Schedule",
            "autopair_last_response": now_in_toronto().isoformat()
        }
    })
    return jsonify({"status": "success", "action": "Schedule requested"})


def handle_question_request(lead):
    phone = format_phone_number(lead.get("properties", {}).get("phone"))
    send_sms(phone, "Absolutely, I’m here to help!\nWhat would you like to know more about?")

    update_lead_in_hubspot(lead["id"], {
        "properties": {
            "autopair_status": "Awaiting Question",
            "autopair_last_response": now_in_toronto().isoformat()
        }
    })
    return jsonify({"status": "success", "action": "Question requested"})



# def handle_schedule_submission(lead, schedule_text):
#     from autopair_chatbot.utils import parse_schedule_text

#     phone = format_phone_number(lead.get("properties", {}).get("phone"))
#     scheduled_time = parse_schedule_text(schedule_text)

#     if scheduled_time:
#         formatted_time = scheduled_time.strftime("%A, %B %d at %I:%M %p")
#         send_sms(phone, f"Thank you! We've scheduled your callback for {formatted_time} (Eastern Time).")
#         update_data = {
#             "properties": {
#                 "autopair_status": "Call Scheduled",
#                 "autopair_scheduled_time": int(scheduled_time.timestamp() * 1000),
#                 "autopair_last_response": now_in_toronto().isoformat()
#             }
#         }
#     else:
#         send_sms(phone, "I didn't understand that time. Please try again (e.g. 'Friday 2pm').")
#         update_data = {
#             "properties": {
#                 "autopair_last_response": now_in_toronto().isoformat()
#             }
#         }

#     update_lead_in_hubspot(lead["id"], update_data)
#     return jsonify({"status": "success"})

def handle_schedule_submission(lead, schedule_text):
    from autopair_chatbot.utils import parse_schedule_text
    from datetime import time as dt_time

    phone = format_phone_number(lead.get("properties", {}).get("phone"))
    scheduled_time = parse_schedule_text(schedule_text)

    if not scheduled_time:
        if any(phrase in schedule_text.lower() for phrase in ["not sure", "maybe", "idk", "i don't know"]):
            send_sms(phone, "No problem! Would you prefer a call in the morning, afternoon, or evening? I’ll share some available time slots.\n\nReply with one:\n• Morning (9 AM–12 PM)\n• Afternoon (12 PM–4 PM)\n• Evening (4 PM–8 PM)")
        else:
            send_sms(phone, "Thanks! Just a heads-up we’re only available Monday to Friday from 9:00 AM to 8:00 PM (EST Toronto time).\nCould you send a new time within those hours?")
        return jsonify({"status": "invalid_time"})

    weekday = scheduled_time.weekday()  # 0 = Monday, 6 = Sunday
    hour = scheduled_time.hour
    minute = scheduled_time.minute

    # Validate: weekday Mon–Fri and between 9am–8pm
    if weekday >= 5 or not (9 <= hour < 20 or (hour == 20 and minute == 0)):
        send_sms(phone, "Thanks! Just a heads-up we’re only available Monday to Friday from 9:00 AM to 8:00 PM (EST Toronto time).\nCould you send a new time within those hours?")
        return jsonify({"status": "invalid_time"})

    formatted_time = scheduled_time.strftime("%A, %B %d at %I:%M %p")
    send_sms(phone, f"Great! I’ve scheduled your call for {formatted_time} (EST Toronto time).\nOne of our specialists will contact you then. If you need to reschedule, just message us here.")

    update_data = {
        "properties": {
            "autopair_status": "Call Scheduled",
            "autopair_scheduled_time": int(scheduled_time.timestamp() * 1000),
            "autopair_last_response": now_in_toronto().isoformat()
        }
    }

    update_lead_in_hubspot(lead["id"], update_data)
    return jsonify({"status": "success"})

def handle_question_submission(lead, question):
    props = lead.get("properties", {})
    phone = format_phone_number(props.get("phone", ""))

    if not phone:
        return jsonify({"status": "error", "message": "Invalid phone number"}), 400

    context = f"Customer: {props.get('firstname', '')}, Vehicle: {props.get('vehicle_year', '')} {props.get('vehicle_make', '')} {props.get('vehicle_model', '')}, Qualified plans: {props.get('autopair_qualified_plans', 'Unknown')}"

    # 🔍 Force fallback if question is vague, confusing, or silly
    lower_question = question.strip().lower()
    force_fallback = any(
        phrase in lower_question
        for phrase in [
            "idk", "i don't know", "not sure", "maybe", "confused",
            "no idea", "help me", "can't decide",
            "cat drives", "cat driving", "what if my cat",
            "dog drives", "pet driving", "can my pet",
            "i'm lost", "don't understand", "talk to someone"
        ]
    )

    ai_response = get_ai_response(question, context)

    if (
        force_fallback
        or not ai_response
        or "trouble" in ai_response.lower()
        or "not sure" in ai_response.lower()
        or "can't answer" in ai_response.lower()
        or "unsure" in ai_response.lower()
        or "not confident" in ai_response.lower()
        or "you should talk to" in ai_response.lower()
    ):
        ai_response = (
            "That’s a great question! I want to make sure you get the most accurate answer.\n"
            "Would you like one of our warranty specialists to give you a quick call and walk you through everything?\n\n"
            "1️⃣ Call me now\n2️⃣ Schedule a call"
        )

        update_lead_in_hubspot(lead["id"], {
            "properties": {
                "autopair_status": "Awaiting Schedule",
                "autopair_last_question": question,
                "autopair_last_response": int(now_in_toronto().timestamp() * 1000)
            }
        })
    else:
        update_lead_in_hubspot(lead["id"], {
            "properties": {
                "autopair_status": "Question Answered",
                "autopair_last_question": question,
                "autopair_last_response": int(now_in_toronto().timestamp() * 1000)
            }
        })

    send_sms(phone, ai_response)
    return jsonify({"status": "success", "response": ai_response})
