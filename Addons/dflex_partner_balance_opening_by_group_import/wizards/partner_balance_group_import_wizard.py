
# -*- coding: utf-8 -*-
import base64
import csv
import io
import re
from decimal import Decimal, InvalidOperation

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DflexPartnerBalanceGroupImportWizard(models.TransientModel):
    _name = "dflex.partner.balance.group.import.wizard"
    _description = "Importar saldos clientes por grupo reporte"

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Diario de apertura",
        required=True,
        domain="[('company_id', '=', company_id)]",
    )
    report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo reporte cliente",
        required=True,
        default="fca",
    )
    receivable_account_id = fields.Many2one(
        "account.account",
        string="Cuenta saldo cliente",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
        help="Cuenta contable de clientes/saldos a usar en todas las líneas de contacto.",
    )
    capital_account_id = fields.Many2one(
        "account.account",
        string="Cuenta Capital integrado",
        required=True,
        domain="[('company_ids', 'in', company_id)]",
        help="Contrapartida acumulada para este grupo. Se elige antes de importar.",
    )
    accounting_date = fields.Date(
        string="Fecha contable",
        required=True,
        default=fields.Date.context_today,
    )
    csv_file = fields.Binary(string="Archivo CSV", required=True)
    csv_filename = fields.Char(string="Nombre archivo")
    create_missing_partners = fields.Boolean(
        string="Crear contactos faltantes",
        default=False,
        help="Recomendado dejar desactivado en la primera simulación.",
    )
    dry_run = fields.Boolean(string="Solo simular, no crear nada", default=True)
    post_move = fields.Boolean(string="Publicar asiento", default=False)
    result = fields.Text(string="Resultado", readonly=True)

    @api.onchange("company_id")
    def _onchange_company_id(self):
        if self.company_id:
            self.journal_id = False
            self.receivable_account_id = False
            self.capital_account_id = self._find_account_by_code("3.1.1.01.002", self.company_id)

    def _account_company_domain(self, company):
        Account = self.env["account.account"]
        if "company_ids" in Account._fields:
            return [("company_ids", "in", company.id)]
        if "company_id" in Account._fields:
            return [("company_id", "=", company.id)]
        return []

    def _find_account_by_code(self, code, company):
        Account = self.env["account.account"].with_company(company).with_context(allowed_company_ids=[company.id])
        return Account.search([("code", "=", code)] + self._account_company_domain(company), limit=1)

    def _validate_configuration(self):
        self.ensure_one()
        company = self.company_id
        if self.journal_id.company_id != company:
            raise UserError(_("El diario no pertenece a la compañía seleccionada."))
        for account, label in [
            (self.receivable_account_id, _("Cuenta saldo cliente")),
            (self.capital_account_id, _("Cuenta Capital integrado")),
        ]:
            if not account:
                raise UserError(_("Falta configurar %s.") % label)
            if "company_ids" in account._fields and company not in account.company_ids:
                raise UserError(_("%s no pertenece a la compañía seleccionada.") % label)
            if "company_id" in account._fields and account.company_id != company:
                raise UserError(_("%s no pertenece a la compañía seleccionada.") % label)
        Line = self.env["account.move.line"]
        if "dg_client_sales_report_group" not in Line._fields:
            raise UserError(
                _("No existe el campo dg_client_sales_report_group en apuntes contables. Instalá/actualizá dg_client_sales_report.")
            )

    def _decode_csv(self):
        raw = base64.b64decode(self.csv_file or b"")
        if not raw:
            raise UserError(_("Subí un archivo CSV."))
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise UserError(_("No se pudo leer el CSV. Guardalo como UTF-8 o ANSI/Latin-1."))

    def _normalize_header(self, name):
        key = (name or "").strip().lower()
        key = key.replace(" ", "_").replace("-", "_")
        aliases = {
            "razón_social": "razsoc",
            "razon_social": "razsoc",
            "cliente": "razsoc",
            "nombre": "razsoc",
            "contacto": "razsoc",
            "cuit": "cuit",
            "vat": "cuit",
            "saldo": "saldo",
            "importe": "saldo",
            "monto": "saldo",
            "grupo": "grupo",
            "tipo": "grupo",
        }
        return aliases.get(key, key)

    def _iter_csv_rows(self):
        text = self._decode_csv()
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = ";"

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        if not reader.fieldnames:
            raise UserError(_("El CSV no tiene encabezados."))

        normalized = {name: self._normalize_header(name) for name in reader.fieldnames}
        required = {"razsoc", "saldo"}
        missing = required - set(normalized.values())
        if missing:
            raise UserError(_("Faltan columnas obligatorias en el CSV: %s") % ", ".join(sorted(missing)))

        for line_number, row in enumerate(reader, start=2):
            data = {}
            for original_name, value in row.items():
                if original_name is None:
                    continue
                key = normalized.get(original_name)
                if key:
                    data[key] = (value or "").strip()
            if not any(data.values()):
                continue
            data["_line_number"] = line_number
            yield data

    def _parse_amount(self, value, line_number):
        if not value:
            raise UserError(_("Línea %s: falta saldo.") % line_number)
        clean = re.sub(r"[^0-9,.\-]", "", value)
        if "," in clean and "." in clean:
            if clean.rfind(",") > clean.rfind("."):
                clean = clean.replace(".", "").replace(",", ".")
            else:
                clean = clean.replace(",", "")
        elif "," in clean:
            clean = clean.replace(",", ".")
        try:
            return Decimal(clean)
        except InvalidOperation:
            raise UserError(_("Línea %s: saldo inválido: %s") % (line_number, value))

    def _clean_cuit(self, value):
        clean = re.sub(r"\D", "", value or "")
        return clean or False

    def _find_partner(self, name, cuit):
        Partner = self.env["res.partner"].with_company(self.company_id).with_context(allowed_company_ids=[self.company_id.id])
        if cuit:
            partner = Partner.search([("vat", "=", cuit)], limit=1)
            if partner:
                return partner, "cuit"
            formatted = "%s-%s-%s" % (cuit[:2], cuit[2:10], cuit[10:]) if len(cuit) == 11 else cuit
            partner = Partner.search([("vat", "=", formatted)], limit=1)
            if partner:
                return partner, "cuit_formateado"
        if name:
            partner = Partner.search([("name", "ilike", name)], limit=1)
            if partner:
                return partner, "nombre"
        return False, "no_encontrado"

    def _create_partner(self, name, cuit):
        Partner = self.env["res.partner"].with_company(self.company_id).with_context(allowed_company_ids=[self.company_id.id])
        vals = {
            "name": name or _("Cliente apertura sin nombre"),
            "customer_rank": 1,
            "company_type": "company",
        }
        if cuit:
            vals["vat"] = cuit
        return Partner.create(vals)

    def _row_belongs_to_selected_group(self, row):
        csv_group = (row.get("grupo") or "").strip().upper()
        if not csv_group:
            return True
        selected = "FCA" if self.report_group == "fca" else "INTERNO"
        accepted = [selected]
        if selected == "INTERNO":
            accepted.append("INTERNAS")
        return csv_group in accepted

    def _prepare_partner_line(self, row, partner, amount):
        name = row.get("razsoc") or partner.display_name
        label = "Apertura saldo cliente %s - %s" % (dict(self._fields["report_group"].selection)[self.report_group], name)
        abs_amount = abs(amount)
        if amount >= 0:
            debit = abs_amount
            credit = Decimal("0.00")
        else:
            debit = Decimal("0.00")
            credit = abs_amount
        return (0, 0, {
            "name": label,
            "account_id": self.receivable_account_id.id,
            "partner_id": partner.id,
            "dg_client_sales_report_group": self.report_group,
            "debit": float(debit),
            "credit": float(credit),
        })

    def _prepare_capital_line(self, label, debit, credit):
        return (0, 0, {
            "name": label,
            "account_id": self.capital_account_id.id,
            "debit": float(debit),
            "credit": float(credit),
        })

    def _prepare_move_vals(self, line_ids):
        group_label = dict(self._fields["report_group"].selection)[self.report_group]
        return {
            "move_type": "entry",
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "date": self.accounting_date,
            "ref": "Apertura saldos clientes %s" % group_label,
            "line_ids": line_ids,
        }

    def action_import(self):
        self.ensure_one()
        self._validate_configuration()

        ctx = dict(self.env.context, allowed_company_ids=[self.company_id.id], force_company=self.company_id.id)
        wizard = self.with_company(self.company_id).with_context(ctx)
        Move = self.env["account.move"].with_company(self.company_id).with_context(ctx)

        rows = list(wizard._iter_csv_rows())
        if not rows:
            raise UserError(_("No hay filas para importar."))

        selected_rows = [row for row in rows if wizard._row_belongs_to_selected_group(row)]
        if not selected_rows:
            raise UserError(_("El CSV no tiene filas para el grupo seleccionado."))

        partner_lines = []
        result_lines = []
        errors = []
        missing_partners = []
        total = Decimal("0.00")
        capital_debit = Decimal("0.00")
        capital_credit = Decimal("0.00")
        count = 0

        for row in selected_rows:
            line_number = row["_line_number"]
            name = row.get("razsoc") or ""
            cuit = wizard._clean_cuit(row.get("cuit"))
            amount = wizard._parse_amount(row.get("saldo"), line_number)
            if amount == 0:
                continue

            partner, match_method = wizard._find_partner(name, cuit)
            if not partner:
                if wizard.create_missing_partners and not wizard.dry_run:
                    partner = wizard._create_partner(name, cuit)
                    match_method = "creado"
                else:
                    missing_partners.append("Línea %s | %s | CUIT %s" % (line_number, name, cuit or "sin CUIT"))
                    match_method = "no_encontrado"

            count += 1
            total += amount
            result_lines.append("%s | $ %.2f | %s | %s" % (name, amount, cuit or "sin CUIT", match_method))

            if partner:
                partner_lines.append(wizard._prepare_partner_line(row, partner, amount))
                if amount >= 0:
                    capital_credit += abs(amount)
                else:
                    capital_debit += abs(amount)

        if missing_partners and not wizard.create_missing_partners:
            errors.append(
                _("Contactos no encontrados. Corregí/importá contactos primero o activá 'Crear contactos faltantes' después de revisar la simulación.\n%s")
                % "\n".join(missing_partners[:100])
            )

        output = [
            "SIMULACIÓN: no se creó nada." if wizard.dry_run else "IMPORTACIÓN REAL ejecutada.",
            "Compañía: %s" % wizard.company_id.display_name,
            "Diario: %s" % wizard.journal_id.display_name,
            "Grupo reporte cliente: %s" % dict(wizard._fields["report_group"].selection)[wizard.report_group],
            "Cuenta saldo cliente: %s" % wizard.receivable_account_id.display_name,
            "Capital integrado: %s" % wizard.capital_account_id.display_name,
            "Cantidad de saldos: %s" % count,
            "Total grupo: $ %.2f" % total,
            "Capital integrado al Debe: $ %.2f" % capital_debit,
            "Capital integrado al Haber: $ %.2f" % capital_credit,
            "Asiento: único",
            "Estado asiento: %s" % ("publicado" if wizard.post_move else "borrador"),
        ]

        if errors:
            output.append("")
            output.append("ADVERTENCIAS / ERRORES:")
            output.extend(errors)

        if errors and not wizard.dry_run:
            raise UserError("\n".join(errors))

        if not wizard.dry_run:
            line_ids = list(partner_lines)
            capital_label = "Apertura saldos clientes %s - Capital integrado" % dict(wizard._fields["report_group"].selection)[wizard.report_group]
            if capital_debit:
                line_ids.append(wizard._prepare_capital_line(capital_label, capital_debit, Decimal("0.00")))
            if capital_credit:
                line_ids.append(wizard._prepare_capital_line(capital_label, Decimal("0.00"), capital_credit))
            if not line_ids:
                raise UserError(_("No hay líneas válidas para crear el asiento."))

            move = Move.create(wizard._prepare_move_vals(line_ids))
            if wizard.post_move:
                move.action_post()
            output.append("Asiento creado: %s" % (move.display_name or move.name or move.id))

        output.append("")
        output.append("Detalle:")
        output.extend(result_lines[:300])
        wizard.result = "\n".join(output)

        return {
            "type": "ir.actions.act_window",
            "res_model": wizard._name,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
