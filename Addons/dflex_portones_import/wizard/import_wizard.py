
from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, csv

# Mapea encabezados normalizados del CSV -> nombre técnico del modelo
HEADER_MAP = {
    'nota de venta': 'x_nota_de_Venta',      # respeta exactamente tu nombre técnico
    'cliente +3000': 'x_nombre_del_cliente',
    'direccion cliente': 'x_direccion_del_cliente',
    'distribuidor': 'x_distribuidor',
}

NAME_CANDIDATES = [
    'nota de venta', 'nv', 'n° de venta', 'nro venta', 'venta'
]

def _norm(s):
    return (str(s) if s is not None else '').strip()

def _lower(s):
    return _norm(s).lower()

def _looks_like_csv(text):
    sample = '\\n'.join(text.splitlines()[:3])
    return (sample.count(',') >= 1) or (sample.count(';') >= 1)

class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importar portones desde CSV (1 encabezado; datos desde fila 2)'

    file = fields.Binary(required=True, string='Archivo CSV')
    filename = fields.Char(string='Nombre de archivo')

    def _read_csv(self, content):
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
            raise UserError('CSV inválido: hace falta 1 fila de encabezado y datos desde la 2.')
        headers = [_norm(h) for h in rows[0]]
        data_rows = rows[1:]
        return headers, data_rows

    def _build_header_index(self, headers):
        Porton = self.env['dflex.porton']
        existing_fields = Porton._fields
        idx_to_field = {}
        id_index = None
        for i, h in enumerate(headers):
            key = _lower(h)
            if id_index is None and any(cand in key for cand in NAME_CANDIDATES):
                id_index = i
            tech = HEADER_MAP.get(key)
            if tech and tech in existing_fields:
                idx_to_field[i] = tech
        return idx_to_field, id_index

    def action_import(self):
        self.ensure_one()
        headers, rows = self._read_csv(self.file)
        idx_to_field, id_index = self._build_header_index(headers)
        if not idx_to_field:
            raise UserError("No se encontraron columnas mapeables. Revisá los encabezados y el HEADER_MAP.")
        Porton = self.env['dflex.porton']
        created_ids = []
        for r_idx, row in enumerate(rows, start=2):
            vals = {}
            for i, val in enumerate(row):
                if i in idx_to_field:
                    vals[idx_to_field[i]] = _norm(val)
            name_val = None
            if id_index is not None and id_index < len(row):
                name_val = _norm(row[id_index])
            if not name_val:
                name_val = f"Sin NV (fila {r_idx})"
            vals['name'] = name_val
            rec = Porton.create(vals)
            created_ids.append(rec.id)
        action = self.env.ref('dflex_portones_import.action_dflex_porton').read()[0]
        action['domain'] = [('id', 'in', created_ids)]
        return action
