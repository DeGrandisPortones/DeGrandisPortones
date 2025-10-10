from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, csv

HEADER_MAP = {
    # encabezado en CSV -> nombre técnico en dflex.porton
    'nota de venta': 'x_nota_de_Venta',
    'cliente +3000': 'x_nombre_del_cliente',
    'direccion cliente': 'x_direccion_del_cliente',
    'distribuidor': 'x_distribuidor',
}

def _norm(s):
    return (str(s) if s is not None else '').strip()

class DflexPortonImport(models.Model):
    _name = 'dflex.porton.import'
    _description = 'Lotes de importación de Portones'

    name = fields.Char(required=True, default='Importación CSV')
    file_name = fields.Char()
    total_rows = fields.Integer()
    state = fields.Selection([('draft','Borrador'),('done','Importado')], default='draft')
    note = fields.Text()

class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importador de Portones desde CSV'

    file = fields.Binary(required=True, string='Archivo CSV')
    filename = fields.Char(string='Nombre')

    def _read_csv(self, content):
        data = base64.b64decode(content or b'')
        if not data:
            raise UserError('El archivo está vacío.')
        # intenta utf-8 luego latin-1
        try:
            text = data.decode('utf-8')
        except Exception:
            text = data.decode('latin-1', errors='replace')
        # delimitador
        first = text.splitlines()[0] if text else ''
        delimiter = ';' if first.count(';') > first.count(',') else ','
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if len(rows) < 2:
            raise UserError('CSV inválido: se espera 1 fila de encabezado + datos.')
        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
        return headers, data_rows

    def _build_mapping(self, headers):
        idx_to_field = {}
        for i, h in enumerate(headers):
            k = _norm(h).lower()
            if k in HEADER_MAP:
                idx_to_field[i] = HEADER_MAP[k]
        if not idx_to_field:
            raise UserError('Ningún encabezado del CSV coincide con los esperados: %s' % ', '.join(HEADER_MAP.keys()))
        return idx_to_field

    def action_import(self):
        self.ensure_one()
        headers, data_rows = self._read_csv(self.file)
        idx_to_field = self._build_mapping(headers)

        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or 'Importación',
            'file_name': self.filename,
            'total_rows': len(data_rows),
            'note': 'CSV; columnas mapeadas: %s' % ', '.join([headers[i] for i in idx_to_field.keys()]),
        })
        Porton = self.env['dflex.porton']
        created_ids = []
        # intenta deducir name por "nota de venta" si está mapeada
        name_field = HEADER_MAP.get('nota de venta')
        name_idx = None
        if name_field:
            for i, f in idx_to_field.items():
                if f == name_field:
                    name_idx = i
                    break

        for row_idx, row in enumerate(data_rows, start=2):
            values = {}
            for i, f in idx_to_field.items():
                if i < len(row):
                    values[f] = _norm(row[i])
            name_val = _norm(row[name_idx]) if name_idx is not None and name_idx < len(row) else ''
            if not name_val:
                name_val = 'Sin NV (fila %s)' % row_idx
            rec = Porton.create({
                'name': name_val,
                **values,
            })
            created_ids.append(rec.id)

        batch.state = 'done'
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Portones importados',
            'res_model': 'dflex.porton',
            'view_mode': 'list,form',
            'domain': [('id', 'in', created_ids)],
            'target': 'current',
        }
        return action