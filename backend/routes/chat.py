from flask import Blueprint, request, jsonify

bp = Blueprint("chat", __name__, url_prefix="/chat")

@bp.route("/", methods=["POST"])
def chat():
    data = request.get_json() or {}
    message = data.get("message", "")

    return jsonify({
        "reply": f"Demo response received: {message}"
    })