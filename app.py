import pickle
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import joblib
import numpy as np
import pandas as pd
import bcrypt
from datetime import datetime

app = Flask(__name__)

client = MongoClient("mongodb+srv://agriai:agriai123@cluster0.c7rqeds.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
db = client["agriai"]

users_collection = db["users"]
detections_collection = db["detections"]

rf = joblib.load("model.joblib")
scaler = pickle.load(open("scaler.pkl", "rb"))
le = pickle.load(open("label_encoder.pkl", "rb"))
normal_moisture = 50

features = [
"SAVI","Temperature","Humidity",
"Rainfall","Wind_Speed","Soil_Moisture",
"Soil_pH","Organic_Matter","Water_Flow",
"Moisture_Temp_Interaction",
"NDVI_Temp_Ratio",
"pH_Deviation",
"Moisture_Deviation",
"High_Temp_Flag",
"Low_Temp_Flag",
"Extreme_Heat"
]

def generate_recommendation(predicted_label, confidence):

    recommendations = []

    if confidence < 0.35:
        recommendations.append("Model confidence is low. Field inspection recommended.")

    if "Drought" in predicted_label:
        recommendations.append("Increase irrigation gradually.")
        recommendations.append("Use drip irrigation to conserve water.")

    if "Waterlogging" in predicted_label:
        recommendations.append("Improve drainage system immediately.")
        recommendations.append("Avoid further irrigation.")

    if "Heat" in predicted_label:
        recommendations.append("Use shading nets or mulching.")
        recommendations.append("Apply anti-transpirant spray.")

    if "Cold" in predicted_label:
        recommendations.append("Use protective covers or greenhouse methods.")
        recommendations.append("Adjust irrigation timing.")

    if "pH Imbalance" in predicted_label:
        recommendations.append("Conduct soil testing.")
        recommendations.append("Apply lime or sulfur.")

    if "Nutrient Deficiency" in predicted_label:
        recommendations.append("Apply organic compost.")
        recommendations.append("Check micronutrient levels.")

    if "Atmospheric" in predicted_label:
        recommendations.append("Monitor sunlight exposure.")

    if len(recommendations) == 0:
        recommendations.append("Crop condition appears healthy.")
        recommendations.append("Maintain monitoring.")

    return recommendations

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home_page():
    return render_template("home.html")

@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/detection")
def detection():
    return render_template("detection.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/signup", methods=["POST"])
def signup():

    data = request.json

    name = data["name"]
    email = data["email"]
    password = data["password"]

    existing_user = users_collection.find_one({"email": email})

    if existing_user:
        return jsonify({"success": False, "message": "User already exists"})

    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password.decode("utf-8")
    })

    return jsonify({"success": True, "redirect": "/home"})

@app.route("/login", methods=["POST"])
def login():

    data = request.json

    email = data["email"]
    password = data["password"]

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"success": False, "message": "Invalid email or password"})

    if bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
        return jsonify({"success": True, "redirect": "/home"})
    else:
        return jsonify({"success": False, "message": "Invalid email or password"})

@app.route("/predict", methods=["POST"])
def predict():

    data = request.json

    SAVI = float(data["SAVI"])
    Temperature = float(data["Temperature"])
    Humidity = float(data["Humidity"])
    Rainfall = float(data["Rainfall"])
    Wind_Speed = float(data["Wind_Speed"])
    Soil_Moisture = float(data["Soil_Moisture"])
    Soil_pH = float(data["Soil_pH"])
    Organic_Matter = float(data["Organic_Matter"])
    Water_Flow = float(data["Water_Flow"])
    NDVI = float(data["NDVI"])

    Moisture_Temp_Interaction = Soil_Moisture * Temperature
    NDVI_Temp_Ratio = NDVI / (Temperature + 1)
    pH_Deviation = abs(Soil_pH - 7)
    Moisture_Deviation = abs(Soil_Moisture - normal_moisture)

    High_Temp_Flag = 1 if Temperature > 35 else 0
    Low_Temp_Flag = 1 if Temperature < 10 else 0
    Extreme_Heat = 1 if Temperature > 40 else 0

    row = [
        SAVI,Temperature,Humidity,
        Rainfall,Wind_Speed,Soil_Moisture,
        Soil_pH,Organic_Matter,Water_Flow,
        Moisture_Temp_Interaction,
        NDVI_Temp_Ratio,
        pH_Deviation,
        Moisture_Deviation,
        High_Temp_Flag,
        Low_Temp_Flag,
        Extreme_Heat
    ]

    df = pd.DataFrame([row], columns=features)

    df_scaled = pd.DataFrame(
        scaler.transform(df),
        columns=features
    )

    probs = rf.predict_proba(df_scaled)
    pred_class = rf.predict(df_scaled)

    predicted_label = le.inverse_transform(pred_class)[0]
    confidence = float(np.max(probs))

    if Temperature > 40 and Soil_Moisture < 30:
        predicted_label = "Combined Stress - Heat & Drought"
        confidence = max(confidence, 0.65)

    elif Soil_Moisture < 25 and Rainfall < 50:
        predicted_label = "Water Stress - Severe Drought"
        confidence = max(confidence, 0.70)

    elif Soil_Moisture > 80 and Rainfall > 200:
        predicted_label = "Water Stress - Waterlogging"
        confidence = max(confidence, 0.70)

    elif Temperature > 38 and Humidity < 30:
        predicted_label = "Temperature Stress - Extreme Heat"
        confidence = max(confidence, 0.65)

    elif Soil_pH < 5.5 or Soil_pH > 8:
        predicted_label = "Soil & Chemical Stress - pH Imbalance"
        confidence = max(confidence, 0.70)

    severity_score = (1 - confidence) * 100

    if severity_score < 30:
        severity_label = "Low"
    elif severity_score < 60:
        severity_label = "Medium"
    else:
        severity_label = "High"

    recommendations = generate_recommendation(predicted_label, confidence)

    detections_collection.insert_one({

        "SAVI": SAVI,
        "Temperature": Temperature,
        "Humidity": Humidity,
        "Rainfall": Rainfall,
        "Wind_Speed": Wind_Speed,
        "Soil_Moisture": Soil_Moisture,
        "Soil_pH": Soil_pH,
        "Organic_Matter": Organic_Matter,
        "Water_Flow": Water_Flow,
        "NDVI": NDVI,

        "stress_type": predicted_label,
        "confidence": round(confidence,3),
        "severity_score": round(severity_score,2),
        "severity_level": severity_label,
        "recommendations": recommendations,

        "timestamp": datetime.now()

    })

    return jsonify({

        "stress_type": predicted_label,
        "confidence": round(confidence,3),
        "severity_score": round(severity_score,2),
        "severity_level": severity_label,
        "recommendations": recommendations

    })

@app.route("/history")
def history():

    predictions = list(detections_collection.find().sort("timestamp",-1))

    for p in predictions:
        p["_id"] = str(p["_id"])

    return jsonify(predictions)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)