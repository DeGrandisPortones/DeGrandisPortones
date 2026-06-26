import json
from odoo import models


class AccountGeneralLedgerNoCarryForwardHandler(models.AbstractModel):
    _name = 'account.general.ledger.no.carryforward.handler'
    _inherit = 'account.general.ledger.report.handler'
    _description = 'Mayor General Sin Arrastre'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        lines = list(super()._dynamic_lines_generator(
            report, options, all_column_groups_expression_totals, warnings=warnings,
        ))

        # Buscar metodos del padre que tengan "balance" en el nombre
        parent_cls = type(self).__mro__[1]
        balance_methods = sorted(
            m for m in dir(parent_cls)
            if 'balance' in m.lower() and not m.startswith('__')
        )

        # Capturar estructura de las primeras 15 lineas para diagnostico
        debug = {
            'total_lines': len(lines),
            'balance_methods_in_parent': balance_methods,
            'first_item_type': str(type(lines[0])) if lines else 'empty',
            'lines': [
                {
                    'id': str(line.get('id', '') if isinstance(line, dict) else line),
                    'name': str((line.get('name', '') if isinstance(line, dict) else '')[:80]),
                    'level': line.get('level') if isinstance(line, dict) else None,
                    'class': line.get('class', '') if isinstance(line, dict) else '',
                    'parent_id': str(line.get('parent_id', '') if isinstance(line, dict) else ''),
                    'ncols': len(line.get('columns') or []) if isinstance(line, dict) else 0,
                    'col_keys': list(((line.get('columns') or [{}])[0]).keys()) if isinstance(line, dict) and line.get('columns') else [],
                    'all_cols': [str(c) for c in (line.get('columns') or [])] if isinstance(line, dict) else [],
                }
                for line in lines[:15]
            ],
        }

        self.env['ir.config_parameter'].sudo().set_param(
            'dg_mayor_sin_arrastre.debug',
            json.dumps(debug, ensure_ascii=False, default=str)[:15000],
        )

        return iter(lines)
