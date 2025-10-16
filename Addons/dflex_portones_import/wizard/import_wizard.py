from odoo import api, fields, models
from odoo.exceptions import UserError
import base64, io, csv, unicodedata, re

# =========================
# Mapa ENCABEZADO -> CAMPO
# =========================
# Clave: encabezado normalizado (minúsculas, sin tildes, espacios compactados)
# Valor: nombre técnico EXACTO en x_dflex.porton (ajústalo a lo que creaste en Studio)
HEADER_MAP = {
    "nota de venta": "x_nota_de_venta",
    "cliente +3000": "x_nombre_del_cliente",
    "direccion cliente": "x_direccion_del_cliente",
    "distribuidor": "x_distribuidor",

    # Agrega más pares acá según tu CSV:
    # "fecha de pedido": "x_fecha_de_pedido",
    # "estado": "x_estado",
    # ...
}

def _norm(s):
    return (str(s) if s is not None else "").strip()

def _normalize_header(h):
    """Quita tildes, pasa a minúsculas y compacta espacios."""
    s = _norm(h)
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

def _looks_like_csv(text):
    sample = "\n".join(text.splitlines()[:3])
    return (sample.count(",") >= 1) or (sample.count(";") >= 1)

class DflexPortonImportBatch(models.TransientModel):
    _name = "dflex.porton.import"
    _description = "Lote de importación de Portones"

    name = fields.Char(default="Importación CSV")

class DflexPortonImportWizard(models.TransientModel):
    _name = "dflex.porton.import.wizard"
    _description = "Importar portones desde CSV (1 encabezado; datos desde fila 2)"

    file = fields.Binary(required=True, string="Archivo CSV")
    filename = fields.Char(string="Nombre de archivo")

    def _read_csv(self):
        data = base64.b64decode(self.file or b"")
        if not data:
            raise UserError("El archivo está vacío.")
        try:
            text = data.decode("utf-8")
        except Exception:
            text = data.decode("latin-1", errors="replace")
        if not _looks_like_csv(text):
            raise UserError("El archivo no parece un CSV válido.")
        first = text.splitlines()[0] if text else ""
        delimiter = ";" if first.count(";") > first.count(",") else ","
        reader = csv.reader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
        if len(rows) < 2:
            raise UserError("CSV inválido: se necesita 1 fila de encabezado y datos desde la fila 2.")
        headers = [_norm(x) for x in rows[0]]
        data_rows = rows[1:]
        return headers, data_rows

    def _build_index_map(self, headers):
        """Devuelve dict: índice_columna -> nombre_de_campo (en x_dflex.porton)"""
        idx_map = {}
        for i, h in enumerate(headers):
            key = _normalize_header(h)
            if key in HEADER_MAP:
                idx_map[i] = HEADER_MAP[key]
        if not idx_map:
            raise UserError("Ningún encabezado coincide con el mapa esperado. Encabezados mínimos: %s" %
                            ", ".join(HEADER_MAP.keys()))
        return idx_map

    def action_import(self):
        self.ensure_one()
        headers, data_rows = self._read_csv()
        idx_map = self._build_index_map(headers)

        Porton = self.env["x_dflex.porton"].sudo()  # <-- Tu modelo Studio
        created_ids = []
        for r_idx, row in enumerate(data_rows, start=2):
            vals = {}
            name_fallback = None
            for i, cell in enumerate(row):
                if i in idx_map:
                    field_name = idx_map[i]
                    val = "" if cell is None else str(cell)
                    vals[field_name] = val
                    # Tomamos "name" del N° de venta si existe
                    if field_name in ("x_nota_de_venta", "name"):
                        name_fallback = val
            if "name" not in vals:
                vals["name"] = name_fallback or f"Fila {r_idx}"

            rec = Porton.create(vals)
            created_ids.append(rec.id)

        # Devolvemos acción sin depender de XML del modelo
        return {
            "type": "ir.actions.act_window",
            "name": "Portones importados",
            "res_model": "x_dflex.porton",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("id", "in", created_ids)],
        }
