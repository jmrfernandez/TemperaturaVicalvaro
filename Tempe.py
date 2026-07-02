import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import requests
from lxml import html


URL = "https://www.eltiempo.es/vicalvaro.html"
XPATH = "/html/body/div[8]/div/div[4]/div/main/section[2]/section/article/div[2]/div[1]/span"
TEMPERATURE_XPATH = "//span[contains(concat(' ', normalize-space(@class), ' '), ' c-tib-text ') and contains(concat(' ', normalize-space(@class), ' '), ' degrees ') and @data-temperature]"
DEFAULT_KAPSO = r"C:\Users\rizquez\AppData\Roaming\npm\kapso.cmd"


def clean_number(value: str) -> str:
    match = re.search(r"-?\d+(?:[,.]\d+)?", value)
    if not match:
        raise RuntimeError(f"No se encontro ningun numero en el valor: {value!r}")
    return match.group(0).replace(",", ".")


def get_weather_number(url: str = URL, xpath: str = XPATH) -> str:
    response = requests.get(
        url,
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

    matches = document.xpath(xpath)
    if not matches:
        raise RuntimeError(
            "No se encontro el elemento de temperatura por clase "
            f"ni ningun elemento con el XPath: {xpath}"
        )

    value = matches[0].text_content().strip()
    if not value:
        raise RuntimeError("El elemento existe, pero no contiene texto.")

    return clean_number(value)


def find_kapso() -> str:
    return shutil.which("kapso") or shutil.which("kapso.cmd") or DEFAULT_KAPSO


def send_whatsapp_text(text: str, to: str, phone_number_id: str | None, phone_number: str | None) -> None:
    kapso = find_kapso()
    command = [
        kapso,
        "whatsapp",
        "messages",
        "send",
        "--to",
        to,
        "--text",
        text,
    ]

    if phone_number_id:
        command.extend(["--phone-number-id", phone_number_id])
    elif phone_number:
        command.extend(["--phone-number", phone_number])
    else:
        raise RuntimeError(
            "Falta KAPSO_PHONE_NUMBER_ID o KAPSO_PHONE_NUMBER. "
            "Kapso necesita saber desde que numero enviar."
        )

    subprocess.run(command, check=True)


def send_whatsapp_template(
    number: str,
    to: str,
    phone_number_id: str | None,
    phone_number: str | None,
    template_name: str,
    template_language: str,
) -> None:
    kapso = find_kapso()
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": template_language},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": number}],
                }
            ],
        },
    }

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as payload_file:
        json.dump(payload, payload_file, ensure_ascii=False)
        payload_path = payload_file.name

    command = [
        kapso,
        "whatsapp",
        "messages",
        "send",
        "--input",
        payload_path,
    ]

    if phone_number_id:
        command.extend(["--phone-number-id", phone_number_id])
    elif phone_number:
        command.extend(["--phone-number", phone_number])
    else:
        raise RuntimeError(
            "Falta KAPSO_PHONE_NUMBER_ID o KAPSO_PHONE_NUMBER. "
            "Kapso necesita saber desde que numero enviar."
        )

    try:
        subprocess.run(command, check=True)
    finally:
        try:
            os.unlink(payload_path)
        except OSError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lee un numero de eltiempo.es/vicalvaro.html y lo envia por WhatsApp usando Kapso."
    )
    parser.add_argument("--to", default=os.getenv("KAPSO_TO"), help="Telefono destinatario en formato internacional.")
    parser.add_argument(
        "--phone-number-id",
        default=os.getenv("KAPSO_PHONE_NUMBER_ID"),
        help="ID interno de Meta del numero de WhatsApp emisor.",
    )
    parser.add_argument(
        "--phone-number",
        default=os.getenv("KAPSO_PHONE_NUMBER"),
        help="Numero de WhatsApp emisor visible, si no usas phone-number-id.",
    )
    parser.add_argument("--url", default=URL, help="URL de la que leer el dato.")
    parser.add_argument("--xpath", default=XPATH, help="XPath exacto del dato.")
    parser.add_argument(
        "--template-name",
        default=os.getenv("KAPSO_TEMPLATE_NAME"),
        help="Nombre de una plantilla aprobada de WhatsApp. Si se indica, se envia template.",
    )
    parser.add_argument(
        "--template-language",
        default=os.getenv("KAPSO_TEMPLATE_LANGUAGE", "es"),
        help="Codigo de idioma de la plantilla. Por defecto: es.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.to:
        print("ERROR: falta --to o la variable de entorno KAPSO_TO.", file=sys.stderr)
        return 2

    try:
        number = get_weather_number(args.url, args.xpath)
        message = f"Numero actual en ElTiempo Vicalvaro: {number}"
        if args.template_name:
            send_whatsapp_template(
                number=number,
                to=args.to,
                phone_number_id=args.phone_number_id,
                phone_number=args.phone_number,
                template_name=args.template_name,
                template_language=args.template_language,
            )
        else:
            send_whatsapp_text(
                text=message,
                to=args.to,
                phone_number_id=args.phone_number_id,
                phone_number=args.phone_number,
            )
        print(f"Enviado por WhatsApp: {message}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
