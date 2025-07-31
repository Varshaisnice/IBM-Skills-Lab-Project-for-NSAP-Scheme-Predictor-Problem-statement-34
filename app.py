from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# 🔑 Replace with your actual IBM Cloud credentials
API_KEY = "Zn-6XI7s8NDzJlOjS9Ae4-VDy-tbVoxy4CgNVwp_FlFy"
DEPLOYMENT_URL = "https://eu-gb.ml.cloud.ibm.com/ml/v4/deployments/226586f7-98cb-42c8-b5c3-e82d24ebbeb1/predictions?version=2021-05-01"

def get_token():
    url = "https://iam.cloud.ibm.com/identity/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = f"apikey={API_KEY}&grant_type=urn:ibm:params:oauth:grant-type:apikey"

    try:
        res = requests.post(url, headers=headers, data=data)
        res.raise_for_status()  # Raise exception for HTTP errors
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

        values = [[input_data.get(field) for field in fields]]

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
        response.raise_for_status()  # Raises HTTPError if request failed

        result = response.json()
        prediction = result["predictions"][0]["values"][0][0]

        return jsonify({"scheme": prediction})

    except Exception as e:
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
