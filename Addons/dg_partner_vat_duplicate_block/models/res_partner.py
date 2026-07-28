# -*- coding: utf-8 -*-
from odoo import _, api, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("vat", "company_id")
    def _check_duplicate_vat(self):
        """Bloquea crear/guardar un contacto con el mismo CUIT/VAT que otro
        contacto activo ya existente.

        Odoo sólo muestra un aviso no bloqueante (banner "ya existe un
        contacto con el mismo CUIT") y deja guardar igual, lo que termina
        generando contactos duplicados. Acá lo convertimos en un error real.

        Se excluyen los contactos que ya pertenecen a la misma entidad
        comercial (p. ej. un hijo que hereda el CUIT de su empresa), y se
        puede saltear puntualmente con el contexto `skip_duplicate_vat_check`
        para procesos automáticos que necesiten crear contactos con CUIT
        repetido a propósito.
        """
        if self.env.context.get("skip_duplicate_vat_check"):
            return

        for partner in self:
            if not partner.vat:
                continue

            domain = [
                ("id", "!=", partner.id),
                ("vat", "=", partner.vat),
                ("commercial_partner_id", "!=", partner.commercial_partner_id.id),
            ]
            if partner.company_id:
                domain.append(("company_id", "in", [False, partner.company_id.id]))

            duplicate = self.env["res.partner"].search(domain, limit=1)
            if duplicate:
                raise ValidationError(
                    _(
                        "Ya existe otro contacto con el mismo CUIT/VAT (%(vat)s): "
                        "'%(existing)s'.\n\n"
                        "No se puede guardar un contacto duplicado. Si es el mismo "
                        "contacto, buscalo y editá el existente en lugar de crear uno "
                        "nuevo."
                    )
                    % {"vat": partner.vat, "existing": duplicate.display_name}
                )
