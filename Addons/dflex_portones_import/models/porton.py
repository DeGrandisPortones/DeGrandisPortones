from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)

class DflexPortonImportBatch(models.Model):
    _name = 'dflex.porton.import'
    _description = 'Lote de importación de portones'
    _order = 'create_date desc'

    name = fields.Char(string='Nombre', required=True, default=lambda self: _('Importación %s') % fields.Date.today())
    file_name = fields.Char('Archivo')
    total_rows = fields.Integer('Filas')
    note = fields.Text('Notas')
    porton_ids = fields.One2many('dflex.porton', 'import_id', string='Portones')
    state = fields.Selection([('draft','Borrador'),('done','Importado')], default='draft')

class DflexPorton(models.Model):
    _name = 'dflex.porton'
    _description = 'Portón (fila importada)'
    _order = 'id desc'

    name = fields.Char('Identificador', index=True, required=True)
    import_id = fields.Many2one('dflex.porton.import', string='Lote de importación', ondelete='cascade')
    source_row = fields.Integer('Fila origen')
    specs_json = fields.Json('Especificaciones (JSON)')
    spec_ids = fields.One2many('dflex.porton.spec', 'porton_id', string='Especificaciones')
    state = fields.Selection([('draft','Borrador'),('imported','Importado')], default='draft')

    def action_view_specs(self):
        self.ensure_one()
        return {{
            'name': _('Especificaciones'),
            'type': 'ir.actions.act_window',
            'res_model': 'dflex.porton.spec',
            'view_mode': 'tree,form',
            'domain': [('porton_id', '=', self.id)],
            'context': dict(self.env.context, default_porton_id=self.id),
        }}

    @api.model
    def create_from_rows(self, rows, batch, name_column=None):
        Porton = self.env['dflex.porton']
        Spec = self.env['dflex.porton.spec']
        created = self.env['dflex.porton']
        for idx, row in enumerate(rows, start=2):  # assume row 1 = headers; display 1-based excel row numbers
            # Row is a dict col->value
            specs = {{k: (v if v not in [False, None] else '') for k, v in row.items()}}
            # Name strategy: prefer an explicit column, else build one
            name = None
            if name_column and specs.get(name_column):
                name = str(specs.get(name_column))
            else:
                # Combine first two non-empty columns
                first_keys = [k for k in specs.keys() if str(specs.get(k)).strip()]
                if first_keys:
                    name = f"{first_keys[0]}: {specs[first_keys[0]]}"
                else:
                    name = _('Portón fila %s') % idx
            rec = Porton.create({{
                'name': name,
                'import_id': batch.id,
                'source_row': idx,
                'specs_json': specs,
                'state': 'imported',
            }})
            # Create key/value child rows for tabular inspection and pivoting
            kvs = []
            for k, v in specs.items():
                kvs.append({{
                    'porton_id': rec.id,
                    'key': str(k),
                    'value': str(v) if v is not None else '',
                }})
            Spec.create(kvs)
            created += rec
        return created