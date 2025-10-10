from odoo import models, fields

class DflexPorton(models.Model):
    _name = 'dflex.porton'
    _description = 'Portón (Core)'

    name = fields.Char("Nota de Venta / ID", required=True)
    import_id = fields.Many2one('dflex.porton.import', string="Lote de importación")
    source_row = fields.Integer("Fila origen")
    specs_json = fields.Json(string="Especificaciones (JSON)")