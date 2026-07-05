from flask import Flask, request, jsonify
import os
import re
import requests
from lxml import html

app = Flask(__name__)

URL = "https://www.eltiempo.es/vicalvaro.html"
TEMPERATURE_XPATH = "//span[contains(concat(' ', normalize-space(@class), ' '), ' c-tib-text ') and contains(concat(' ', normalize-space(@class), ' '), ' degrees ') and @data-temperature]"
KAPSO_API_KEY = os.getenv("KAPSO_API_KEY")


def clean_number(value: str) -> str:
    match = re.search(r"-?\d+(?:[,.]\d+)?", value)
    if not match:
        raise RuntimeError(f"No se encontró ningún número en el valor: {value!r}")
    return match.group(0).replace(",", ".")


def get_weather_number() -> str:
    response = requests.get(
        URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            )
        },
        timeout=30,
    )
    response.raise_for_status()

    document = html.fromstring(response.content)
    temperature_matches = document.xpath(TEMPERATURE_XPATH)

    if temperature_matches:
        value = temperature_matches[0].get("data-temperature") or temperature_matches[0].text_content()
        return clean_number(value.strip())

    raise RuntimeError("No se encontró la temperatura en ElTiempo.")


def send_whatsapp_text(to: str, phone_number_id: str, text: str):
    if not KAPSO_API_KEY:
        raise RuntimeError("Falta la variable de entorno KAPSO_API_KEY en Render.")

    url = f"https://api.kapso.ai/meta/whatsapp/v24.0/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }

    headers = {
        "X-API-Key": KAPSO_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    print("Respuesta Kapso:", response.status_code, response.text)
    response.raise_for_status()


@app.route("/", methods=["GET"])
def home():
    return "Bot de WhatsApp activo en Render", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(silent=True)

    print("Webhook recibido:")
    print(data)

    try:
        message = data.get("message", {})
        kapso_info = message.get("kapso", {})
        direction = kapso_info.get("direction")

        # Solo responder a mensajes entrantes
        if direction != "inbound":
            print("Mensaje ignorado porque no es inbound.")
            return jsonify({"status": "ignored"}), 200

        texto_original = message.get("text", {}).get("body", "")
        texto = texto_original.strip().lower()

        telefono_origen = message.get("from")
        phone_number_id = data.get("phone_number_id")

        print("Mensaje recibido:", texto_original)
        print("Teléfono origen:", telefono_origen)
        print("Phone number ID:", phone_number_id)

        if not texto:
            return jsonify({"status": "ok"}), 200

        if texto == "hola":
            respuesta = (
                "Hola José 👋\n\n"
                "Estoy activo en Render.\n"
                "Puedes probar con:\n\n"
                "clima"
            )

            send_whatsapp_text(
                to=telefono_origen,
                phone_number_id=phone_number_id,
                text=respuesta
            )

        elif texto.startswith("clima"):
            temperatura = get_weather_number()

            respuesta = (
                f"Temp Vicálvaro: {temperatura}°C"
            )

            send_whatsapp_text(
                to=telefono_origen,
                phone_number_id=phone_number_id,
                text=respuesta
            )

        else:
            respuesta = (
                "No he entendido el mensaje.\n\n"
                "De momento puedes escribir:\n"
                "hola\n"
                "clima"
            )

            send_whatsapp_text(
                to=telefono_origen,
                phone_number_id=phone_number_id,
                text=respuesta
            )

        return jsonify({"status": "ok"}), 200

    except Exception as e:
        print("ERROR en webhook:", e)
        return jsonify({"status": "error", "detail": str(e)}), 200
