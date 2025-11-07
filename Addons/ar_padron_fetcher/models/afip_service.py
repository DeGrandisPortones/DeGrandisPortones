# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import re
import base64
import logging

_logger = logging.getLogger(__name__)

CUIT_RE = re.compile(r"^\d{11}$")

def _calc_cuit_check_digit(cuit):
    """Verifica/retorna dígito verificador del CUIT (método oficial)."""
    weights = [5,4,3,2,7,6,5,4,3,2]
    total = sum(int(d)*w for d,w in zip(cuit[:10], weights))
    dv = 11 - (total % 11)
    if dv == 11:
        dv = 0
    elif dv == 10:
        dv = 9
    return dv

class ArPadronService(models.AbstractModel):
    """Servicio para consultar Padrón AFIP/ARCA.

    Implementa un 'mock' para dev (sin credenciales)
    y deja un hook claro para producción (via SOAP/WSAA).
    """
    _name = "ar.padron.service"
    _description = "AR Padrón Service (AFIP/ARCA)"

    @api.model
    def _get_settings(self):
        ICP = self.env["ir.config_parameter"].sudo()
        env = ICP.get_param("ar_padron_fetcher.env", default="mock")  # mock|test|prod
        use_mock = ICP.get_param("ar_padron_fetcher.use_mock", default="True") == "True"
        company_vat = self.env.company.vat or ""
        cert_b64 = ICP.get_param("ar_padron_fetcher.cert_b64", default=False)
        key_b64 = ICP.get_param("ar_padron_fetcher.key_b64", default=False)
        key_password = ICP.get_param("ar_padron_fetcher.key_password", default="")
        return {
            "env": env,
            "use_mock": use_mock,
            "company_vat": re.sub(r"\D", "", company_vat or ""),
            "cert_b64": cert_b64,
            "key_b64": key_b64,
            "key_password": key_password,
        }

    @api.model
    def _validate_cuit(self, cuit):
        if not cuit or not CUIT_RE.match(cuit):
            raise UserError(_("Ingrese un CUIT de 11 dígitos."))
        if int(cuit[-1]) != _calc_cuit_check_digit(cuit):
            raise UserError(_("CUIT inválido: dígito verificador incorrecto."))

    @api.model
    def lookup(self, cuit):
        """Devuelve un dict con datos padron mapeados a partner.*

        Keys esperadas:
          - name
          - street, city, zip, state_name (opcional), country_code
          - afip_responsibility (texto, si está disponible)
        """
        self._validate_cuit(cuit)
        conf = self._get_settings()

        if conf["use_mock"] or conf["env"] == "mock":
            # Datos simulados (útil en dev/homologación)
            _logger.info("AR Padrón MOCK activado - devolviendo datos de ejemplo.")
            sample = {
                "name": "Cliente Demo SRL",
                "street": "Av. Siempre Viva 742",
                "city": "CABA",
                "zip": "1000",
                "state_name": "Ciudad Autónoma de Buenos Aires",
                "country_code": "AR",
                "afip_responsibility": "Responsable Inscripto",
            }
            return sample

        # --- Hook real: implementar llamada a AFIP/ARCA ---
        # Sugerido: usar WSAA + SOAP (zeep) a ws_sr_padron_a5
        # 1) Obtener Token/Sign desde WSAA con cert/key cargados en Ajustes
        # 2) Invocar getPersona con token/sign al servicio A5
        # 3) Mapear el resultado al dict de arriba

        try:
            from .wsaa_zeep import get_token_sign, padron_a5_get_person
        except Exception as e:  # pragma: no cover
            raise UserError(_("Dependencias faltantes para AFIP (zeep/crypto). Error: %s") % e)

        token, sign = get_token_sign(self.env, conf)
        data = padron_a5_get_person(self.env, token, sign, cuit, environment=conf["env"])
        # Map básico (ajustar según payload real):
        mapped = {
            "name": data.get("denominacion") or data.get("nombre"),
            "street": (data.get("domicilio") or {}).get("calle"),
            "city": (data.get("domicilio") or {}).get("localidad"),
            "zip": (data.get("domicilio") or {}).get("cp"),
            "state_name": (data.get("domicilio") or {}).get("provincia"),
            "country_code": "AR",
            "afip_responsibility": data.get("categoria_iva") or (data.get("imp_iva") or {}).get("categoria"),
        }
        return mapped