
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, re, unicodedata, csv

HEADER_NV_CANDIDATES = [
    'nv', 'n v', 'numero de venta', 'n° de venta', 'nº de venta',
    'nro venta', 'nro de venta', 'número de venta', 'n° venta', 'venta n°', 'nota de venta', 'venta'
]

def _norm(s): return (str(s) if s is not None else '').strip()
def _lower(s): return _norm(s).lower()
def _slug(s):
    s = _norm(s)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()
    if not s: s = 'col'
    if s[0].isdigit(): s = 'c_' + s
    return s[:50]

def _looks_like_csv(text):
    sample = '\n'.join(text.splitlines()[:3])
    return (sample.count(',') >= 3) or (sample.count(';') >= 3)

class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importar portones desde CSV (1 encabezado; datos desde fila 2)'

    file = fields.Binary(required=True, string='Archivo CSV')
    filename = fields.Char(string='Nombre de archivo')

    def _read_csv(self, content, filename):
        data = base64.b64decode(content or b'')
        if not data:
            raise UserError('El archivo está vacío.')
        try:
            text = data.decode('utf-8')
        except Exception:
            text = data.decode('latin-1', errors='replace')
        if not _looks_like_csv(text):
            raise UserError('El archivo no parece un CSV válido.')
        first = text.splitlines()[0] if text else ''
        delimiter = ';' if first.count(';') > first.count(',') else ','
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if len(rows) < 2:
            raise UserError('CSV inválido: necesita 1 fila de encabezado y datos desde la 2.')
        headers = [_norm(x) for x in rows[0]]
        data_rows = rows[1:]
        return headers, data_rows

    def _find_identifier_index(self, headers):
        for idx, h in enumerate(headers):
            if _lower(h) == 'name':
                return idx
        for idx, h in enumerate(headers):
            text = _lower(h)
            for cand in HEADER_NV_CANDIDATES:
                if cand in text:
                    return idx
        return None

    def _build_mapping(self, headers):
        Fields = self.env['ir.model.fields'].sudo()
        flds = Fields.search([('model', '=', 'dflex.porton')])
        by_label = { _lower(f.field_description or ''): f.name for f in flds if f.name.startswith('x_') }
        by_name = { f.name: True for f in flds }

        mapping = {}
        for i, h in enumerate(headers):
            lbl = _lower(h)
            if lbl in ('name',):
                continue
            if lbl in by_label:
                mapping[i] = by_label[lbl]
                continue
            candidate = 'x_' + _slug(h)
            if candidate in by_name:
                mapping[i] = candidate
                continue
        return mapping

    def action_import(self):
        self.ensure_one()
        headers, data_rows = self._read_csv(self.file, self.filename or 'import.csv')

        idx2field = self._build_mapping(headers)
        if not idx2field:
            raise UserError('No se pudo mapear ninguna columna del CSV con campos del modelo. Verifique encabezados.')

        id_index = self._find_identifier_index(headers)

        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or 'Importación',
            'file_name': self.filename,
            'total_rows': len(data_rows),
            'note': 'CSV (1 encabezado)',
            'state': 'draft',
        })

        Porton = self.env['dflex.porton']
        created_ids = []

        for r_idx, row in enumerate(data_rows, start=2):
            values = {}
            specs = {}
            for i, cell in enumerate(row):
                if i in idx2field:
                    v = '' if cell is None else str(cell)
                    field_name = idx2field[i]
                    values[field_name] = v
                    specs[field_name] = v
            name_val = None
            if id_index is not None and id_index < len(row):
                name_val = _norm(row[id_index])
            if not name_val:
                name_val = 'Sin NV (fila %s)' % r_idx

            rec = Porton.create({
                'name': name_val,
                'import_id': batch.id,
                'source_row': r_idx,
                'specs_json': specs,
                **values,
            })
            created_ids.append(rec.id)

        batch.state = 'done'

        action = self.env.ref('dflex_portones_import.action_dflex_porton').read()[0]
        action['domain'] = [('id', 'in', created_ids)]
        return action
