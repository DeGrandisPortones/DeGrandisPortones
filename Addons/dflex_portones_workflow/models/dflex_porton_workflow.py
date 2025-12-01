from odoo import api, fields, models


class DflexPorton(models.Model):
    _inherit = "x_dflex.porton"

    # Estado general del portón
    x_estado = fields.Selection(
        selection=[
            ("acopio", "Acopio"),
            ("pend_medir", "Pendiente de medición"),
            ("pend_modif", "Pendiente de modificaciones comerciales"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "En producción"),
        ],
        string="Estado workflow",
        default="acopio",
        tracking=True,
    )

    # Aprobaciones
    x_aprob_comercial = fields.Boolean(string="Aprobación comercial", default=False)
    x_aprob_planificacion = fields.Boolean(string="Aprobación planificación", default=False)
    x_aprob_administracion = fields.Boolean(string="Aprobación administración", default=False)

    # Helpers para ver si está todo aprobado
    x_todas_aprobaciones = fields.Boolean(
        string="Todas las aprobaciones OK",
        compute="_compute_todas_aprobaciones",
        store=True,
    )

    @api.depends("x_aprob_comercial", "x_aprob_planificacion", "x_aprob_administracion")
    def _compute_todas_aprobaciones(self):
        for rec in self:
            rec.x_todas_aprobaciones = bool(
                rec.x_aprob_comercial and
                rec.x_aprob_planificacion and
                rec.x_aprob_administracion
            )

    # Acciones simples de cambio de estado (se podrán usar luego en botones)
    def action_set_acopio(self):
        for rec in self:
            rec.x_estado = "acopio"

    def action_set_pend_medir(self):
        for rec in self:
            rec.x_estado = "pend_medir"

    def action_set_pend_modif(self):
        for rec in self:
            rec.x_estado = "pend_modif"

    def action_set_preproduccion(self):
        for rec in self:
            rec.x_estado = "preproduccion"

    def action_set_produccion(self):
        for rec in self:
            rec.x_estado = "produccion"
