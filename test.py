# from autopair_chatbot.utils import (
#     build_detailed_qualification_message,
#     set_surcharge_flags,
# )

# # ======= Sample Test Leads =======
# test_leads = [
#     {
#         "properties": {
#             "firstname": "John",
#             "vehicle_year": "2020",
#             "vehicle_make": "Audi",
#             "vehicle_model": "A4",
#             "vehicle_mileage": "70000",
#             "autopair_qualified_plans": "Works, Works Plus",
#             "phone": "+14165551234"
#         }
#     },
#     {
#         "properties": {
#             "firstname": "Jane",
#             "vehicle_year": "2021",
#             "vehicle_make": "BMW",
#             "vehicle_model": "M3",
#             "vehicle_mileage": "30000",
#             "autopair_qualified_plans": "Works, Works Plus",
#             "phone": "+14165556789"
#         }
#     },
#     {
#         "properties": {
#             "firstname": "Ali",
#             "vehicle_year": "2019",
#             "vehicle_make": "Toyota",
#             "vehicle_model": "Corolla",
#             "vehicle_mileage": "80000",
#             "autopair_qualified_plans": "Standard",
#             "phone": "+14165559876"
#         }
#     },
#     {
#         "properties": {
#             "firstname": "Sarah",
#             "vehicle_year": "2022",
#             "vehicle_make": "Porsche",
#             "vehicle_model": "911",
#             "vehicle_mileage": "15000",
#             "autopair_qualified_plans": "Works, Works Plus",
#             "phone": "+14165550000"
#         }
#     }
# ]

# # ======= Run Tests =======
# for lead in test_leads:
#     props = lead["properties"]
#     props = set_surcharge_flags(props)
#     message = build_detailed_qualification_message(props)

#     print("=" * 60)
#     print(f"Lead: {props.get('vehicle_make')} {props.get('vehicle_model')}")
#     print(f"Premium Surcharge: {props.get('premium_surcharge', False)}")
#     print(f"Exotic Surcharge: {props.get('exotic_surcharge', False)}\n")
#     print("Generated Message:\n")
#     print(message)
#     print("\n")



# test_question_submission.py

from autopair_chatbot.routes import handle_question_submission
from flask import Flask, request, jsonify
from flask.testing import FlaskClient
import json

# Create test Flask app
app = Flask(__name__)
app.testing = True

# Sample test client
client = app.test_client()

# Simulated lead from HubSpot (adjust as needed)
test_lead = {
    "id": "1234567890",
    "properties": {
        "firstname": "Ali",
        "phone": "+14165551234",
        "vehicle_year": "2020",
        "vehicle_make": "Audi",
        "vehicle_model": "A4",
        "vehicle_mileage": "70000",
        "autopair_qualified_plans": "Works Plan, Works Plus Plan"
    }
}

# Test question (Option 3 flow)
test_question = "What is included in the Works Plan?"

# Wrap testing in Flask route for simulation
@app.route("/test-submit-question", methods=["GET"])
def test_submit_question():
    with app.test_request_context():
        # Call your actual function
        response = handle_question_submission(test_lead, test_question)
        return response

# Run test manually
if __name__ == "__main__":
    with app.test_client() as test_client:
        response = test_client.get("/test-submit-question")
        print("\n📨 Test SMS Response:")
        print(json.dumps(response.json, indent=2))
