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

    mensaje = ""
    telefono = ""

    try:
        mensaje = data["message"]["text"]["body"]
        telefono = data["message"]["from"]
    except Exception as e:
        print("No se pudo extraer el mensaje:", e)

    print("Mensaje recibido:", mensaje)
    print("Teléfono origen:", telefono)

    if mensaje:
        texto = mensaje.strip().lower()

        if texto == "hola":
            print("El usuario ha saludado")

        elif texto.startswith("clima"):
            ciudad = texto.replace("clima", "").strip()
            print("Ciudad solicitada:", ciudad)

        else:
            print("Mensaje no reconocido")

    return jsonify({"status": "ok"}), 200
