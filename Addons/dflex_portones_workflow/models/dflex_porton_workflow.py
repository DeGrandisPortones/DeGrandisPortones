
# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        selection=[
            ("acopio", "Acopio"),
            ("pendiente_medicion", "Pendiente de medición"),
            ("pendiente_modif_comercial", "Pendiente de modif. comercial"),
            ("pre_produccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado portón",
        default="acopio",
        tracking=True,
    )

    x_aprob_comercial = fields.Boolean(
        string="Aprobación comercial",
        default=False,
        tracking=True,
    )
    x_aprob_planificacion = fields.Boolean(
        string="Aprobación planificación",
        default=False,
        tracking=True,
    )
    x_aprob_administracion = fields.Boolean(
        string="Aprobación administración",
        default=False,
        tracking=True,
    )

    def _check_can_set_pre_produccion(self):
        for rec in self:
            missing = []
            if not rec.x_aprob_comercial:
                missing.append(_("Comercial"))
            if not rec.x_aprob_planificacion:
                missing.append(_("Planificación"))
            if not rec.x_aprob_administracion:
                missing.append(_("Administración"))
            if missing:
                raise models.ValidationError(
                    _("No se puede pasar a Pre-producción. Faltan aprobaciones de: %s")
                    % ", ".join(missing)
                )

    def action_set_acopio(self):
        for rec in self:
            rec.write({"x_estado": "acopio"})

    def action_set_pendiente_medicion(self):
        for rec in self:
            rec.write({"x_estado": "pendiente_medicion"})

    def action_set_pendiente_modif_comercial(self):
        for rec in self:
            rec.write({"x_estado": "pendiente_modif_comercial"})

    def action_set_pre_produccion(self):
        self._check_can_set_pre_produccion()
        for rec in self:
            rec.write({"x_estado": "pre_produccion"})

    def action_set_produccion(self):
        for rec in self:
            rec.write({"x_estado": "produccion"})
