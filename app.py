from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo en Render", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    print("Webhook recibido:")
    print(data)

    return jsonify({"status": "ok"}), 200
