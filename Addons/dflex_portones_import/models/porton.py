from odoo import fields, models

class DflexPortonImport(models.Model):
    _name = 'dflex.porton.import'
    _description = 'Lote de importación de portones'
    _order = 'create_date desc'

    name = fields.Char(required=True, default=lambda self: 'Importación %s' % fields.Date.today())
    file_name = fields.Char()
    total_rows = fields.Integer()
    note = fields.Text()
    porton_ids = fields.One2many('dflex.porton', 'import_id')
    state = fields.Selection([('draft','Borrador'),('done','Importado')], default='draft')


class DflexPorton(models.Model):
    _name = 'dflex.porton'
    _description = 'Portón (fila importada)'
    _order = 'id desc'

    name = fields.Char(string='Identificador (NV)', index=True, required=True)
    import_id = fields.Many2one('dflex.porton.import', string='Importación', ondelete='cascade', index=True)
    source_row = fields.Integer(string='Fila origen')
    specs_json = fields.Json(string='Especificaciones (JSON)')
    spec_ids = fields.One2many('dflex.porton.spec', 'porton_id', string='Especificaciones (K/V)')
    state = fields.Selection([('imported','Importado')], default='imported')
