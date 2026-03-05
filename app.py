from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import joblib
import numpy as np
import pandas as pd
import bcrypt
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = MongoClient(os.getenv("MONGO_URI"))
db = client["agriai"]

users_collection = db["users"]
detections_collection = db["detections"]

rf = joblib.load("model.joblib")
scaler = joblib.load("scaler.pkl")
le = joblib.load("label_encoder.pkl")

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

    if predicted_label == "Water Stress - Drought":
        recommendations.append("Increase irrigation gradually.")
        recommendations.append("Use drip irrigation.")

    elif predicted_label == "Water Stress - Waterlogging":
        recommendations.append("Improve drainage.")
        recommendations.append("Avoid irrigation.")

    elif predicted_label == "Temperature Stress - Heat":
        recommendations.append("Use shading nets.")
        recommendations.append("Apply anti-transpirant spray.")

    elif predicted_label == "Temperature Stress - Cold":
        recommendations.append("Use protective covers.")
        recommendations.append("Adjust irrigation timing.")

    elif predicted_label == "Soil & Chemical Stress - pH Imbalance":
        recommendations.append("Conduct soil testing.")
        recommendations.append("Apply lime or sulfur.")

    elif predicted_label == "Soil & Chemical Stress - Nutrient Deficiency":
        recommendations.append("Apply organic compost.")
        recommendations.append("Check micronutrients.")

    else:
        recommendations.append("Crop condition healthy.")
        recommendations.append("Maintain monitoring.")

    return recommendations


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/home")
def home():
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

    if users_collection.find_one({"email": email}):
        return jsonify({"success": False, "message": "User already exists"})

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed.decode()
    })

    return jsonify({"success": True})


@app.route("/login", methods=["POST"])
def login():

    data = request.json

    email = data["email"]
    password = data["password"]

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"success": False, "message": "Invalid email or password"})

    if bcrypt.checkpw(password.encode(), user["password"].encode()):
        return jsonify({"success": True, "email": email})

    return jsonify({"success": False, "message": "Invalid email or password"})


@app.route("/predict", methods=["POST"])
def predict():

    data = request.json

    email = data["email"]

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
        SAVI,Temperature,Humidity,Rainfall,Wind_Speed,
        Soil_Moisture,Soil_pH,Organic_Matter,Water_Flow,
        Moisture_Temp_Interaction,NDVI_Temp_Ratio,
        pH_Deviation,Moisture_Deviation,
        High_Temp_Flag,Low_Temp_Flag,Extreme_Heat
    ]

    df = pd.DataFrame([row], columns=features)
    df_scaled = scaler.transform(df)

    probs = rf.predict_proba(df_scaled)
    pred = rf.predict(df_scaled)

    predicted_label = le.inverse_transform(pred)[0]
    confidence = float(np.max(probs))

    severity_score = (1 - confidence) * 100

    severity_label = "Low"
    if severity_score > 60:
        severity_label = "High"
    elif severity_score > 30:
        severity_label = "Medium"

    recommendations = generate_recommendation(predicted_label, confidence)

    detections_collection.insert_one({
        "email": email,
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


@app.route("/history/<email>")
def history(email):

    predictions = list(
        detections_collection.find({"email": email}).sort("timestamp",-1)
    )

    for p in predictions:
        p["_id"] = str(p["_id"])

    return jsonify(predictions)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)