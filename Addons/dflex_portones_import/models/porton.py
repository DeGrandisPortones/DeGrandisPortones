from odoo import api, fields, models, _
class DflexPortonImport(models.Model):
    _name = 'dflex.porton.import'
    _description = 'Lote de importación de portones'
    _order = 'create_date desc'
    name = fields.Char(required=True, default=lambda self: _('Importación %s') % fields.Date.today())
    file_name = fields.Char()
    total_rows = fields.Integer()
    note = fields.Text()
    porton_ids = fields.One2many('dflex.porton', 'import_id')
    state = fields.Selection([('draft','Borrador'),('done','Importado')], default='draft')

class DflexPorton(models.Model):
    _name = 'dflex.porton'
    _description = 'Portón (fila importada)'
    _order = 'id desc'
    name = fields.Char(index=True, required=True)
    import_id = fields.Many2one('dflex.porton.import', ondelete='cascade')
    source_row = fields.Integer()
    specs_json = fields.Json()
    spec_ids = fields.One2many('dflex.porton.spec', 'porton_id')
    state = fields.Selection([('draft','Borrador'),('imported','Importado')], default='draft')

    def action_view_specs(self):
        self.ensure_one()
        return {
            'name': _('Especificaciones'),
            'type': 'ir.actions.act_window',
            'res_model': 'dflex.porton.spec',
            'view_mode': 'list,form',
            'domain': [('porton_id', '=', self.id)],
            'context': {'default_porton_id': self.id},
        }

    @api.model
    def create_from_rows(self, rows, batch, name_column=None):
        Porton = self.env['dflex.porton']
        Spec = self.env['dflex.porton.spec']
        created = self.env['dflex.porton']
        for idx, row in enumerate(rows, start=2):
            specs = {k: (v if v not in [False, None] else '') for k, v in row.items()}
            name = None
            if name_column and specs.get(name_column):
                name = str(specs.get(name_column))
            else:
                first_keys = [k for k in specs.keys() if str(specs.get(k)).strip()]
                name = f"{first_keys[0]}: {specs[first_keys[0]]}" if first_keys else _('Portón fila %s') % idx
            rec = Porton.create({
                'name': name,
                'import_id': batch.id,
                'source_row': idx,
                'specs_json': specs,
                'state': 'imported',
            })
            Spec.create([{'porton_id': rec.id, 'key': str(k), 'value': str(v) if v is not None else ''} for k, v in specs.items()])
            created += rec
        return created
