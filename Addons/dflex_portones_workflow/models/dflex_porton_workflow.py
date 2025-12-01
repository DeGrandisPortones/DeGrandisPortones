from odoo import models, fields

class DflexPortonWorkflow(models.Model):
    _inherit = "x_dflex.porton"

    x_estado = fields.Selection(
        [
            ("acopio", "Acopio"),
            ("pend_medicion", "Pendiente de medición"),
            ("pend_ajustes_comercial", "Pendiente de ajustes comerciales"),
            ("preproduccion", "Pre-producción"),
            ("produccion", "Producción"),
        ],
        string="Estado del portón",
        default="acopio",
        tracking=True,
    )

    x_aprob_comercial = fields.Boolean(string="Aprobación Comercial")
    x_aprob_planificacion = fields.Boolean(string="Aprobación Planificación")
    x_aprob_administracion = fields.Boolean(string="Aprobación Administración")
