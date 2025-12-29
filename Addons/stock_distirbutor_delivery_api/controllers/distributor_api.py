# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class DistributorApiController(http.Controller):
    # -------------------------------------------------------------------------
    # Utilidades internas (CORS / JSON helpers)
    # -------------------------------------------------------------------------

    def _cors_headers(self):
        origin = request.httprequest.headers.get("Origin") or "*"
        return [
            ("Access-Control-Allow-Origin", origin),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            (
                "Access-Control-Allow-Headers",
                "Origin, Content-Type, Accept, Authorization, X-Distributor-Id",
            ),
        ]

    def _json_default(self, obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    def _json_response(self, payload, status=200):
        body = json.dumps(payload, default=self._json_default, ensure_ascii=False)
        headers = [("Content-Type", "application/json; charset=utf-8")]
        headers += self._cors_headers()
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    def _handle_preflight(self):
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)
        return None

    # -------------------------------------------------------------------------
    # Helpers: header obligatorio + resolución de etiqueta
    # -------------------------------------------------------------------------

    def _get_request_odoo_distributor_id_required(self):
        """Header obligatorio. Devuelve int o lanza error 403."""
        raw = request.httprequest.headers.get("X-Distributor-Id")
        if not raw:
            return None

        try:
            val = int(str(raw).strip())
            if val <= 0:
                return None
            return val
        except Exception:
            return None

    def _get_distributor_tag_required(self):
        """Resuelve la etiqueta a partir del X-Distributor-Id (obligatorio).

        Regla:
          - 1 => 'Distribuidor'
          - N => 'DistribuidorN' (ej: 2 -> Distribuidor2)
        """
        odoo_distributor_id = self._get_request_odoo_distributor_id_required()
        if not odoo_distributor_id:
            return None, self._json_response(
                {
                    "error": "forbidden",
                    "message": "Falta header X-Distributor-Id o es inválido.",
                },
                status=403,
            )

        Category = request.env["res.partner.category"].sudo()

        if odoo_distributor_id == 1:
            tag_name = "Distribuidor"
            tag = Category.search([("name", "=", tag_name)], limit=1)
        else:
            # Nombre exacto pedido: Distribuidor2, Distribuidor3, etc.
            tag_name = f"Distribuidor{odoo_distributor_id}"
            tag = Category.search([("name", "=", tag_name)], limit=1)
            if not tag:
                # tolerancia: "Distribuidor 2"
                tag = Category.search([("name", "=", f"Distribuidor {odoo_distributor_id}")], limit=1)

        if not tag:
            return None, self._json_response(
                {
                    "error": "forbidden",
                    "message": f"No existe la etiqueta requerida: {tag_name}",
                },
                status=403,
            )

        return tag, None

    def _get_vip_pricelist(self):
        Pricelist = request.env["product.pricelist"].sudo()
        return Pricelist.search([("name", "=", "Lista Vip")], limit=1)

    # -------------------------------------------------------------------------
    # GET /distributor/api/pickings
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_pickings(self, **kwargs):
        preflight = self._handle_preflight()
        if preflight is not None:
            return preflight

        distributor_tag, err = self._get_distributor_tag_required()
        if err:
            return err

        StockPicking = request.env["stock.picking"].sudo()

        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "not in", ["done", "cancel"]),
            ("state", "in", ["assigned", "confirmed", "waiting"]),
            ("partner_id.category_id", "in", distributor_tag.ids),
        ]

        pickings = StockPicking.search(domain, order="scheduled_date asc, id asc")

        data = []
        for picking in pickings:
            ready_to_pick = picking.state == "assigned"
            ready_label = _("En stock") if ready_to_pick else _("Pendiente")

            lines = []
            for move in picking.move_ids_without_package:
                product = move.product_id
                if not product:
                    continue
                qty = move.product_uom_qty
                if qty <= 0:
                    continue

                lines.append(
                    {
                        "id": move.id,
                        "product_id": product.id,
                        "product_name": product.display_name,
                        "quantity": qty,
                        "uom": move.product_uom.name or "",
                    }
                )

            final_customer = getattr(picking, "x_final_customer_id", False)
            final_customer_completed = bool(final_customer)
            final_customer_name = final_customer.name if final_customer else False

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin or "",
                    "partner_name": picking.partner_id.display_name or "",
                    "scheduled_date": fields.Datetime.to_string(picking.scheduled_date)
                    if picking.scheduled_date
                    else False,
                    "state": picking.state,
                    "ready_to_pick": ready_to_pick,
                    "ready_label": ready_label,
                    "final_customer_completed": final_customer_completed,
                    "final_customer_name": final_customer_name,
                    "lines": lines,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # POST /distributor/api/pickings/<id>/final_customer
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        distributor_tag, err = self._get_distributor_tag_required()
        if err:
            return err

        StockPicking = request.env["stock.picking"].sudo()
        picking = StockPicking.browse(picking_id)
        if not picking.exists():
            return self._json_response({"error": "Picking no encontrado"}, status=404)

        # Validación: el picking debe pertenecer a esa etiqueta
        if distributor_tag not in picking.partner_id.category_id:
            return self._json_response(
                {
                    "error": "forbidden",
                    "message": "No tiene permisos para modificar este picking.",
                },
                status=403,
            )

        try:
            raw = request.httprequest.data or b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except Exception as exc:
            _logger.exception("Error parseando JSON de final_customer: %s", exc)
            return self._json_response(
                {"error": "JSON inválido en el cuerpo de la petición"}, status=400
            )

        vals = {
            "final_customer_name": payload.get("name"),
            "final_customer_street": payload.get("street"),
            "final_customer_city": payload.get("city"),
            "final_customer_vat": payload.get("vat"),
            "final_customer_phone": payload.get("phone"),
            "final_customer_email": payload.get("email"),
            "final_customer_notes": payload.get("notes"),
            "final_customer_completed": True,
        }

        picking.write(vals)
        return self._json_response({"data": {"id": picking.id, "updated": True}})

    # -------------------------------------------------------------------------
    # GET /distributor/api/distributors
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_distributors(self, **kwargs):
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        distributor_tag, err = self._get_distributor_tag_required()
        if err:
            return err

        Partner = request.env["res.partner"].sudo()

        partners = Partner.search(
            [
                ("active", "=", True),
                ("category_id", "in", distributor_tag.ids),
            ],
            order="name asc",
        )

        data = []
        for partner in partners:
            data.append(
                {
                    "id": partner.id,
                    "name": partner.name,
                    "vat": partner.vat or "",
                    "street": partner.street or "",
                    "city": partner.city or "",
                    "phone": partner.phone or "",
                    "email": partner.email or "",
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # GET /distributor/api/products
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        # Header obligatorio también acá (mantiene consistencia de seguridad)
        distributor_tag, err = self._get_distributor_tag_required()
        if err:
            return err

        PricelistItem = request.env["product.pricelist.item"].sudo()
        ProductProduct = request.env["product.product"].sudo()

        pricelist = self._get_vip_pricelist()
        if not pricelist:
            _logger.warning("No se encontró la lista de precios 'Lista Vip'")
            return self._json_response({"data": []})

        items = PricelistItem.search(
            [
                ("pricelist_id", "=", pricelist.id),
                ("applied_on", "in", ["0_product_variant", "1_product"]),
            ]
        )

        if not items:
            return self._json_response({"data": []})

        product_ids = set()
        price_by_product = {}

        for item in items:
            if item.product_id:
                prod = item.product_id
                product_ids.add(prod.id)
                price = (
                    item.fixed_price
                    if item.fixed_price not in (False, None)
                    else prod.list_price
                )
                price_by_product[prod.id] = float(price or 0.0)
            elif item.product_tmpl_id:
                for prod in item.product_tmpl_id.product_variant_ids:
                    product_ids.add(prod.id)
                    price = (
                        item.fixed_price
                        if item.fixed_price not in (False, None)
                        else prod.list_price
                    )
                    price_by_product[prod.id] = float(price or 0.0)

        if not product_ids:
            return self._json_response({"data": []})

        products = ProductProduct.search(
            [
                ("id", "in", list(product_ids)),
                ("sale_ok", "=", True),
            ],
            order="name asc",
        )

        data = []
        for product in products:
            price = price_by_product.get(product.id, float(product.list_price or 0.0))
            data.append(
                {
                    "id": product.id,
                    "name": product.display_name,
                    "default_code": product.default_code or "",
                    "uom_name": product.uom_id.name or "",
                    "list_price": price,
                }
            )

        return self._json_response({"data": data})

    # -------------------------------------------------------------------------
    # POST /distributor/api/quotations
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        preflight = self._handle_preflight()
        if preflight is not None:
            return preflight

        distributor_tag, err = self._get_distributor_tag_required()
        if err:
            return err

        try:
            raw = request.httprequest.data or b"{}"
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8") or "{}"
            payload = json.loads(raw or "{}")

            distributor_id = payload.get("distributor_id")
            lines = payload.get("lines") or []
            notes = payload.get("notes") or ""

            if not distributor_id:
                return self._json_response(
                    {
                        "error": "missing_distributor",
                        "message": "Debe indicar el distribuidor (distributor_id).",
                    },
                    status=400,
                )

            if not lines:
                return self._json_response(
                    {
                        "error": "no_lines",
                        "message": "Debe enviar al menos una línea de producto.",
                    },
                    status=400,
                )

            Company = request.env["res.company"].sudo()
            company = Company.search([("name", "=", "Vert Deco Cercos")], limit=1)
            if not company:
                company = request.env.company

            Partner = request.env["res.partner"].with_company(company).sudo()
            Pricelist = request.env["product.pricelist"].with_company(company).sudo()
            PricelistItem = request.env["product.pricelist.item"].with_company(company).sudo()
            Product = request.env["product.product"].with_company(company).sudo()
            SaleOrder = request.env["sale.order"].with_company(company).sudo()

            distributor = Partner.browse(int(distributor_id))
            if not distributor.exists():
                return self._json_response(
                    {
                        "error": "invalid_distributor",
                        "message": "El distribuidor indicado no existe.",
                    },
                    status=400,
                )

            # Validación: el distribuidor debe pertenecer a esa etiqueta
            if distributor_tag not in distributor.category_id:
                return self._json_response(
                    {
                        "error": "forbidden",
                        "message": "El distribuidor no pertenece a su etiqueta asignada.",
                    },
                    status=403,
                )

            vip_pricelist = Pricelist.search(
                [
                    ("name", "=", "Lista Vip"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )
            if not vip_pricelist:
                return self._json_response(
                    {
                        "error": "no_pricelist",
                        "message": "No se encontró la lista de precios 'Lista Vip' para la empresa Vert Deco Cercos.",
                    },
                    status=400,
                )

            internal_note = notes.strip() if notes else False

            order_lines = []
            for line in lines:
                product_id = line.get("product_id")
                qty = float(line.get("quantity") or 0.0)
                if not product_id or qty <= 0:
                    continue

                product = Product.browse(int(product_id))
                if not product.exists():
                    continue

                price = product.list_price
                item_domain = [
                    ("pricelist_id", "=", vip_pricelist.id),
                    ("company_id", "=", company.id),
                    ("applied_on", "in", ["0_product_variant", "1_product"]),
                    "|",
                    ("product_id", "=", product.id),
                    ("product_tmpl_id", "=", product.product_tmpl_id.id),
                ]
                item = PricelistItem.search(item_domain, limit=1)
                if item:
                    price = item.fixed_price or price

                order_lines.append(
                    (0, 0, {"product_id": product.id, "product_uom_qty": qty, "price_unit": price})
                )

            if not order_lines:
                return self._json_response(
                    {
                        "error": "no_valid_lines",
                        "message": "No se pudo generar ninguna línea de pedido (verificar productos y cantidades).",
                    },
                    status=400,
                )

            order = SaleOrder.create(
                {
                    "partner_id": distributor.id,
                    "company_id": company.id,
                    "pricelist_id": vip_pricelist.id,
                    "note": internal_note,
                    "order_line": order_lines,
                }
            )

            return self._json_response(
                {"success": True, "order_id": order.id, "name": order.name},
                status=200,
            )

        except Exception as e:
            _logger.exception("Error al crear la cotización desde la API de distribuidores")
            return self._json_response(
                {
                    "error": "internal_error",
                    "message": "Error interno al crear la cotización en Odoo.",
                    "detail": str(e),
                },
                status=500,
            )
