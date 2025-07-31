from flask import Flask, request, jsonify, render_template
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Retrieve IBM Cloud credentials from environment variables
API_KEY = os.getenv("IBM_API_KEY")
DEPLOYMENT_URL = os.getenv("IBM_DEPLOYMENT_URL")

# Validate environment variables
if not API_KEY or not DEPLOYMENT_URL:
    raise ValueError("Missing required environment variables: IBM_API_KEY or IBM_DEPLOYMENT_URL")

# Eligibility criteria for NSAP schemes (example, expand as needed)
ELIGIBILITY_CRITERIA = {
    "IGNOAPS": "Age 60+ years, BPL household, no regular income source.",
    "IGNWPS": "Widow aged 40-79 years, BPL household.",
    "IGNDPS": "Persons with severe disabilities, aged 18-79 years, BPL household.",
    "NSAP": "General NSAP eligibility: BPL household, no other pension support."
}

def get_token():
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = f"apikey={API_KEY}&grant_type=urn:ibm:params:oauth:grant-type:apikey"

    try:
        res = requests.post(url, headers=headers, data=data)
        res.raise_for_status()
        json_data = res.json()
        access_token = json_data.get("access_token")
        if access_token:
            return access_token
        else:
            print("Access token not found. Full response:", json_data)
            return None
    except Exception as e:
        print("Error getting token:", e)
        return None

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        input_data = request.get_json()

        fields = [
            "finyear", "lgdstatecode", "statename", "lgddistrictcode",
            "districtname", "totalbeneficiaries", "totalmale", "totalfemale",
            "totaltransgender", "totalsc", "totalst", "totalgen", "totalobc",
            "totalaadhaar", "totalmobilenumber"
        ]

        # Ensure all fields are provided, set defaults to 0 for numeric fields if missing
        values = [[input_data.get(field, 0 if field not in ["statename", "districtname"] else "") for field in fields]]

        payload = {
            "input_data": [{
                "fields": fields,
                "values": values
            }]
        }

        token = get_token()
        if not token:
            return jsonify({"error": "Failed to retrieve IBM Cloud access token"}), 500

        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(DEPLOYMENT_URL, json=payload, headers=headers)
        response.raise_for_status()

        result = response.json()
        prediction_data = result["predictions"][0]["values"][0]
        prediction = prediction_data[0]  # Predicted scheme
        probabilities = prediction_data[1] if len(prediction_data) > 1 else [1.0]  # Probabilities (if available)
        
        # Calculate confidence score (highest probability)
        confidence_score = max(probabilities) * 100 if probabilities else 100.0
        
        # Get eligibility criteria
        eligibility = ELIGIBILITY_CRITERIA.get(prediction, "No eligibility criteria available.")

        return jsonify({
            "scheme": prediction,
            "confidence_score": f"{confidence_score:.2f}%",
            "eligibility_criteria": eligibility
        })

    except Exception as e:
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
