# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ResPartner(models.Model):
    _inherit = "res.partner"

    def action_ar_update_from_padron(self):
        for partner in self:
            cuit = (partner.vat or "").replace("-", "").replace(" ", "")
            if not cuit:
                raise UserError(_("El CUIT (VAT) está vacío en este contacto."))
            service = self.env["ar.padron.service"]
            data = service.lookup(cuit)

            vals = {}
            # Nombre
            if data.get("name"):
                vals["name"] = data["name"]
            # Dirección
            if data.get("street"):
                vals["street"] = data["street"]
            if data.get("city"):
                vals["city"] = data["city"]
            if data.get("zip"):
                vals["zip"] = data["zip"]
            # País / Provincia
            if data.get("country_code"):
                country = self.env["res.country"].search([("code","=",data["country_code"])], limit=1)
                if country:
                    vals["country_id"] = country.id
            if data.get("state_name") and vals.get("country_id"):
                state = self.env["res.country.state"].search([
                    ("name","ilike", data["state_name"]),
                    ("country_id","=", vals["country_id"])
                ], limit=1)
                if state:
                    vals["state_id"] = state.id

            # Intentar mapear Responsabilidad AFIP por texto
            if data.get("afip_responsibility"):
                resp = self.env["l10n_ar.afip.responsibility.type"].search([
                    ("name","ilike", data["afip_responsibility"])
                ], limit=1)
                if resp:
                    vals["l10n_ar_afip_responsibility_type_id"] = resp.id

            if vals:
                partner.write(vals)

        return True