from odoo import fields, models, tools


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    dg_client_sales_report_group = fields.Selection(
        selection=[
            ("fca", "Subtotal FCA"),
            ("internas", "Subtotal Internas"),
        ],
        string="Grupo reporte clientes",
        help=(
            "Usar para clasificar saldos iniciales o ajustes manuales en el reporte "
            "de clientes. Si se deja vacio, el reporte clasifica por diario."
        ),
        copy=False,
    )


class DgClientSalesReportLine(models.Model):
    _name = "dg.client.sales.report.line"
    _description = "Reporte de Clientes por Diario"
    _auto = False
    _order = "partner_id, report_group, invoice_date, move_id"

    partner_id = fields.Many2one("res.partner", string="Cliente", readonly=True)
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
            ("out_invoice", "Factura de cliente"),
            ("out_refund", "Nota de credito de cliente"),
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
                SELECT
                    am.id AS id,
                    COALESCE(rp.commercial_partner_id, am.partner_id) AS partner_id,
                    CASE
                        -- Odoo 18 stores translatable journal names as JSON/JSONB; compare extracted text values only.
                        WHEN ajn.journal_name = 'Diario Ventas Preimpreso' THEN 'fca'
                        WHEN ajn.journal_name = 'Diario Ventas Internas' THEN 'internas'
                    END AS report_group,
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
                    am.amount_untaxed_signed AS amount_untaxed_signed,
                    am.amount_tax_signed AS amount_tax_signed,
                    am.amount_total_signed AS amount_total_signed,
                    am.amount_residual_signed AS amount_residual_signed
                FROM account_move am
                JOIN account_journal aj ON aj.id = am.journal_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(
                        aj.name->>'es_AR',
                        aj.name->>'es_ES',
                        aj.name->>'es_419',
                        aj.name->>'en_US',
                        (
                            SELECT journal_name_any.value
                            FROM jsonb_each_text(aj.name) AS journal_name_any(lang, value)
                            LIMIT 1
                        )
                    ) AS journal_name
                ) ajn ON TRUE
                JOIN res_company company ON company.id = am.company_id
                LEFT JOIN res_partner rp ON rp.id = am.partner_id
                WHERE am.state = 'posted'
                    AND am.move_type IN ('out_invoice', 'out_refund')
                    AND aj.type = 'sale'
                    AND ajn.journal_name IN ('Diario Ventas Preimpreso', 'Diario Ventas Internas')

                UNION ALL

                SELECT
                    1000000000 + aml.id AS id,
                    COALESCE(rp.commercial_partner_id, aml.partner_id) AS partner_id,
                    COALESCE(
                        aml.dg_client_sales_report_group,
                        CASE
                            WHEN ajn.journal_name = 'Saldos Iniciales FCA' THEN 'fca'
                            WHEN ajn.journal_name = 'Saldos Iniciales Internas' THEN 'internas'
                        END
                    ) AS report_group,
                    'opening_balance'::varchar AS source_type,
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
                    aml.balance AS amount_total_signed,
                    aml.amount_residual AS amount_residual_signed
                FROM account_move_line aml
                JOIN account_move am ON am.id = aml.move_id
                JOIN account_journal aj ON aj.id = am.journal_id
                LEFT JOIN LATERAL (
                    SELECT COALESCE(
                        aj.name->>'es_AR',
                        aj.name->>'es_ES',
                        aj.name->>'es_419',
                        aj.name->>'en_US',
                        (
                            SELECT journal_name_any.value
                            FROM jsonb_each_text(aj.name) AS journal_name_any(lang, value)
                            LIMIT 1
                        )
                    ) AS journal_name
                ) ajn ON TRUE
                JOIN account_account aa ON aa.id = aml.account_id
                JOIN res_company company ON company.id = aml.company_id
                LEFT JOIN res_partner rp ON rp.id = aml.partner_id
                WHERE am.state = 'posted'
                    AND am.move_type = 'entry'
                    AND aa.account_type = 'asset_receivable'
                    AND aml.partner_id IS NOT NULL
                    AND (
                        aml.dg_client_sales_report_group IN ('fca', 'internas')
                        OR ajn.journal_name IN ('Saldos Iniciales FCA', 'Saldos Iniciales Internas')
                    )
                    AND (aml.balance != 0.0 OR aml.amount_residual != 0.0)
            )
            """
        )
