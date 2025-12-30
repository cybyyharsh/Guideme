from flask import Flask, jsonify
from flask_cors import CORS
from routes.chat import bp as chat_bp
from routes.auth import bp as auth_bp
from routes.map import bp as map_bp

def create_app():
    app = Flask(__name__)

    CORS(
        app,
        resources={r"/api/*": {"origins": ["http://127.0.0.1:5500"]}},
        supports_credentials=True
    )

    app.register_blueprint(chat_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(map_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})


    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)