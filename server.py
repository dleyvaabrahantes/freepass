import os
import json
import shutil
import uuid
import hashlib
import subprocess
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

CERTS_PATH = "certificates"
TEMPLATE_PATH = "template"
OUTPUT_PATH = "passes"
os.makedirs(OUTPUT_PATH, exist_ok=True)

@app.route("/generate-pass", methods=["POST"])
def generate_pass():
    data = request.json
    nombre = data.get("nombre")
    telefono = data.get("telefono")
    qr = data.get("qr")

    if not all([nombre, telefono, qr]):
        return jsonify({"error": "Faltan datos"}), 400

    serial = str(uuid.uuid4())
    pass_dir = os.path.join(OUTPUT_PATH, serial)
    os.makedirs(pass_dir, exist_ok=True)

    # Copiar imágenes desde plantilla
    for file in ["icon.png", "logo.png"]:
        shutil.copy(os.path.join(TEMPLATE_PATH, file), os.path.join(pass_dir, file))

    # Crear pass.json
    pass_json = {
        "formatVersion": 1,
        "passTypeIdentifier": "pass.com.tuempresa.tarjeta",
        "serialNumber": serial,
        "teamIdentifier": "TU_TEAM_ID",
        "organizationName": "FrutiRico",
        "description": "Tarjeta de Fidelidad",
        "foregroundColor": "rgb(255,255,255)",
        "backgroundColor": "rgb(0,122,255)",
        "storeCard": {
            "primaryFields": [
                {"key": "nombre", "label": "Nombre", "value": nombre}
            ],
            "secondaryFields": [
                {"key": "telefono", "label": "Teléfono", "value": telefono}
            ]
        },
        "barcode": {
            "format": "PKBarcodeFormatQR",
            "message": qr,
            "messageEncoding": "iso-8859-1"
        }
    }

    with open(os.path.join(pass_dir, "pass.json"), "w") as f:
        json.dump(pass_json, f, indent=4)

    # Crear manifest.json con hashes SHA1
    manifest = {}
    for file in os.listdir(pass_dir):
        path = os.path.join(pass_dir, file)
        with open(path, "rb") as f:
            manifest[file] = hashlib.sha1(f.read()).hexdigest()

    with open(os.path.join(pass_dir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=4)

    # Firmar el manifest.json
    signature_path = os.path.join(pass_dir, "signature")
    subprocess.run([
        "openssl", "smime", "-binary", "-sign",
        "-certfile", f"{CERTS_PATH}/wwdr.pem",
        "-signer", f"{CERTS_PATH}/certificate.pem",
        "-inkey", f"{CERTS_PATH}/key.pem",
        "-in", os.path.join(pass_dir, "manifest.json"),
        "-out", signature_path,
        "-outform", "DER",
        "-nodetach"
    ], check=True)

    # Comprimir todo como .pkpass
    pkpass_path = os.path.join(OUTPUT_PATH, f"{serial}.pkpass")
    shutil.make_archive(pkpass_path.replace(".pkpass", ""), 'zip', pass_dir)
    os.rename(pkpass_path.replace(".pkpass", "") + ".zip", pkpass_path)

    return send_file(pkpass_path, mimetype="application/vnd.apple.pkpass")

if __name__ == "__main__":
    app.run(debug=True)
