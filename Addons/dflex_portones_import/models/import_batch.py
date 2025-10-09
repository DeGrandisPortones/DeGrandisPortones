
from odoo import fields, models

class DflexPortonImport(models.Model):
    _name = 'dflex.porton.import'
    _description = 'Lote de importación de portones'

    name = fields.Char(required=True, default='Importación')
    file_name = fields.Char()
    total_rows = fields.Integer()
    note = fields.Text()
    state = fields.Selection([('draft', 'Borrador'), ('done', 'Listo')], default='draft')
