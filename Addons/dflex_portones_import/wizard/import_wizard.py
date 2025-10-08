from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64, io
HEADER_CANDIDATES = ['nv','numero de venta','n° de venta','nro venta','nro de venta','número de venta']
def _normalize(s): return (str(s) if s is not None else '').strip()
def _lower(s): return _normalize(s).lower()
class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importar portones desde Excel (hoja PRINCIPAL)'
    file = fields.Binary(required=True)
    filename = fields.Char()
    name_column = fields.Char(help='Si se omite, se usa NV/Numero de venta si existe.')
    def _detect_header_row(self, ws, max_scan=25):
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan, values_only=True), start=1):
            texts = [_lower(v) for v in row if v not in (None, '')]
            if texts and any(any(c in t for c in HEADER_CANDIDATES) for t in texts): return idx
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan, values_only=True), start=1):
            if len([v for v in row if _normalize(v)]) >= 5: return idx
        return 1
    def _read_excel(self, content, filename):
        data = base64.b64decode(content or b'')
        if not data: raise UserError(_('El archivo está vacío.'))
        buf = io.BytesIO(data)
        rows, headers = [], []
        sheet_name = 'PRINCIPAL'
        if (filename or '').lower().endswith('.xls'):
            try: import xlrd
            except Exception as e: raise UserError(_('Falta xlrd para .xls: %s') % e)
            book = xlrd.open_workbook(file_contents=buf.read())
            if sheet_name not in book.sheet_names(): raise UserError(_('No se encontró la hoja "%s".') % sheet_name)
            sh = book.sheet_by_name(sheet_name)
            headers = [str(sh.cell_value(0,c)).strip() for c in range(sh.ncols)]
            for r in range(1, sh.nrows):
                row = {}
                for c, h in enumerate(headers):
                    v = sh.cell_value(r,c)
                    if isinstance(v, float) and v.is_integer(): v = int(v)
                    row[h] = v
                rows.append(row)
        else:
            try: import openpyxl
            except Exception as e: raise UserError(_('Falta openpyxl para .xlsx: %s') % e)
            wb = openpyxl.load_workbook(buf, data_only=True)
            if sheet_name not in wb.sheetnames: raise UserError(_('No se encontró la hoja "%s".') % sheet_name)
            ws = wb[sheet_name]
            hrow = self._detect_header_row(ws)
            header_cells = next(ws.iter_rows(min_row=hrow, max_row=hrow))
            headers = [str(c.value).strip() if c.value is not None else '' for c in header_cells]
            for r in ws.iter_rows(min_row=hrow+1, values_only=True):
                row = {}
                for h, v in zip(headers, list(r)):
                    if isinstance(v, float) and getattr(v, 'is_integer', lambda: False)(): v = int(v)
                    row[h] = v
                rows.append(row)
        rows = [r for r in rows if any((_normalize(v)) for v in r.values())]
        return headers, rows
    def action_import(self):
        self.ensure_one()
        headers, rows = self._read_excel(self.file, self.filename or 'import.xlsx')
        name_col = self.name_column or None
        if not name_col:
            lowered = {_lower(h): h for h in headers}
            for cand in HEADER_CANDIDATES:
                if cand in lowered: name_col = lowered[cand]; break
            if not name_col:
                for k, original in lowered.items():
                    if any(c in k for c in HEADER_CANDIDATES): name_col = original; break
        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or _('Importación'),
            'file_name': self.filename, 'total_rows': len(rows),
            'note': _('Hoja: PRINCIPAL | Columnas: %s') % ', '.join([h or '-' for h in headers]),
        })
        self.env['dflex.porton'].create_from_rows(rows, batch, name_column=name_col)
        batch.state = 'done'
        action = self.env.ref('dflex_portones_import.action_dflex_porton').read()[0]
        action['domain'] = [('import_id', '=', batch.id)]
        action['context'] = {}
        return action
