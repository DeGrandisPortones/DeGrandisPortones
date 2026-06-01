from collections import defaultdict
from unicodedata import normalize

from odoo import _, api, fields, models
from odoo.tools.misc import format_date, formatLang


class ReportDgAccountStatement(models.AbstractModel):
    _name = "report.dg_resumen_cta_cte.report_account_statement"
    _description = "Reporte de cuenta corriente"

    GROUPS = (
        ("fca", "Subtotal FCA"),
        ("internas", "Subtotal Internas"),
    )

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env["dg.account.statement.wizard"].browse(docids)
        statements = []
        for wizard in wizards:
            for statement in self._get_wizard_statements(wizard):
                statements.append(self._filter_statement_for_print(statement, wizard.print_group))
        return {
            "doc_ids": docids,
            "doc_model": "dg.account.statement.wizard",
            "docs": wizards,
            "statements": statements,
            "groups": self.GROUPS,
            "format_amount": self._format_amount,
            "format_report_date": self._format_report_date,
        }

    def _format_amount(self, amount, currency):
        return formatLang(self.env, amount or 0.0, currency_obj=currency)

    def _format_report_date(self, value):
        if not value:
            return ""
        return format_date(self.env, value)

    def _normalize_text(self, value):
        value = value or ""
        value = normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
        return " ".join(value.lower().strip().split())

    def _journal_group(self, journal):
        group = journal.dg_client_sales_report_group
        if group in ("fca", "internas"):
            return group
        normalized_name = self._normalize_text(journal.name)
        if "preimpreso" in normalized_name:
            return "fca"
        if "interna" in normalized_name:
            return "internas"
        if "saldos iniciales fca" in normalized_name:
            return "fca"
        if "saldos iniciales internas" in normalized_name:
            return "internas"
        return False

    def _line_direct_group(self, line):
        group = line.dg_client_sales_report_group
        if group in ("fca", "internas"):
            return group
        return self._journal_group(line.move_id.journal_id)

    def _invoice_line_group(self, line):
        group = line.dg_client_sales_report_group
        if group in ("fca", "internas"):
            return group
        return self._journal_group(line.move_id.journal_id)

    def _counterpart_group(self, line):
        group = line.dg_client_sales_report_group
        if group in ("fca", "internas"):
            return group
        move = line.move_id
        if move.move_type in ("out_invoice", "out_refund"):
            return self._journal_group(move.journal_id)
        return self._line_direct_group(line)

    def _get_partial_reconcile_records(self, line):
        return line.matched_debit_ids | line.matched_credit_ids

    def _get_counterpart_line(self, partial, line):
        if partial.debit_move_id == line:
            return partial.credit_move_id
        return partial.debit_move_id

    def _get_document_name(self, line, group=False, split=False):
        move = line.move_id
        document = move.name if move.name and move.name != "/" else False
        document = document or line.name or move.ref or _("Sin numero")
        if split and group:
            label = dict(self.GROUPS).get(group, group)
            document = "%s (%s)" % (document, label)
        return document

    def _append_statement_line(self, bucket, line, group, amount, entry_type, split=False):
        if group not in ("fca", "internas") or abs(amount or 0.0) < 0.005:
            return
        bucket.append(
            {
                "id": "%s-%s-%s" % (line.id, group, len(bucket)),
                "date": line.date,
                "document": self._get_document_name(line, group=group, split=split),
                "description": line.ref or line.move_id.ref or line.move_id.invoice_origin or "",
                "amount": amount,
                "entry_type": entry_type,
                "move_id": line.move_id.id,
                "line_id": line.id,
            }
        )

    def _classify_and_append_line(self, bucket, line):
        move = line.move_id

        # Ventas, notas de credito y notas de debito de cliente.
        if move.move_type in ("out_invoice", "out_refund"):
            group = self._invoice_line_group(line)
            self._append_statement_line(bucket, line, group, line.balance, "sale")
            return

        direct_group = line.dg_client_sales_report_group
        journal_group = self._journal_group(move.journal_id)

        # Saldos iniciales/apertura: no se muestran como movimientos del periodo.
        # Solo forman saldo anterior cuando quedan antes de Fecha desde.
        group = direct_group if direct_group in ("fca", "internas") else journal_group
        if not line.payment_id:
            if group in ("fca", "internas"):
                self._append_statement_line(bucket, line, group, line.balance, "opening")
            return

        # Cobranzas/recibos. Si estan conciliados, se reparten segun la factura,
        # nota o saldo inicial contra el que se aplicaron.
        partials = self._get_partial_reconcile_records(line)
        if partials:
            amount_by_group = defaultdict(float)
            sign = 1.0 if line.balance >= 0.0 else -1.0
            for partial in partials:
                counterpart = self._get_counterpart_line(partial, line)
                counterpart_group = self._counterpart_group(counterpart)
                if counterpart_group in ("fca", "internas"):
                    amount_by_group[counterpart_group] += sign * partial.amount
            for counterpart_group, amount in amount_by_group.items():
                self._append_statement_line(
                    bucket,
                    line,
                    counterpart_group,
                    amount,
                    "collection",
                    split=len(amount_by_group) > 1,
                )
            return

        # Recibos/anticipos sin imputar: solo entran si se pueden clasificar.
        if group in ("fca", "internas"):
            self._append_statement_line(bucket, line, group, line.balance, "collection")

    def _get_lines_for_wizard(self, wizard):
        domain = [
            ("company_id", "=", wizard.company_id.id),
            ("parent_state", "=", "posted"),
            ("account_id.account_type", "=", "asset_receivable"),
            ("partner_id", "!=", False),
        ]
        if wizard.date_to:
            domain.append(("date", "<=", wizard.date_to))
        if wizard.partner_id:
            domain.append(("partner_id", "child_of", wizard.partner_id.commercial_partner_id.id))
        elif wizard.partner_ids:
            domain.append(("partner_id", "child_of", wizard.partner_ids.ids))

        lines = self.env["account.move.line"].search(domain, order="date asc, id asc")
        bucket = []
        for line in lines:
            self._classify_and_append_line(bucket, line)
        return bucket

    def _get_partners_from_lines(self, wizard, lines):
        if wizard.partner_id:
            return wizard.partner_id.commercial_partner_id
        if wizard.partner_ids:
            partners = wizard.partner_ids.mapped("commercial_partner_id")
            return partners.sorted(lambda p: p.name or "")

        partner_ids = set()
        line_ids = [item["line_id"] for item in lines]
        if line_ids:
            aml_lines = self.env["account.move.line"].browse(line_ids)
            partner_ids.update(aml_lines.mapped("partner_id.commercial_partner_id").ids)
        return self.env["res.partner"].browse(list(partner_ids)).sorted(lambda p: p.name or "")

    def _prepare_statement_for_partner(self, wizard, partner, all_lines):
        currency = wizard.company_id.currency_id
        partner_child_ids = set(self.env["res.partner"].search([("id", "child_of", partner.id)]).ids)

        line_records = self.env["account.move.line"].browse([item["line_id"] for item in all_lines])
        line_partner_map = {line.id: line.partner_id.id for line in line_records}

        groups_data = []
        total_balance = 0.0
        date_from = wizard.date_from

        for group_key, group_label in self.GROUPS:
            raw_lines = [
                item for item in all_lines
                if item.get("line_id") in line_partner_map
                and line_partner_map[item["line_id"]] in partner_child_ids
                and self._line_group_from_item(item) == group_key
            ]

            previous_balance = 0.0
            period_lines = []
            for item in raw_lines:
                if date_from and item["date"] and item["date"] < date_from:
                    previous_balance += item["amount"]
                elif (
                    (not date_from or not item["date"] or item["date"] >= date_from)
                    and item.get("entry_type") in ("sale", "collection")
                    and abs(item.get("amount") or 0.0) >= 0.005
                ):
                    period_lines.append(item.copy())

            period_lines.sort(key=lambda item: (item["date"] or fields.Date.today(), item["line_id"], item["id"]))

            prepared_lines = []
            running_balance = 0.0
            total_debit = 0.0
            total_credit = 0.0

            if wizard.include_initial_balance and date_from and abs(previous_balance) > 0.004:
                running_balance = previous_balance
                if previous_balance >= 0.0:
                    total_debit += previous_balance
                else:
                    total_credit += abs(previous_balance)
                prepared_lines.append(
                    {
                        "date": False,
                        "document": _("Saldo anterior"),
                        "description": "",
                        "entry_type": "opening",
                        "debit": previous_balance if previous_balance > 0.0 else 0.0,
                        "credit": abs(previous_balance) if previous_balance < 0.0 else 0.0,
                        "balance": running_balance,
                    }
                )

            for item in period_lines:
                amount = item["amount"]
                running_balance += amount
                debit = amount if amount > 0.0 else 0.0
                credit = abs(amount) if amount < 0.0 else 0.0
                total_debit += debit
                total_credit += credit
                prepared_lines.append(
                    {
                        "date": item["date"],
                        "document": item["document"],
                        "description": item["description"],
                        "entry_type": item.get("entry_type") or "",
                        "debit": debit,
                        "credit": credit,
                        "balance": running_balance,
                    }
                )

            group_balance = running_balance
            total_balance += group_balance
            groups_data.append(
                {
                    "key": group_key,
                    "label": group_label,
                    "lines": prepared_lines,
                    "debit": total_debit,
                    "credit": total_credit,
                    "balance": group_balance,
                    "has_data": bool(prepared_lines) or abs(total_debit) > 0.004 or abs(total_credit) > 0.004 or abs(group_balance) > 0.004,
                }
            )

        return {
            "wizard": wizard,
            "partner": partner,
            "company": wizard.company_id,
            "currency": currency,
            "date_from": wizard.date_from,
            "date_to": wizard.date_to,
            "groups": groups_data,
            "total_balance": total_balance,
            "has_data": any(group["has_data"] for group in groups_data),
        }

    def _filter_statement_for_print(self, statement, print_group):
        if print_group in ("fca", "internas"):
            groups = [group for group in statement["groups"] if group["key"] == print_group and group.get("has_data")]
        else:
            groups = [group for group in statement["groups"] if group.get("has_data")]
        filtered = dict(statement)
        filtered["groups"] = groups
        filtered["total_balance"] = sum(group["balance"] for group in groups)
        return filtered

    def _line_group_from_item(self, item):
        identifier = item.get("id") or ""
        parts = str(identifier).split("-")
        if len(parts) >= 2 and parts[1] in ("fca", "internas"):
            return parts[1]
        return False

    def _get_wizard_statements(self, wizard):
        all_lines = self._get_lines_for_wizard(wizard)
        partners = self._get_partners_from_lines(wizard, all_lines)
        return [self._prepare_statement_for_partner(wizard, partner, all_lines) for partner in partners]
