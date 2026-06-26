from odoo import fields, models, tools


class AccountAccount(models.Model):
    _inherit = "account.account"

    dg_supplier_report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo reporte proveedores",
        help=(
            "Clasifica los movimientos de cuentas a pagar en el reporte de proveedores. "
            "Configurar en las cuentas contables de proveedores (ej: 2.1.1.01.010 = FCA, "
            "6.2.1.01.010 = Internas)."
        ),
        copy=False,
    )


class AccountJournal(models.Model):
    _inherit = "account.journal"

    dg_supplier_report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo reporte proveedores",
        help=(
            "Clasifica los movimientos de este diario en el reporte de proveedores. "
            "Si se deja vacio, el reporte clasifica por cuenta contable o nombre del diario."
        ),
        copy=False,
    )


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    dg_supplier_report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo reporte proveedores",
        help=(
            "Usar para clasificar saldos iniciales, ajustes manuales o pagos/debitos "
            "sin imputar en el reporte de proveedores. Si se deja vacio, el reporte "
            "clasifica por cuenta contable, diario o la factura conciliada cuando sea posible."
        ),
        copy=False,
    )


class DgSupplierReportLine(models.Model):
    _name = "dg.supplier.report.line"
    _description = "Reporte de Proveedores por Diario"
    _auto = False
    _order = "partner_id, report_group, invoice_date, move_id"

    partner_id = fields.Many2one("res.partner", string="Proveedor", readonly=True)
    report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo",
        readonly=True,
    )
    source_type = fields.Selection(
        selection=[
            ("invoice", "Factura / NC"),
            ("opening_balance", "Saldo inicial / ajuste"),
            ("payment_debit", "Pago / debito sin aplicar"),
        ],
        string="Origen del saldo",
        readonly=True,
    )
    move_id = fields.Many2one("account.move", string="Comprobante", readonly=True)
    line_id = fields.Many2one("account.move.line", string="Apunte contable", readonly=True)
    move_name = fields.Char(string="Numero", readonly=True)
    ref = fields.Char(string="Referencia", readonly=True)
    invoice_origin = fields.Char(string="Origen", readonly=True)
    invoice_date = fields.Date(string="Fecha de factura", readonly=True)
    accounting_date = fields.Date(string="Fecha contable", readonly=True)
    invoice_date_due = fields.Date(string="Fecha de vencimiento", readonly=True)
    journal_id = fields.Many2one("account.journal", string="Diario", readonly=True)
    company_id = fields.Many2one("res.company", string="Compania", readonly=True)
    company_currency_id = fields.Many2one("res.currency", string="Moneda compania", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Moneda factura", readonly=True)
    move_type = fields.Selection(
        selection=[
            ("in_invoice", "Factura de proveedor"),
            ("in_refund", "Nota de credito de proveedor"),
            ("entry", "Asiento contable"),
        ],
        string="Tipo",
        readonly=True,
    )
    payment_state = fields.Selection(
        selection=[
            ("not_paid", "No pagado"),
            ("in_payment", "En pago"),
            ("paid", "Pagado"),
            ("partial", "Parcial"),
            ("reversed", "Revertido"),
            ("invoicing_legacy", "Sistema anterior"),
        ],
        string="Estado de pago",
        readonly=True,
    )
    amount_untaxed_signed = fields.Monetary(
        string="Base imponible",
        currency_field="company_currency_id",
        readonly=True,
        group_operator="sum",
    )
    amount_tax_signed = fields.Monetary(
        string="Impuestos",
        currency_field="company_currency_id",
        readonly=True,
        group_operator="sum",
    )
    amount_total_signed = fields.Monetary(
        string="Total",
        currency_field="company_currency_id",
        readonly=True,
        group_operator="sum",
    )
    amount_residual_signed = fields.Monetary(
        string="Saldo",
        currency_field="company_currency_id",
        readonly=True,
        group_operator="sum",
    )

    def action_open_move(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.move_id.display_name,
            "res_model": "account.move",
            "res_id": self.move_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                WITH invoice_moves AS (
                    SELECT
                        am.id AS id,
                        COALESCE(rp.commercial_partner_id, am.partner_id) AS partner_id,
                        COALESCE(
                            aj.dg_supplier_report_group,
                            payable_acct.dg_supplier_report_group,
                            CASE
                                WHEN ajn.normalized_journal_name IN ('compras preimpreso', 'diario compras preimpreso') THEN 'fca'
                                WHEN ajn.normalized_journal_name IN ('compras internas', 'diario compras internas') THEN 'internas'
                            END
                        ) AS report_group,
                        'invoice'::varchar AS source_type,
                        am.id AS move_id,
                        NULL::integer AS line_id,
                        am.name AS move_name,
                        am.ref AS ref,
                        am.invoice_origin AS invoice_origin,
                        am.invoice_date AS invoice_date,
                        am.date AS accounting_date,
                        am.invoice_date_due AS invoice_date_due,
                        am.journal_id AS journal_id,
                        am.company_id AS company_id,
                        company.currency_id AS company_currency_id,
                        am.currency_id AS currency_id,
                        am.move_type AS move_type,
                        am.payment_state AS payment_state,
                        -am.amount_untaxed_signed AS amount_untaxed_signed,
                        -am.amount_tax_signed AS amount_tax_signed,
                        -am.amount_total_signed AS amount_total_signed,
                        -am.amount_residual_signed AS amount_residual_signed
                    FROM account_move am
                    JOIN account_journal aj ON aj.id = am.journal_id
                    LEFT JOIN LATERAL (
                        SELECT
                            LOWER(TRIM(COALESCE(
                                aj.name->>'es_AR',
                                aj.name->>'es_ES',
                                aj.name->>'es_419',
                                aj.name->>'en_US',
                                (
                                    SELECT journal_name_any.value
                                    FROM jsonb_each_text(aj.name) AS journal_name_any(lang, value)
                                    LIMIT 1
                                )
                            ))) AS normalized_journal_name
                    ) ajn ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT aa2.dg_supplier_report_group
                        FROM account_move_line aml2
                        JOIN account_account aa2 ON aa2.id = aml2.account_id
                        WHERE aml2.move_id = am.id
                            AND aa2.dg_supplier_report_group IS NOT NULL
                        LIMIT 1
                    ) payable_acct ON TRUE
                    JOIN res_company company ON company.id = am.company_id
                    LEFT JOIN res_partner rp ON rp.id = am.partner_id
                    WHERE am.state = 'posted'
                        AND am.move_type IN ('in_invoice', 'in_refund')
                        AND aj.type = 'purchase'
                        AND ABS(am.amount_residual_signed) > 0.004
                ),
                payable_entry_lines AS (
                    SELECT
                        1000000000 + aml.id AS id,
                        COALESCE(rp.commercial_partner_id, aml.partner_id) AS partner_id,
                        COALESCE(
                            aml.dg_supplier_report_group,
                            inferred_group.report_group,
                            aj.dg_supplier_report_group,
                            aa.dg_supplier_report_group,
                            CASE
                                WHEN ajn.normalized_journal_name IN ('saldos iniciales proveedores fca', 'compras preimpreso', 'diario compras preimpreso') THEN 'fca'
                                WHEN ajn.normalized_journal_name IN ('saldos iniciales proveedores internas', 'compras internas', 'diario compras internas') THEN 'internas'
                            END
                        ) AS report_group,
                        CASE
                            WHEN aml.payment_id IS NOT NULL THEN 'payment_debit'::varchar
                            ELSE 'opening_balance'::varchar
                        END AS source_type,
                        am.id AS move_id,
                        aml.id AS line_id,
                        am.name AS move_name,
                        COALESCE(aml.ref, am.ref) AS ref,
                        am.invoice_origin AS invoice_origin,
                        COALESCE(am.invoice_date, am.date) AS invoice_date,
                        aml.date AS accounting_date,
                        aml.date_maturity AS invoice_date_due,
                        am.journal_id AS journal_id,
                        aml.company_id AS company_id,
                        company.currency_id AS company_currency_id,
                        COALESCE(aml.currency_id, company.currency_id) AS currency_id,
                        am.move_type AS move_type,
                        am.payment_state AS payment_state,
                        0.0 AS amount_untaxed_signed,
                        0.0 AS amount_tax_signed,
                        -aml.balance AS amount_total_signed,
                        -aml.amount_residual AS amount_residual_signed
                    FROM account_move_line aml
                    JOIN account_move am ON am.id = aml.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    LEFT JOIN LATERAL (
                        SELECT
                            LOWER(TRIM(COALESCE(
                                aj.name->>'es_AR',
                                aj.name->>'es_ES',
                                aj.name->>'es_419',
                                aj.name->>'en_US',
                                (
                                    SELECT journal_name_any.value
                                    FROM jsonb_each_text(aj.name) AS journal_name_any(lang, value)
                                    LIMIT 1
                                )
                            ))) AS normalized_journal_name
                    ) ajn ON TRUE
                    LEFT JOIN LATERAL (
                        SELECT
                            CASE
                                WHEN COUNT(DISTINCT matched_groups.report_group) = 1 THEN MIN(matched_groups.report_group)
                                ELSE NULL
                            END AS report_group
                        FROM (
                            SELECT DISTINCT
                                COALESCE(
                                    counterpart_journal.dg_supplier_report_group,
                                    counterpart_aa.dg_supplier_report_group,
                                    CASE
                                        WHEN counterpart_journal_names.normalized_journal_name IN ('compras preimpreso', 'diario compras preimpreso') THEN 'fca'
                                        WHEN counterpart_journal_names.normalized_journal_name IN ('compras internas', 'diario compras internas') THEN 'internas'
                                    END
                                ) AS report_group
                            FROM account_partial_reconcile apr
                            JOIN account_move_line counterpart_line
                                ON counterpart_line.id = CASE
                                    WHEN apr.debit_move_id = aml.id THEN apr.credit_move_id
                                    ELSE apr.debit_move_id
                                END
                            JOIN account_move counterpart_move ON counterpart_move.id = counterpart_line.move_id
                            JOIN account_journal counterpart_journal ON counterpart_journal.id = counterpart_move.journal_id
                            JOIN account_account counterpart_aa ON counterpart_aa.id = counterpart_line.account_id
                            LEFT JOIN LATERAL (
                                SELECT
                                    LOWER(TRIM(COALESCE(
                                        counterpart_journal.name->>'es_AR',
                                        counterpart_journal.name->>'es_ES',
                                        counterpart_journal.name->>'es_419',
                                        counterpart_journal.name->>'en_US',
                                        (
                                            SELECT counterpart_journal_name_any.value
                                            FROM jsonb_each_text(counterpart_journal.name) AS counterpart_journal_name_any(lang, value)
                                            LIMIT 1
                                        )
                                    ))) AS normalized_journal_name
                            ) counterpart_journal_names ON TRUE
                            WHERE (apr.debit_move_id = aml.id OR apr.credit_move_id = aml.id)
                                AND counterpart_move.move_type IN ('in_invoice', 'in_refund')
                        ) matched_groups
                        WHERE matched_groups.report_group IS NOT NULL
                    ) inferred_group ON TRUE
                    JOIN account_account aa ON aa.id = aml.account_id
                    JOIN res_company company ON company.id = aml.company_id
                    LEFT JOIN res_partner rp ON rp.id = aml.partner_id
                    WHERE am.state = 'posted'
                        AND am.move_type = 'entry'
                        AND aa.account_type = 'liability_payable'
                        AND aml.partner_id IS NOT NULL
                        AND ABS(aml.amount_residual) > 0.004
                )
                SELECT *
                FROM invoice_moves
                WHERE report_group IN ('fca', 'internas')

                UNION ALL

                SELECT *
                FROM payable_entry_lines
                WHERE report_group IN ('fca', 'internas')
            )
            """
        )
