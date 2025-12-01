from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        [
            ("borrador", "Borrador"),
            ("acopio", "Acopio"),
            ("pendiente_medicion", "Pendiente de medición"),
            ("pendiente_modif_comercial", "Pendiente modif. comercial"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado portón",
        default="borrador",
    )

    x_aprob_comercial = fields.Boolean(string="Aprob. Comercial")
    x_aprob_planificacion = fields.Boolean(string="Aprob. Planificación")
    x_aprob_administracion = fields.Boolean(string="Aprob. Administración")

    # --- Acciones de cambio de estado (botones del formulario) ---

    def action_set_acopio(self):
        for rec in self:
            rec.x_estado = "acopio"

    def action_set_pendiente_medicion(self):
        for rec in self:
            rec.x_estado = "pendiente_medicion"

    def action_set_pendiente_modif_comercial(self):
        for rec in self:
            rec.x_estado = "pendiente_modif_comercial"

    def action_set_preproduccion(self):
        for rec in self:
            if not (rec.x_aprob_comercial and rec.x_aprob_planificacion and rec.x_aprob_administracion):
                raise UserError(
                    _(
                        "Para pasar a Pre-producción, las 3 aprobaciones (Comercial, "
                        "Planificación y Administración) deben estar marcadas."
                    )
                )
            rec.x_estado = "preproduccion"

    def action_set_produccion(self):
        for rec in self:
            if rec.x_estado != "preproduccion":
                raise UserError(
                    _(
                        "Solo puede pasar a Producción desde Pre-producción. "
                        "Verifique el estado y las aprobaciones."
                    )
                )
            rec.x_estado = "produccion"
