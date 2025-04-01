import express from "express";
import bodyParser from "body-parser";
import fs from "fs";
import { PKPass } from "passkit-generator";

const app = express();
app.use(bodyParser.json());

// Cargar certificados
function loadCertificates() {
    return {
        wwdr: fs.readFileSync("certs/wwdr.pem"),
        signerCert: fs.readFileSync("certs/cert.pem"),
        signerKey: fs.readFileSync("certs/key.pem"),
        signerKeyPassphrase: "pass"
    };
}

function formatearEnBloquesDe4(valor) {
    return valor.replace(/(.{4})/g, "$1 ").trim();
}

// Ruta para generar el pase
app.post("/generar-pase", async (req, res) => {
    try {
        const { nombre, telefono, tarjeta } = req.body;
        const certificates = loadCertificates();
        console.log("🟢 Datos recibidos:");
        console.log("Nombre:", nombre);
        console.log("Teléfono:", telefono);
        console.log("Tarjeta:", tarjeta);

        const pass = await PKPass.from({
            model: "./pass/Model/Generic.pass",
            certificates
        }, {
            serialNumber: Date.now().toString(),
            description: "CubaMoney",
            organizationName: "CubaMoney",
            // fields: {
            //     primaryFields: [{ key: "name", label: "Nombre", value: nombre }],
            //     secondaryFields: [{ key: "phone", label: "Teléfono", value: telefono }]
            // }
        });

        // ✅ Accede a los campos definidos en el modelo
const primaryFields = pass.primaryFields;
const secondaryFields = pass.secondaryFields;

// ✅ Reemplaza los valores
const nombreField = primaryFields.find(f => f.key === "name");
if (nombreField) nombreField.value = nombre;

const extraField = pass.auxiliaryFields.find(f => f.key === "extra");
if (extraField) extraField.value = formatearEnBloquesDe4(tarjeta);

const telefonoField = secondaryFields.find(f => f.key === "phone");
if (telefonoField) telefonoField.value = telefono;

    const barcodeMessage = `TRANSFERMOVIL_ETECSA,TRANSFERENCIA,${tarjeta},${telefono}`;
        pass.setBarcodes(barcodeMessage);

        const buffer = pass.getAsBuffer();
        res.set({
            "Content-Type": "application/vnd.apple.pkpass",
            "Content-Disposition": "attachment; filename=mi-pase.pkpass"
        });
        res.send(buffer);
    } catch (err) {
        console.error("Error generando el pase:", err);
        res.status(500).send("Error generando el pase");
    }
});

app.listen(3000, () => {
    console.log("Servidor corriendo en http://localhost:3000");
});
