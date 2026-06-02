# -*- coding: utf-8 -*-
import logging
import re
import unicodedata

from lxml import html as lxml_html
from lxml import etree

from odoo import models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    # Comprobantes AFIP de exportacion:
    # 19 Factura de exportacion E, 20 Nota de debito E, 21 Nota de credito E.
    DG_EXPORT_DOCUMENT_CODES = {"19", "20", "21"}

    DG_DUE_DATE_PATTERNS = (
        "fecha de vencimiento",
        "due date",
        "vencimiento cae",
        "vto cae",
        "vto. cae",
        "fecha vto cae",
        "fch vto cae",
        "fch. vto cae",
        "cae vence",
    )

    def _render_qweb_html(self, report_ref, docids=None, data=None):
        # Odoo 18 llama a este metodo con los ids como segundo argumento posicional.
        # No usamos res_ids= porque algunas versiones no aceptan ese keyword.
        result = super()._render_qweb_html(report_ref, docids, data=data)
        try:
            if self._dg_should_hide_due_dates(report_ref, res_ids=docids, data=data):
                result = self._dg_strip_due_dates_from_result(result)
        except Exception:
            # No se bloquea la impresion si cambia el HTML del reporte.
            _logger.exception("No se pudieron ocultar fechas de vencimiento en Factura E.")
        return result

    def _dg_should_hide_due_dates(self, report_ref, res_ids=None, data=None):
        report = self._dg_get_report_safely(report_ref)
        if report and report.model != "account.move":
            return False

        ids = self._dg_extract_res_ids(res_ids=res_ids, data=data)
        if not ids:
            return False

        moves = self.env["account.move"].browse(ids).exists()
        if not moves:
            return False

        # Para no afectar facturas locales, solo se aplica si todos los comprobantes
        # del lote son comprobantes E/exportacion.
        return bool(moves) and all(moves.mapped("_dg_is_export_document_for_due_date_hiding"))

    def _dg_get_report_safely(self, report_ref):
        try:
            return self._get_report(report_ref)
        except Exception:
            return False

    @staticmethod
    def _dg_extract_res_ids(res_ids=None, data=None):
        ids = res_ids
        if not ids and isinstance(data, dict):
            ids = data.get("docids") or data.get("ids") or data.get("active_ids")
        if not ids:
            return []
        if isinstance(ids, int):
            return [ids]
        if isinstance(ids, str):
            return [int(item) for item in ids.split(",") if item.strip().isdigit()]
        return list(ids)

    def _dg_strip_due_dates_from_result(self, result):
        if isinstance(result, tuple):
            if not result:
                return result
            html_content = result[0]
            stripped_html = self._dg_strip_due_dates_from_html(html_content)
            return (stripped_html, *result[1:])
        return self._dg_strip_due_dates_from_html(result)

    def _dg_strip_due_dates_from_html(self, html_content):
        if not html_content:
            return html_content

        is_bytes = isinstance(html_content, (bytes, bytearray))
        text = bytes(html_content).decode("utf-8", errors="ignore") if is_bytes else str(html_content)

        try:
            document = lxml_html.fromstring(text)
        except (etree.ParserError, TypeError, ValueError):
            return self._dg_strip_due_dates_by_regex(text).encode("utf-8") if is_bytes else self._dg_strip_due_dates_by_regex(text)

        candidates = self._dg_find_due_date_elements(document)
        for element in candidates:
            self._dg_remove_due_date_line(element)

        rendered = etree.tostring(document, encoding="unicode", method="html")
        return rendered.encode("utf-8") if is_bytes else rendered

    def _dg_find_due_date_elements(self, document):
        candidates = []
        seen = set()

        for element in document.xpath("//*[not(self::script) and not(self::style)]"):
            text = self._dg_normalize_text(" ".join(element.itertext()))
            if not text:
                continue
            if not self._dg_contains_due_date_label(text):
                continue

            # Evita tomar contenedores grandes como body/page/report completo.
            if len(text) > 220:
                continue

            key = id(element)
            if key not in seen:
                candidates.append(element)
                seen.add(key)

        # Primero elementos mas chicos: strong/span/td puntuales antes que divs padres.
        candidates.sort(key=lambda el: len(self._dg_normalize_text(" ".join(el.itertext()))))
        return candidates

    def _dg_remove_due_date_line(self, element):
        if element.getparent() is None:
            return

        # Si esta dentro de una fila de tabla chica, se elimina toda la fila.
        tr = self._dg_closest_tag(element, {"tr"})
        if tr is not None and len(self._dg_normalize_text(" ".join(tr.itertext()))) <= 220:
            self._dg_remove_node(tr)
            return

        # Si el label esta en un bloque corto independiente, se elimina el bloque.
        block = self._dg_closest_short_block(element)
        if block is not None:
            block_text = self._dg_normalize_text(" ".join(block.itertext()))
            # No borrar el bloque completo si tambien contiene datos utiles como origen/incoterm.
            if not any(token in block_text for token in ("origen", "source", "incoterm", "referencia", "reference")):
                self._dg_remove_node(block)
                return

        # Fallback: borra el label, el valor inmediato y el salto de linea siguiente.
        self._dg_remove_inline_line(element)

    def _dg_closest_short_block(self, element):
        current = element
        while current is not None:
            tag = (current.tag or "").lower() if isinstance(current.tag, str) else ""
            if tag in {"p", "li", "div", "td", "th", "span"}:
                text = self._dg_normalize_text(" ".join(current.itertext()))
                if len(text) <= 180:
                    return current
            current = current.getparent()
        return None

    @staticmethod
    def _dg_closest_tag(element, tags):
        current = element
        while current is not None:
            tag = (current.tag or "").lower() if isinstance(current.tag, str) else ""
            if tag in tags:
                return current
            current = current.getparent()
        return None

    def _dg_remove_inline_line(self, element):
        parent = element.getparent()
        if parent is None:
            self._dg_remove_node(element)
            return

        # Si el parent usa br para separar lineas, borra desde el label hasta el br.
        next_node = element.getnext()
        while next_node is not None:
            node_after = next_node.getnext()
            tag = (next_node.tag or "").lower() if isinstance(next_node.tag, str) else ""
            self._dg_remove_node(next_node)
            if tag == "br":
                break
            next_node = node_after

        element.tail = ""
        self._dg_remove_node(element)

    @staticmethod
    def _dg_remove_node(node):
        parent = node.getparent()
        if parent is None:
            return
        previous = node.getprevious()
        if previous is not None:
            previous.tail = (previous.tail or "") + (node.tail or "")
        elif node.tail:
            parent.text = (parent.text or "") + node.tail
        parent.remove(node)

    @classmethod
    def _dg_contains_due_date_label(cls, normalized_text):
        return any(pattern in normalized_text for pattern in cls.DG_DUE_DATE_PATTERNS)

    @staticmethod
    def _dg_normalize_text(value):
        if not value:
            return ""
        normalized = unicodedata.normalize("NFKD", value)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = normalized.lower()
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _dg_strip_due_dates_by_regex(self, text):
        # Fallback para HTML no parseable: elimina lineas completas que contengan labels de vencimiento.
        lines = text.splitlines()
        kept = []
        for line in lines:
            normalized = self._dg_normalize_text(line)
            if self._dg_contains_due_date_label(normalized):
                continue
            kept.append(line)
        return "\n".join(kept)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _dg_is_export_document_for_due_date_hiding(self):
        self.ensure_one()
        document_type = self._dg_get_record_field("l10n_latam_document_type_id")
        if not document_type:
            return False

        code = (self._dg_get_record_field_value(document_type, "code") or "").strip()
        if code in IrActionsReport.DG_EXPORT_DOCUMENT_CODES:
            return True

        name = self._dg_get_record_field_value(document_type, "name") or ""
        letter = self._dg_get_record_field_value(document_type, "l10n_ar_letter") or ""
        normalized_name = IrActionsReport._dg_normalize_text(name)
        normalized_letter = IrActionsReport._dg_normalize_text(letter)
        return normalized_letter == "e" or "exportacion" in normalized_name or "export" in normalized_name

    def _dg_get_record_field(self, field_name):
        self.ensure_one()
        if field_name not in self._fields:
            return False
        return self[field_name]

    @staticmethod
    def _dg_get_record_field_value(record, field_name):
        if not record or field_name not in record._fields:
            return False
        return record[field_name]
