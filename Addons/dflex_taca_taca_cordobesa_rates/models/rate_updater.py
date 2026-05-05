# -*- coding: utf-8 -*-
import logging

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

    @api.model
    def _get_rate_model(self):
        if "sale.financing.rate" not in self.env:
            raise UserError("No existe el modelo sale.financing.rate. Revisar que dflex_sale_financing_taca_taca esté instalado.")
        return self.env["sale.financing.rate"].sudo().with_context(active_test=False)

    def _get_rate_percent_field(self, Rate):
        if "rate_percent" in Rate._fields:
            return "rate_percent"

        for field_name in (
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
        ):
            if field_name in Rate._fields:
                return field_name

        raise UserError("No se encontró el campo de porcentaje/recargo en sale.financing.rate.")

    def _get_name(self, installments, rate):
        return "Tarjeta Cordobesa - %s cuotas (+%.2f%%)" % (installments, rate)

    def _find_cordobesa_plans(self, Rate):
        domain = []
        if "card_type" in Rate._fields:
            domain.append(("card_type", "=", "cordobesa"))

        records = Rate.search(domain)
        if not records:
            raise UserError("No se encontraron registros de Tarjeta Cordobesa en sale.financing.rate.")

        if "plan_id" in Rate._fields:
            return records.mapped("plan_id")

        return [False]

    def _find_rate(self, Rate, plan, installments):
        domain = []
        if "card_type" in Rate._fields:
            domain.append(("card_type", "=", "cordobesa"))
        if "installments" in Rate._fields:
            domain.append(("installments", "=", installments))
        if plan and "plan_id" in Rate._fields:
            domain.append(("plan_id", "=", plan.id))

        return Rate.search(domain)

    def _get_template(self, Rate, plan):
        domain = []
        if "card_type" in Rate._fields:
            domain.append(("card_type", "=", "cordobesa"))
        if plan and "plan_id" in Rate._fields:
            domain.append(("plan_id", "=", plan.id))
        return Rate.search(domain, limit=1)

    def _build_defaults(self, template, installments, rate, rate_field):
        vals = {
            rate_field: rate,
        }

        if "active" in template._fields:
            vals["active"] = True
        if "card_type" in template._fields:
            vals["card_type"] = "cordobesa"
        if "installments" in template._fields:
            vals["installments"] = installments
        if "name" in template._fields:
            vals["name"] = self._get_name(installments, rate)
        if "description" in template._fields:
            vals["description"] = self._get_name(installments, rate)

        return vals

    def _ensure_xmlid(self, record, installments, plan):
        if not record:
            return

        suffix = "%s_cuotas" % installments
        if plan:
            suffix = "plan_%s_%s" % (plan.id, suffix)

        xmlid_name = "cordobesa_%s" % suffix

        existing = self.env["ir.model.data"].sudo().search([
            ("module", "=", "dflex_taca_taca_cordobesa_rates"),
            ("name", "=", xmlid_name),
        ], limit=1)

        if existing:
            if existing.model != record._name or existing.res_id != record.id:
                existing.write({"model": record._name, "res_id": record.id})
            return

        self.env["ir.model.data"].sudo().create({
            "module": "dflex_taca_taca_cordobesa_rates",
            "name": xmlid_name,
            "model": record._name,
            "res_id": record.id,
            "noupdate": True,
        })

    @api.model
    def update_cordobesa_rates(self):
        """Actualiza/crea cuotas Cordobesa sin duplicar claves únicas.

        La búsqueda usa active_test=False porque algunas cuotas pueden existir
        inactivas y no aparecer en la vista. Ese era el caso que provocaba el
        duplicate key (plan_id, card_type, installments).
        """
        Rate = self._get_rate_model()
        rate_field = self._get_rate_percent_field(Rate)
        plans = self._find_cordobesa_plans(Rate)

        updated = []
        created = []

        for plan in plans:
            template = self._get_template(Rate, plan)
            if not template:
                continue

            for installments, rate in self.TARGET_RATES.items():
                records = self._find_rate(Rate, plan, installments)
                vals = {
                    rate_field: rate,
                }
                if "active" in Rate._fields:
                    vals["active"] = True
                if "name" in Rate._fields:
                    vals["name"] = self._get_name(installments, rate)

                if records:
                    records.write(vals)
                    for record in records:
                        self._ensure_xmlid(record, installments, plan)
                    updated.append((plan.id if plan else False, installments, len(records)))
                    _logger.info(
                        "Taca Taca Cordobesa: actualizado plan %s cuota %s -> %s%% en %s registro(s)",
                        plan.display_name if plan else "-",
                        installments,
                        rate,
                        len(records),
                    )
                    continue

                defaults = self._build_defaults(template, installments, rate, rate_field)
                new_record = template.copy(default=defaults)
                self._ensure_xmlid(new_record, installments, plan)
                created.append((plan.id if plan else False, installments, new_record.id))
                _logger.info(
                    "Taca Taca Cordobesa: creado plan %s cuota %s -> %s%% registro %s",
                    plan.display_name if plan else "-",
                    installments,
                    rate,
                    new_record.id,
                )

        if not updated and not created:
            raise UserError("No se pudo actualizar ni crear ninguna tasa Cordobesa/Taca Taca.")

        return True
