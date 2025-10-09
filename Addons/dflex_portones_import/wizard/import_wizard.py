from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, re, unicodedata, csv

HEADER_NV_CANDIDATES = [
    'nv', 'n v', 'numero de venta', 'n° de venta', 'nº de venta',
    'nro venta', 'nro de venta', 'número de venta', 'n° venta', 'venta n°', 'nota de venta', 'venta'
]

def _norm(s):
    return (str(s) if s is not None else '').strip()

def _lower(s):
    return _norm(s).lower()

def _slug(s):
    s = _norm(s)
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    s = re.sub(r'[^a-zA-Z0-9]+', '_', s).strip('_').lower()
    if not s:
        s = 'col'
    if s and s[0].isdigit():
        s = 'c_' + s
    return s[:50]

def _label_single(h):
    return _norm(h)

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
        headers = [ _norm(x) for x in rows[0] ]
        data_rows = rows[1:]
        return headers, data_rows

    def _build_columns(self, headers):
        cols = []
        for idx, h in enumerate(headers):
            h1 = _norm(h)
            # Omitir columnas "Columna X" y también 'name'
            if _lower(h1) == 'name':
                continue
            if re.match(r'^\s*columna\b', _lower(h1)):
                continue
            if not h1:
                continue
            lbl = _label_single(h1)
            tech = ('x_%s' % _slug(h1)).strip('_')
            if not tech.startswith('x_'):
                tech = 'x_' + tech
            cols.append({'index': idx, 'label': lbl, 'tech': tech[:63], 'h1': h1})
        # Evitar duplicados técnicos
        seen = {}
        for c in cols:
            base = c['tech']
            k = base
            i = 1
            while k in seen:
                i += 1
                k = (base[:60] + '_' + str(i))[:63]
            c['tech'] = k
            seen[k] = True
        return cols

    def _ensure_fields(self, columns):
        Model = self.env['ir.model'].sudo()
        Fields = self.env['ir.model.fields'].sudo()
        model = Model.search([('model', '=', 'dflex.porton')], limit=1)
        if not model:
            raise UserError('No se encontró el modelo dflex.porton.')
        out = []
        for col in columns:
            name = col['tech']
            field = Fields.search([('model_id', '=', model.id), ('name', '=', name)], limit=1)
            if not field:
                field = Fields.create({
                    'name': name,
                    'model_id': model.id,
                    'ttype': 'char',
                    'field_description': col['label'],
                    'store': True,
                })
            out.append({'name': name, 'label': col['label']})
        return out

    def _upsert_dynamic_form_view(self, fields_meta):
        View = self.env['ir.ui.view'].sudo()
        lines = ['                  <field name="%s" string="%s"/>' % (f['name'], f['label']) for f in fields_meta]
        field_xml = "\n".join(lines) or '                  <separator string="(sin columnas detectadas)"/>'
        arch = """
        <form string="Portón">
          <sheet>
            <group>
              <field name="name"/>
              <field name="import_id"/>
              <field name="source_row"/>
            </group>
            <notebook>
              <page string="Datos importados">
                <group col="4">
{}
                </group>
              </page>
              <page string="JSON">
                <field name="specs_json" widget="json"/>
              </page>
            </notebook>
          </sheet>
        </form>
        """.format(field_xml)
        rec = View.search([('model', '=', 'dflex.porton'), ('name', '=', 'dflex.porton.form.auto')], limit=1)
        vals = {'arch_db': arch, 'type': 'form', 'priority': 1}
        if rec:
            rec.write(vals)
        else:
            View.create({'name': 'dflex.porton.form.auto', 'model': 'dflex.porton', **vals})

    def _find_identifier_index(self, headers):
        # 1º preferir 'name'
        for idx, h in enumerate(headers):
            if _lower(h) == 'name':
                return idx
        # 2º buscar NV por candidatos
        for idx, h in enumerate(headers):
            text = _lower(h)
            for cand in HEADER_NV_CANDIDATES:
                if cand in text:
                    return idx
        return None

    def action_import(self):
        self.ensure_one()
        if not self.filename or not self.filename.lower().endswith('.csv'):
            raise UserError('Este importador acepta únicamente CSV.')
        headers, data_rows = self._read_csv(self.file, self.filename or 'import.csv')
        columns = self._build_columns(headers)
        if not columns:
            raise UserError('No se detectaron columnas válidas.')
        meta = self._ensure_fields(columns)
        idx2tech = { c['index']: c['tech'] for c in columns }
        id_index = self._find_identifier_index(headers)

        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or 'Importación',
            'file_name': self.filename,
            'total_rows': len(data_rows),
            'note': 'CSV (1 encabezado) | Columnas: %s' % ', '.join([c['label'] for c in columns]),
            'state': 'draft',
        })

        Porton = self.env['dflex.porton']
        Spec = self.env['dflex.porton.spec']
        created_ids = []
        for r_idx, row in enumerate(data_rows, start=2):
            values, specs = {}, {}
            for i, cell in enumerate(row):
                if i in idx2tech:
                    v = '' if cell is None else str(cell)
                    values[idx2tech[i]] = v
                    specs[idx2tech[i]] = v
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
            if specs:
                Spec.create([{'porton_id': rec.id, 'key': k, 'value': v} for k, v in specs.items()])
            created_ids.append(rec.id)

        batch.state = 'done'
        self._upsert_dynamic_form_view([{'name': f['name'], 'label': f['label']} for f in meta])
        action = self.env.ref('dflex_portones_import.action_dflex_porton').read()[0]
        action['domain'] = [('id', 'in', created_ids)]
        return action