# main.py
import os
from dotenv import load_dotenv
from flask import Flask
import logging
from autopair_chatbot import sms_handlers, hubspot, lead_monitor
from threading import Thread
from autopair_chatbot.follow_up_scheduler import run_follow_up_scheduler
import time


load_dotenv()
app = Flask(__name__)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.route("/sms-webhook", methods=["POST"])
def sms_webhook_route():
    return sms_handlers.sms_webhook()

@app.route("/hubspot-webhook", methods=["POST"])
def hubspot_webhook_route():
    return hubspot.hubspot_webhook()


if __name__ == "__main__":
    lead_monitor.start_lead_monitor()

    # Start follow-up scheduler in background
    def schedule_loop():
        while True:
            try:
                run_follow_up_scheduler()
            except Exception as e:
                logger.error(f"❌ Follow-up scheduler crashed: {e}")
            time.sleep(3600)  # Wait 1 hour between runs

    Thread(target=schedule_loop, daemon=True).start()
    
    app.run(host="0.0.0.0", port=5000)
