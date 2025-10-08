from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64, io

HEADER_CANDIDATES = ['nv','numero de venta','n° de venta','nro venta','nro de venta','número de venta']

def _normalize(s): 
    return (str(s) if s is not None else '').strip()

def _lower(s): 
    return _normalize(s).lower()

def _is_xlsx(data):
    # ZIP magic
    return data.startswith(b'PK\x03\x04')

def _is_xls(data):
    # OLE Compound File magic
    return data.startswith(b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1')

class DflexPortonImportWizard(models.TransientModel):
    _name = 'dflex.porton.import.wizard'
    _description = 'Importar portones desde Excel (hoja PRINCIPAL)'

    file = fields.Binary(required=True, string='Archivo XLS/XLSX')
    filename = fields.Char(string='Nombre de archivo')
    name_column = fields.Char(string='Columna para nombre (opcional)', help='Si se omite, se usa NV/Número de venta automáticamente si existe.')

    def _detect_header_row(self, ws, max_scan=25):
        # Solo para XLSX (openpyxl)
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan, values_only=True), start=1):
            texts = [_lower(v) for v in row if v not in (None, '')]
            if texts and any(any(c in t for c in HEADER_CANDIDATES) for t in texts):
                return idx
        for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_scan, values_only=True), start=1):
            if len([v for v in row if _normalize(v)]) >= 5:
                return idx
        return 1

    def _read_excel(self, content, filename):
        data = base64.b64decode(content or b'')
        if not data:
            raise UserError(_('El archivo está vacío.'))
        rows, headers = [], []
        sheet_name = 'PRINCIPAL'

        # Detección por contenido primero (más confiable que la extensión)
        if _is_xlsx(data) or (filename or '').lower().endswith('.xlsx'):
            try:
                import openpyxl
            except Exception as e:
                raise UserError(_('Falta dependencia openpyxl para .xlsx: %s') % e)
            wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
            if sheet_name not in wb.sheetnames:
                raise UserError(_('No se encontró la hoja "%s" en el archivo.') % sheet_name)
            ws = wb[sheet_name]
            header_row = self._detect_header_row(ws)
            header_cells = next(ws.iter_rows(min_row=header_row, max_row=header_row))
            headers = [str(c.value).strip() if c.value is not None else '' for c in header_cells]
            for r in ws.iter_rows(min_row=header_row+1, values_only=True):
                row = {}
                for h, v in zip(headers, list(r)):
                    if isinstance(v, float) and getattr(v, 'is_integer', lambda: False)():
                        v = int(v)
                    row[h] = v
                rows.append(row)
        elif _is_xls(data) or (filename or '').lower().endswith('.xls'):
            # Intentar con xlrd; si no está instalado, dar mensaje claro.
            try:
                import xlrd
            except Exception:
                raise UserError(_('Tu archivo es .XLS (formato antiguo). Esta instancia no tiene xlrd habilitado. '
                                  'Por favor, abrilo y guardalo como .XLSX y volvé a importar.'))
            book = xlrd.open_workbook(file_contents=data)
            if sheet_name not in book.sheet_names():
                raise UserError(_('No se encontró la hoja "%s" en el archivo.') % sheet_name)
            sh = book.sheet_by_name(sheet_name)
            headers = [str(sh.cell_value(0, c)).strip() for c in range(sh.ncols)]
            for r in range(1, sh.nrows):
                row = {}
                for c, h in enumerate(headers):
                    v = sh.cell_value(r, c)
                    if isinstance(v, float) and v.is_integer():
                        v = int(v)
                    row[h] = v
                rows.append(row)
        else:
            # Fallback: intentar XLSX; si falla, mensaje de conversión
            try:
                import openpyxl
                openpyxl.load_workbook(io.BytesIO(data), data_only=True)
                raise UserError(_('No se pudo identificar la hoja PRINCIPAL. Verificá el archivo.'))
            except Exception:
                raise UserError(_('Formato no reconocido. '
                                  'Si tu archivo es .XLS, convertí a .XLSX y reintentá.'))

        # Limpiar filas vacías
        rows = [r for r in rows if any((_normalize(v)) for v in r.values())]
        return headers, rows

    def action_import(self):
        self.ensure_one()
        headers, rows = self._read_excel(self.file, self.filename or 'import.xlsx')

        # Detectar columna NV / Número de venta si no se indicó
        name_col = self.name_column or None
        if not name_col:
            lowered = {_lower(h): h for h in headers}
            for cand in HEADER_CANDIDATES:
                if cand in lowered:
                    name_col = lowered[cand]
                    break
            if not name_col:
                for k, original in lowered.items():
                    if any(c in k for c in HEADER_CANDIDATES):
                        name_col = original
                        break

        batch = self.env['dflex.porton.import'].create({
            'name': self.filename or _('Importación'),
            'file_name': self.filename,
            'total_rows': len(rows),
            'note': _('Hoja: PRINCIPAL | Columnas: %s') % ', '.join([h or '-' for h in headers]),
        })
        self.env['dflex.porton'].create_from_rows(rows, batch, name_column=name_col)
        batch.state = 'done'

        action = self.env.ref('dflex_portones_import.action_dflex_porton').read()[0]
        action['domain'] = [('import_id', '=', batch.id)]
        action['context'] = {}
        return action