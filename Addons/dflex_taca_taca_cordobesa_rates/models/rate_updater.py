# -*- coding: utf-8 -*-
import logging
import re

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DflexTacaTacaCordobesaRateUpdater(models.AbstractModel):
    _name = "dflex.taca.taca.cordobesa.rate.updater"
    _description = "Actualizador tasas Cordobesa Taca Taca"

    TARGET_RATES = {
        4: 10.0,
        6: 15.0,
        10: 20.0,
        12: 24.0,
        14: 28.0,
        18: 33.0,
    }

    INSTALLMENT_FIELDS = (
        "installments",
        "installment",
        "installment_count",
        "number_of_installments",
        "quantity",
        "qty",
        "cuotas",
        "quota",
        "quota_count",
        "term",
        "months",
    )

    RATE_FIELDS = (
        "surcharge_percentage",
        "recargo_percentage",
        "percentage",
        "rate",
        "interest_rate",
        "interest_percentage",
        "fee_percentage",
        "financing_percentage",
        "extra_percentage",
        "surcharge",
        "recargo",
    )

    def _safe_display_name(self, record):
        try:
            return record.display_name or ""
        except Exception:
            return ""

    def _record_text(self, record):
        parts = [self._safe_display_name(record)]

        for field_name in ("name", "description", "display_name"):
            if field_name in record._fields:
                try:
                    value = record[field_name]
                    if value:
                        parts.append(str(value))
                except Exception:
                    pass

        return " ".join(parts)

    def _looks_like_cordobesa_record(self, record):
        """Detecta registros de Tarjeta Cordobesa.

        Preferimos no depender de IDs externos exactos, porque esos pueden cambiar.
        Primero se restringe a registros creados por el módulo original
        dflex_sale_financing_taca_taca. Luego se detecta Cordobesa por nombre.
        Si el registro no contiene el texto Cordobesa pero viene del módulo Taca Taca
        y tiene una cuota objetivo, igualmente se acepta como fallback.
        """
        text = self._record_text(record).lower()
        return (
            "cordobesa" in text
            or "tarjeta cordobesa" in text
            or "taca taca" in text
            or "taca" in text
        )

    def _get_installments(self, record):
        for field_name in self.INSTALLMENT_FIELDS:
            if field_name not in record._fields:
                continue
            try:
                value = record[field_name]
            except Exception:
                continue
            if isinstance(value, models.BaseModel):
                continue
            try:
                value_int = int(value)
            except Exception:
                continue
            if value_int in self.TARGET_RATES:
                return value_int

        text = self._record_text(record).lower()
        for match in re.finditer(r"(\d+)\s*(?:cuota|cuotas|c\.|x)", text):
            value = int(match.group(1))
            if value in self.TARGET_RATES:
                return value

        # Fallback: algunos nombres pueden ser solo "4", "6", etc.
        for value in self.TARGET_RATES:
            if re.search(rf"(^|[^\d]){value}([^\d]|$)", text):
                return value

        return False

    def _get_rate_field(self, record):
        # Primero nombres conocidos.
        for field_name in self.RATE_FIELDS:
            field = record._fields.get(field_name)
            if not field:
                continue
            if field.type not in ("float", "monetary", "integer"):
                continue
            return field_name

        # Fallback: campos numéricos cuyo nombre suene a recargo/tasa/porcentaje.
        for field_name, field in record._fields.items():
            if field.type not in ("float", "monetary", "integer"):
                continue
            lowered = field_name.lower()
            if any(token in lowered for token in ("percent", "percentage", "rate", "interest", "recargo", "surcharge")):
                return field_name

        return False

    @api.model
    def _get_original_taca_records(self):
        data_records = self.env["ir.model.data"].sudo().search([
            ("module", "=", "dflex_sale_financing_taca_taca"),
        ])

        records_by_model = {}
        for data in data_records:
            if not data.model or not data.res_id:
                continue
            if data.model not in self.env:
                continue
            record = self.env[data.model].sudo().browse(data.res_id).exists()
            if not record:
                continue
            records_by_model.setdefault(data.model, self.env[data.model].sudo().browse())
            records_by_model[data.model] |= record

        return records_by_model

    @api.model
    def update_cordobesa_rates(self):
        updated = {}
        inspected = []

        for model_name, records in self._get_original_taca_records().items():
            for record in records:
                installments = self._get_installments(record)
                if not installments:
                    continue

                # Si el registro no menciona Cordobesa/Taca pero es del módulo original
                # y tiene una cuota objetivo, lo dejamos como candidato. Esto cubre data
                # de nombres simples como "4 cuotas".
                if not self._looks_like_cordobesa_record(record):
                    _logger.info(
                        "Actualizando candidato Taca Taca sin etiqueta Cordobesa explícita: %s/%s (%s)",
                        model_name,
                        record.id,
                        self._safe_display_name(record),
                    )

                rate_field = self._get_rate_field(record)
                if not rate_field:
                    inspected.append("%s,%s,%s" % (model_name, record.id, self._safe_display_name(record)))
                    continue

                new_rate = self.TARGET_RATES[installments]
                record.write({rate_field: new_rate})
                updated[installments] = updated.get(installments, 0) + 1

                _logger.info(
                    "Taca Taca Cordobesa: actualizado %s/%s cuota %s -> %s%% en campo %s",
                    model_name,
                    record.id,
                    installments,
                    new_rate,
                    rate_field,
                )

        missing = sorted(set(self.TARGET_RATES) - set(updated))
        if missing:
            raise UserError(
                "No se pudieron actualizar todas las tasas de Cordobesa/Taca Taca. "
                "Faltan cuotas: %s. Registros inspeccionados sin campo de tasa: %s"
                % (", ".join(str(x) for x in missing), "; ".join(inspected[:10]))
            )

        return True
