from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, re, unicodedata

HEADER_NV_CANDIDATES = [
    'nv', 'numero de venta', 'n° de venta', 'nº de venta',
    'nro venta', 'nro de venta', 'número de venta'
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
    if s[0].isdigit():
        s = 'c_' + s
    return s[:50]

def _label(h1, h2):
    h1n, h2n = _norm(h1), _norm(h2)
    if h1n and h2n:
        # Abreviar la cabecera 1 a 3 letras + ". " como en el ejemplo (Ins. Instalador)
        return (h1n[:3].capitalize() + '. ' + h2n).strip()
    return (h1n or h2n)

def _is_xlsx(data):
    return data.startswith(b'PK\x03\x04')

def _is_xls(data):
    return data.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1')

class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importar portones desde Excel (PRINCIPAL, fila1+fila2 encabezados, datos desde fila3)'

    file = fields.Binary(required=True, string='Archivo XLS/XLSX')
    filename = fields.Char(string='Nombre de archivo')

    def _read_excel(self, content, filename):
        data = base64.b64decode(content or b'')
        if not data:
            raise UserError('El archivo está vacío.')
        sheet_name = 'PRINCIPAL'

        if _is_xlsx(data) or (filename or '').lower().endswith('.xlsx'):
            try:
                import openpyxl
            except Exception as e:
                raise UserError('Falta dependencia openpyxl para .xlsx: %s' % e)
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            if sheet_name not in wb.sheetnames:
                raise UserError('No se encontró la hoja "%s".' % sheet_name)
            ws = wb[sheet_name]
            headers1 = [ _norm(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1)) ]
            headers2 = [ _norm(c.value) for c in next(ws.iter_rows(min_row=2, max_row=2)) ]
            rows = []
            for r in ws.iter_rows(min_row=3, values_only=True):
                rows.append(list(r))
        elif _is_xls(data) or (filename or '').lower().endswith('.xls'):
            try:
                import xlrd
            except Exception:
                raise UserError('Tu archivo es .XLS. Esta instancia no trae xlrd. Abrí el archivo y guardalo como .XLSX y reintentá.')
            book = xlrd.open_workbook(file_contents=data)
            if sheet_name not in book.sheet_names():
                raise UserError('No se encontró la hoja "%s".' % sheet_name)
            sh = book.sheet_by_name(sheet_name)
            headers1 = [ _norm(sh.cell_value(0, c)) for c in range(sh.ncols) ]
            headers2 = [ _norm(sh.cell_value(1, c)) for c in range(sh.ncols) ]
            rows = []
            for r in range(2, sh.nrows):
                rows.append([ sh.cell_value(r, c) for c in range(sh.ncols) ])
        else:
            raise UserError('Formato no reconocido. Si es .XLS, convertí a .XLSX.')

        return headers1, headers2, rows

    def _build_columns(self, headers1, headers2):
        cols = []
        for idx, (h1, h2) in enumerate(zip(headers1, headers2)):
            # Omitir relleno: "Columna X"
            if re.match(r'^\s*columna\b', _lower(h1)) or re.match(r'^\s*columna\b', _lower(h2)):
                continue
            lbl = _label(h1, h2) or ('Columna %s' % (idx+1))
            tech = ('x_%s_%s' % (_slug(h1), _slug(h2))).strip('_')
            cols.append({'index': idx, 'label': lbl, 'tech': tech[:63], 'h1': h1, 'h2': h2})
        # Evitar duplicados técnicos
        seen = {}
        for c in cols:
            base = c['tech']
            n = 1
            key = base
            while key in seen:
                n += 1
                key = (base[:60] + '_' + str(n))[:63]
            c['tech'] = key
            seen[key] = True
        return cols

    def _ensure_fields(self, columns):
        Model = self.env['ir.model'].sudo()
        Fields = self.env['ir.model.fields'].sudo()
        model = Model.search([('model', '=', 'dflex.porton')], limit=1)
        if not model:
            raise UserError('No se encontró el modelo dflex.porton.')
        created_or_existing = []
        for col in columns:
            name = col['tech']
            field = Fields.search([('model_id', '=', model.id), ('name', '=', name)], limit=1)
            if not field:
                field = Fields.create({
                    'name': name,
                    'model_id': model.id,
                    'ttype': 'char',
                    'field_description': col['label'],
                    'size': 512,
                    'store': True,
                })
            created_or_existing.append({'name': name, 'label': col['label']})
        return created_or_existing

    def _upsert_dynamic_form_view(self, fields_meta):
        View = self.env['ir.ui.view'].sudo()
        field_xml = "\\n".join(['                  <field name=\"%s\" string=\"%s\"/>' % (f['name'], f['label']) for f in fields_meta])
        arch = f\"\"\"
        <form string=\"Portón\">
          <sheet>
            <group>
              <field name=\"name\"/>
              <field name=\"import_id\"/>
              <field name=\"source_row\"/>
            </group>
            <notebook>
              <page string=\"Datos importados\">
                <group col=\"4\">
{field_xml}
                </group>
              </page>
              <page string=\"JSON\">
                <field name=\"specs_json\" widget=\"json\"/>
              </page>
            </notebook>
          </sheet>
        </form>
        \"\"\"
        rec = View.search([('model', '=', 'dflex.porton'), ('name', '=', 'dflex.porton.form.auto')], limit=1)
        if rec:
            rec.write({'arch_db': arch, 'type': 'form', 'priority': 90})
        else:
            View.create({'name': 'dflex.porton.form.auto', 'model': 'dflex.porton', 'arch_db': arch, 'type': 'form', 'priority': 90})

    def _find_nv_column(self, columns):
        for cand in HEADER_NV_CANDIDATES:
            for c in columns:
                if cand in _lower(c['label']) or cand in _lower(c['h1']) or cand in _lower(c['h2']):
                    return c
        return None

    def action_import(self):
        self.ensure_one()
        h1, h2, data_rows = self._read_excel(self.file, self.filename or 'import.xlsx')
        columns = self._build_columns(h1, h2)
        if not columns:
            raise UserError('No se detectaron columnas válidas en PRINCIPAL.')
        meta = self._ensure_fields(columns)
        idx2tech = { c['index']: c['tech'] for c in columns }
        nv_col = self._find_nv_column(columns)

        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or 'Importación',
            'file_name': self.filename,
            'total_rows': len(data_rows),
            'note': 'Hoja: PRINCIPAL | Columnas: %s' % ', '.join([c['label'] for c in columns]),
            'state': 'draft',
        })

        Porton = self.env['dflex.porton']
        Spec = self.env['dflex.porton.spec']
        created_ids = []
        for r_idx, row in enumerate(data_rows, start=3):
            values = {}
            specs = {}
            for i, cell in enumerate(row):
                if i in idx2tech:
                    v = '' if cell is None else str(cell)
                    values[idx2tech[i]] = v
                    specs[idx2tech[i]] = v
            name_val = None
            if nv_col and nv_col['index'] < len(row):
                nv_raw = row[nv_col['index']]
                name_val = _norm(nv_raw)
            if not name_val:
                name_val = 'Sin NV (fila %s)' % r_idx
            rec = Porton.create({
                'name': name_val,
                'import_id': batch.id,
                'source_row': r_idx,
                'specs_json': specs,
                **values,
            })
            pairs = []
            for c in columns:
                tech = c['tech']
                if tech in values:
                    pairs.append({'porton_id': rec.id, 'key': c['label'], 'value': values[tech]})
            if pairs:
                Spec.create(pairs)
            created_ids.append(rec.id)

        batch.state = 'done'
        self._upsert_dynamic_form_view([{'name': f['name'], 'label': f['label']} for f in meta])
        action = self.env.ref('dflex_portones_import_dyn.action_dflex_porton').read()[0]
        action['domain'] = [('id', 'in', created_ids)]
        return action