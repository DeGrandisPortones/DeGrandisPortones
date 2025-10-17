
# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError

def _norm(s):
    if not s:
        return ""
    # normalize accents + lowercase + collapse spaces/punct
    s = s.strip()
    s = "".join(c for c in s if c not in "\t\r\n")
    s = "".join({"Á":"A","É":"E","Í":"I","Ó":"O","Ú":"U","Ü":"U","Ñ":"N"}.get(c, c) for c in s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return re.sub(r"\s+", " ", s)

def _to_bool(val):
    if val is None:
        return False
    s = str(val).strip().lower()
    s = {"sí":"si"}.get(s, s)
    return s in {"1","true","t","y","yes","si","s","x","verdadero"}

def _to_int(val):
    try:
        if val is None or val == "":
            return False and 0  # preserve False to skip keys
        # Replace commas commonly used as thousands separator/decimal
        v = str(val).replace(",", ".")
        if re.fullmatch(r"-?\d+(\.0+)?", v):
            return int(float(v))
        return int(v)
    except Exception:
        return False and 0

def _to_date(val):
    if not val:
        return False
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return False

# Mapeo desde encabezados del CSV -> nombres técnicos en Odoo (x_*)
# Usamos claves "normalizadas" con _norm() para cubrir variantes como "rev. tipo", "rev tipo", etc.
CSV_TO_FIELD = {
    # Identificación
    "name": "x_name",
    "nota de venta": "x_nota_de_venta",
    "cliente": "x_nombre_del_cliente",
    "direccion cliente": "x_direccion_del_cliente",
    "distribuidor": "x_distribuidor",
    "estado": "x_estado",
    "partida": "x_partida",

    # Fechas
    "fecha de pedido": "x_fecha_de_pedido",
    "fecha de entrega": "x_fecha_de_entrega",
    "fecha entrega estimada": "x_fecha_de_entrega_estimada",
    "fecha de inicio de produccion": "x_fecha_de_inicio_produccion",
    "fecha de inicio produccion": "x_fecha_de_inicio_produccion",

    # Números
    "dias restantes": "x_dias_restantes",
    "dias transcurrido": "x_dias_transcurridos",
    "dintel ancho": "x_dintel_ancho",
    "hueco chico": "x_hueco_chico",
    "hueco grande": "x_hueco_grande",
    "pierna altura": "x_piernas_altura",
    "brazos": "x_largo_brazo",
    "parantes cantidad": "x_parantes_cantidad",
    "parantes internos cantidad": "x_parantes_internos_cantidad",

    # Textos
    "rev fabricante": "x_color_del_revestimiento",
    "rev tipo": "x_color_sistema",
    "espesor revest": "x_parantes_descripcion",  # si tuvieran un campo propio, cámbialo; lo dejamos como texto
    "dintel tipo": "x_dintel_tipo",
    "listones": "x_listones",
    "instalador": "x_instalacion",
    "par distribucion": "x_parantes_distribucion",
    "par descripcion": "x_parantes_descripcion",
    "pierna tipo": "x_piernas_tipo",
    "observaciones": "x_observaciones",

    # Booleans (sí/no)
    "lucera": "x_lucera",
    "pasador condicion": "x_pasador_condicion",
    "empotraduras": "x_instalacion_empotraduras",
    "puerta": "x_puerta",  # si existe
    # Motor
    "motor posicion": "x_motor_posicion",
    "motor condicion": "x_motor_condicion",
    # alias legacy
    "motor doble": "x_motor_posicion",
}

# Para fields que necesitan conversión específica
FIELD_CONVERTERS = {
    # Booleanos
    "x_lucera": _to_bool,
    "x_pasador_condicion": _to_bool,
    "x_instalacion_empotraduras": _to_bool,
    "x_puerta": _to_bool,
    # Fechas
    "x_fecha_de_pedido": _to_date,
    "x_fecha_de_entrega": _to_date,
    "x_fecha_de_entrega_estimada": _to_date,
    "x_fecha_de_inicio_produccion": _to_date,
    # Enteros
    "x_dias_restantes": _to_int,
    "x_dias_transcurridos": _to_int,
    "x_dintel_ancho": _to_int,
    "x_hueco_chico": _to_int,
    "x_hueco_grande": _to_int,
    "x_piernas_altura": _to_int,
    "x_largo_brazo": _to_int,
    "x_parantes_cantidad": _to_int,
    "x_parantes_internos_cantidad": _to_int,
    "x_nota_de_venta": _to_int,
}

class PortonImportWizard(models.TransientModel):
    _name = "x_dflex.porton.import.wizard"
    _description = "Importar portones desde CSV"

    file = fields.Binary(string="Archivo CSV", required=True)
    filename = fields.Char(string="Nombre de archivo")
    update_if_exists = fields.Boolean(
        string="Actualizar si ya existe",
        help="Si está tildado y se encuentra un registro con el mismo Nombre (x_name) o Nota de Venta, se actualizarán los valores."
    )

    def _find_existing(self, model, vals):
        # Busca por x_nota_de_venta, si no por x_name
        domain = []
        nv = vals.get("x_nota_de_venta")
        nm = vals.get("x_name")
        if nv:
            domain = [("x_nota_de_venta", "=", nv)]
        elif nm:
            domain = [("x_name", "=", nm)]
        if not domain:
            return model.browse()
        return model.search(domain, limit=1)

    def _convert(self, field, value):
        if value in (None, ""):
            return False
        conv = FIELD_CONVERTERS.get(field)
        if conv:
            try:
                return conv(value)
            except Exception:
                return value
        # por defecto devolver string tal cual
        return value

    def _get_model_fields(self, Model):
        # Leer metadatos del modelo en runtime para no fallar si faltan campos
        fields_get = Model.fields_get()
        return set(fields_get.keys())

    def action_import(self):
        if not self.file:
            raise UserError(_("Debe adjuntar un CSV."))

        # Decodificar archivo
        try:
            content = base64.b64decode(self.file)
            # intentar detectar BOM/encoding simple
            text = content.decode("utf-8", errors="ignore")
        except Exception as e:
            raise UserError(_("No se pudo leer el CSV: %s") % e)

        # Preparar CSV reader
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        # Preparar mapeo real por encabezado normalizado
        normalized_header_to_field = {}
        for raw in reader.fieldnames:
            k = _norm(raw)
            if k in CSV_TO_FIELD:
                normalized_header_to_field[k] = CSV_TO_FIELD[k]

        Model = self.env["x_dflex.porton"]
        model_fields = self._get_model_fields(Model)

        created_ids, updated_ids = [], []
        for r_idx, row in enumerate(reader, start=2):  # +1 header, +1 start at 2 for humans
            vals = {}
            # mapear columnas
            for raw_key, raw_value in row.items():
                nk = _norm(raw_key)
                field_name = normalized_header_to_field.get(nk)
                if not field_name or field_name not in model_fields:
                    continue
                vals[field_name] = self._convert(field_name, raw_value)

            if not vals:
                continue

            # fallback: si viene columna "name" o similar y no se mapeó
            if "x_name" not in vals:
                if "name" in row and row["name"].strip():
                    vals["x_name"] = row["name"].strip()

            # crear o actualizar
            existing = self._find_existing(Model, vals)
            if existing and self.update_if_exists:
                existing.write(vals)
                updated_ids.append(existing.id)
            elif existing:
                # si no actualizamos, crear duplicado diferenciando por nombre
                if "x_name" in vals:
                    vals["x_name"] = f"{vals['x_name']} (imp {r_idx})"
                rec = Model.create(vals)
                created_ids.append(rec.id)
            else:
                rec = Model.create(vals)
                created_ids.append(rec.id)

        # Abrimos lista de resultados
        domain_ids = created_ids + updated_ids
        return {
            "type": "ir.actions.act_window",
            "name": _("Portones importados"),
            "res_model": "x_dflex.porton",
            "view_mode": "list,form",
            "target": "current",
            "domain": [("id", "in", domain_ids)] if domain_ids else [],
        }
