from flask import Flask, jsonify
from flask_cors import CORS
from backend.routes.chat import bp as chat_bp

app = Flask(__name__)
CORS(app)

# ✅ REGISTER CHAT ROUTES
app.register_blueprint(chat_bp)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "GuideMeAI backend running"}), 200