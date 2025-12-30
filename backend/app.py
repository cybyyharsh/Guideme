from flask import Flask, jsonify
from flask_cors import CORS
from backend.routes.chat import bp as chat_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(chat_bp)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "GuideMeAI backend running"})

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

@app.route("/routes", methods=["GET"])
def list_routes():
    return {
        "routes": [str(rule) for rule in app.url_map.iter_rules()]
    }