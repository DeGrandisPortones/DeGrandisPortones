# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    ar_padron_env = fields.Selection([
        ("mock","Mock (solo pruebas)"),
        ("test","Homologación (AFIP Test)"),
        ("prod","Producción")
    ], string="Entorno AFIP/ARCA", default="mock", config_parameter="ar_padron_fetcher.env")

    ar_padron_use_mock = fields.Boolean(
        string="Usar datos de ejemplo (mock)",
        default=True,
        config_parameter="ar_padron_fetcher.use_mock"
    )

    ar_padron_cert = fields.Binary(string="Certificado (.crt/.pem)",
                                   help="Certificado digital para WSAA", attachment=True)
    ar_padron_key = fields.Binary(string="Clave privada (.key/.pem)",
                                  help="Clave privada para WSAA", attachment=True)
    ar_padron_key_password = fields.Char(string="Password de la clave (si aplica)")

    def set_values(self):
        res = super().set_values()
        ICP = self.env["ir.config_parameter"].sudo()
        # Guardar binarios como base64 en parámetros (simple y portable en Odoo.sh)
        if self.ar_padron_cert:
            ICP.set_param("ar_padron_fetcher.cert_b64", self.ar_padron_cert.decode() if isinstance(self.ar_padron_cert, bytes) else self.ar_padron_cert)
        if self.ar_padron_key:
            ICP.set_param("ar_padron_fetcher.key_b64", self.ar_padron_key.decode() if isinstance(self.ar_padron_key, bytes) else self.ar_padron_key)
        if self.ar_padron_key_password:
            ICP.set_param("ar_padron_fetcher.key_password", self.ar_padron_key_password)
        return res