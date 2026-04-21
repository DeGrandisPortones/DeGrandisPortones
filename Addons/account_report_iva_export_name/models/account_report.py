from odoo import models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def get_default_report_filename(self, options, *args, **kwargs):
        filename = super().get_default_report_filename(options, *args, **kwargs)
        self.ensure_one()

        if not self._is_ar_vat_book_report():
            return filename

        report_scope = self._get_iva_export_scope(options or {})
        if report_scope == 'sales':
            return 'Iva_Ventas'
        if report_scope == 'purchases':
            return 'Iva_Compras'
        if report_scope == 'both':
            return 'Iva_VentasCompras'
        return filename

    def _is_ar_vat_book_report(self):
        self.ensure_one()
        external_ids = list(self.get_external_id().values())
        names = [
            self.name,
            self.display_name,
            self.root_report_id.name if self.root_report_id else False,
            self.root_report_id.display_name if self.root_report_id else False,
            *external_ids,
        ]
        haystack = ' '.join(filter(None, names)).lower()
        return (
            'libro de iva argentino' in haystack
            or 'argentinian vat book' in haystack
            or 'declaracion fiscal' in haystack
            or 'declaración fiscal' in haystack
            or (
                ('argentin' in haystack or 'l10n_ar' in haystack)
                and ('iva' in haystack or 'vat' in haystack)
            )
        )

    def _get_iva_export_scope(self, options):
        sales = False
        purchases = False

        def mark_from_text(text):
            nonlocal sales, purchases
            low = (text or '').strip().lower()
            if not low:
                return
            if low in ('all', 'both', 'todos'):
                sales = True
                purchases = True
                return
            if 'venta' in low or low in ('sale', 'sales'):
                sales = True
            if 'compr' in low or low in ('purchase', 'purchases'):
                purchases = True

        def walk(value, parent_key=''):
            nonlocal sales, purchases

            if isinstance(value, dict):
                for key, item in value.items():
                    low_key = str(key).lower()
                    if isinstance(item, bool):
                        if low_key in ('sales', 'sale', 'ventas') and item:
                            sales = True
                        elif low_key in ('purchases', 'purchase', 'compras') and item:
                            purchases = True
                        elif low_key in ('both', 'all', 'todos') and item:
                            sales = True
                            purchases = True

                selected_keys = ('selected', 'is_selected', 'checked', 'active')
                has_selected_key = any(k in value for k in selected_keys)
                is_selected = any(bool(value.get(k)) for k in selected_keys)

                label_parts = []
                for field_name in ('id', 'name', 'label', 'display_name', 'string', 'value'):
                    field_value = value.get(field_name)
                    if isinstance(field_value, str):
                        label_parts.append(field_value)
                label_text = ' '.join(label_parts)

                if has_selected_key:
                    if is_selected:
                        mark_from_text(label_text)
                else:
                    low_parent = str(parent_key).lower()
                    if low_parent in (
                        'tax_type',
                        'tax_types',
                        'tax_scope',
                        'book_type',
                        'type_tax_use',
                        'filter_tax_type',
                    ):
                        mark_from_text(label_text)

                for key, item in value.items():
                    walk(item, key)
                return

            if isinstance(value, list):
                for item in value:
                    walk(item, parent_key)
                return

            if isinstance(value, str):
                low_parent = str(parent_key).lower()
                if low_parent in (
                    'tax_type',
                    'tax_types',
                    'tax_scope',
                    'book_type',
                    'type_tax_use',
                    'filter_tax_type',
                ):
                    mark_from_text(value)

        walk(options)

        if sales and purchases:
            return 'both'
        if sales:
            return 'sales'
        if purchases:
            return 'purchases'
        return False
