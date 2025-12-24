# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class DistributorApiController(http.Controller):
    """
    API para app de distribuidores.

    Endpoints expuestos (todos pensados para usarse via JS desde un front externo):
      - GET  /distributor/api/pickings
      - POST /distributor/api/pickings/<id>/final_customer
      - GET  /distributor/api/distributors
      - GET  /distributor/api/products
      - POST /distributor/api/quotations

    Todas las respuestas son JSON del tipo {"data": ...} o {"error": "..."}.
    """

    # -------------------------------------------------------------------------
    # Utilidades internas (CORS / JSON helpers)
    # -------------------------------------------------------------------------

    def _cors_headers(self):
        """Construye los headers CORS que se reutilizan en todas las respuestas."""
        origin = request.httprequest.headers.get("Origin") or "*"
        return [
            ("Access-Control-Allow-Origin", origin),
            ("Access-Control-Allow-Credentials", "true"),
            ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            (
                "Access-Control-Allow-Headers",
                "Origin, Content-Type, Accept, Authorization",
            ),
        ]

    def _json_default(self, obj):
        """Soporte para serializar datetime.date/datetime en JSON."""
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    def _json_response(self, payload, status=200):
        """Devuelve una respuesta JSON con CORS."""
        body = json.dumps(payload, default=self._json_default, ensure_ascii=False)
        headers = [("Content-Type", "application/json; charset=utf-8")]
        headers += self._cors_headers()
        response = request.make_response(body, headers)
        response.status_code = status
        return response

    def _handle_preflight(self):
        """Responde OK para las solicitudes OPTIONS (preflight CORS)."""
        if request.httprequest.method == "OPTIONS":
            return self._json_response({"ok": True}, status=200)
        return None

    # -------------------------------------------------------------------------
    # Helpers de negocio
    # -------------------------------------------------------------------------

    def _get_distributor_tag(self):
        """Etiqueta 'Distribuidor' en contactos."""
        Category = request.env["res.partner.category"].sudo()
        return Category.search([("name", "=", "Distribuidor")], limit=1)

    def _get_vip_pricelist(self):
        """
        Devuelve la lista de precios 'Lista Vip'.

        NO filtramos por compañía para evitar problemas de nombre de empresa.
        Se toma la primera que coincida por nombre.
        """
        Pricelist = request.env["product.pricelist"].sudo()
        return Pricelist.search([("name", "=", "Lista Vip")], limit=1)

    def _get_distributor_from_request(self, env, **kwargs):
        """Detecta el distribuidor para el request.

        Implementación flexible:
          1) Param/querystring distributor_id
          2) Header X-Distributor-Id
          3) Usuario logueado (partner_id) si NO es el public_user

        Además valida que el partner tenga la etiqueta 'Distribuidor' (si existe).
        """
        Partner = env["res.partner"].sudo()

        distributor_id = (
            kwargs.get("distributor_id")
            or request.httprequest.args.get("distributor_id")
            or request.httprequest.headers.get("X-Distributor-Id")
        )

        distributor = False
        if distributor_id:
            try:
                distributor = Partner.browse(int(distributor_id))
                if not distributor.exists():
                    distributor = False
            except Exception:
                distributor = False

        if not distributor:
            public_user = env.ref("base.public_user", raise_if_not_found=False)
            if not public_user or env.user.id != public_user.id:
                distributor = env.user.partner_id.sudo() if env.user.partner_id else False

        if not distributor:
            return False

        # Validación opcional: que sea distribuidor por etiqueta
        distributor_tag = self._get_distributor_tag()
        if distributor_tag and distributor_tag.id not in distributor.category_id.ids:
            return False

        return distributor

    # -------------------------------------------------------------------------
    # Listado de entregas (pickings)  [REEMPLAZADO]
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        cors="*",
    )
    def list_pickings(self, **kwargs):
        """Listado de entregas para el distribuidor.

        Devuelve TODOS los pickings pendientes (states: assigned / confirmed / waiting)
        para el distribuidor detectado, y marca si están listos para retirar.
        """
        env = request.env

        # Usa tu lógica actual para obtener el distribuidor
        # (según cabecera, token, usuario portal, etc.)
        distributor = self._get_distributor_from_request(env, **kwargs)
        if not distributor:
            return self._json_response(
                {
                    "error": "no_distributor",
                    "message": "Distribuidor no identificado.",
                },
                status=400,
            )

        # Dominio: todos los OUT pickings del distribuidor, pendientes de operación
        domain = [
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "in", ["assigned", "confirmed", "waiting"]),
            ("company_id", "=", distributor.company_id.id or env.user.company_id.id),
            # si en tu implementación original filtrabas de otra forma por partner,
            # podés ajustar esta línea:
            ("partner_id", "child_of", distributor.id),
        ]

        pickings = (
            env["stock.picking"]
            .sudo()
            .search(domain, order="scheduled_date asc, id asc")
        )

        data = []
        for picking in pickings:
            # ===== Cálculo de estado "listo para retirar" =====
            # Por ahora: listo si el picking está en 'assigned' y
            # no tiene movimientos esperando fabricación.
            ready_to_pick = picking.state == "assigned"
            ready_label = _("En stock") if ready_to_pick else _("Pendiente")

            # Si tenés lógica adicional de fabricación, la podés injertar aquí
            # sin tocar el dominio ni filtrar pickings por este flag.

            # ===== Líneas =====
            lines = []
            for move in picking.move_ids_without_package:
                lines.append(
                    {
                        "id": move.id,
                        "product_id": move.product_id.id,
                        "product_name": move.product_id.display_name,
                        "quantity": move.product_uom_qty,
                        "uom": move.product_uom.name,
                    }
                )

            # ===== Cliente final =====
            final_customer = getattr(picking, "x_final_customer_id", False)
            final_customer_completed = bool(final_customer)
            final_customer_name = final_customer.name if final_customer else False

            data.append(
                {
                    "id": picking.id,
                    "name": picking.name,
                    "origin": picking.origin,
                    "partner_name": picking.partner_id.display_name,
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
    # Guardar datos del cliente final en el picking
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/pickings/<int:picking_id>/final_customer",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def set_final_customer(self, picking_id, **kwargs):
        """
        Actualiza los campos de cliente final del picking
        (nombre, dirección, contacto, etc.) y marca final_customer_completed.
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        StockPicking = request.env["stock.picking"].sudo()

        picking = StockPicking.browse(picking_id)
        if not picking.exists():
            return self._json_response({"error": "Picking no encontrado"}, status=404)

        # Leer JSON del body
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
    # Listado de distribuidores (contactos)
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/distributors",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_distributors(self, **kwargs):
        """
        Devuelve los contactos marcados como 'Distribuidor'.

        Criterios:
          - active = True
          - categoría (etiqueta) 'Distribuidor'
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        Partner = env["res.partner"].sudo()

        distributor_tag = self._get_distributor_tag()
        if not distributor_tag:
            _logger.warning(
                "No existe la etiqueta 'Distribuidor' para listar distribuidores"
            )
            return self._json_response({"data": []})

        domain = [
            ("active", "=", True),
            ("category_id", "in", distributor_tag.ids),
        ]

        partners = Partner.search(domain, order="name asc")

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
    # Productos de la lista de precios VIP
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/products",
        type="http",
        auth="public",
        methods=["GET", "OPTIONS"],
        csrf=False,
    )
    def list_products(self, **kwargs):
        """
        Devuelve SOLO los productos que tienen precio explícito
        en la lista de precios 'Lista Vip'.

        Para cada producto se envía:
          - id
          - name
          - default_code
          - uom_name
          - list_price  (precio de la lista VIP)
        """
        preflight = self._handle_preflight()
        if preflight:
            return preflight

        env = request.env
        PricelistItem = env["product.pricelist.item"].sudo()
        ProductProduct = env["product.product"].sudo()

        pricelist = self._get_vip_pricelist()
        if not pricelist:
            _logger.warning("No se encontró la lista de precios 'Lista Vip'")
            return self._json_response({"data": []})

        # Ítems de tarifa que aplican a productos concretos
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
            # Línea a nivel de variante
            if item.product_id:
                prod = item.product_id
                product_ids.add(prod.id)
                price = (
                    item.fixed_price
                    if item.fixed_price not in (False, None)
                    else prod.list_price
                )
                price_by_product[prod.id] = float(price or 0.0)
            # Línea a nivel de plantilla: se aplica a todas las variantes
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
    # Crear presupuesto (sale.order) para un distribuidor
    # -------------------------------------------------------------------------

    @http.route(
        "/distributor/api/quotations",
        type="http",
        auth="public",
        methods=["POST", "OPTIONS"],
        csrf=False,
    )
    def create_quotation(self, **kwargs):
        """Crear un presupuesto (sale.order) en Odoo a partir de la app.

        Body JSON esperado:
        {
            "distributor_id": 123,
            "customer": {
                "name": "...",
                "phone": "...",
                "email": "...",
                "street": "...",
                "city": "..."
            },
            "notes": "...",
            "lines": [
                {"product_id": 1, "quantity": 3},
                ...
            ]
        }
        """
        # Preflight CORS
        preflight = self._handle_preflight()
        if preflight is not None:
            return preflight

        try:
            # Leer JSON del body
            raw = request.httprequest.data or b"{}"
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8") or "{}"
            payload = json.loads(raw or "{}")

            distributor_id = payload.get("distributor_id")
            customer = payload.get("customer") or {}
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

            # Contexto de empresa Vert Deco Cercos
            Company = request.env["res.company"].sudo()
            company = Company.search([("name", "=", "Vert Deco Cercos")], limit=1)
            if not company:
                # fallback a empresa actual
                company = request.env.company

            Partner = request.env["res.partner"].with_company(company).sudo()
            Pricelist = request.env["product.pricelist"].with_company(company).sudo()
            PricelistItem = (
                request.env["product.pricelist.item"].with_company(company).sudo()
            )
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

            # Buscar lista de precios VIP
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

            # Armar nota interna con datos del cliente final
            note_lines = []
            name = (customer.get("name") or "").strip()
            if name:
                note_lines.append(f"Cliente final: {name}")
            phone = (customer.get("phone") or "").strip()
            if phone:
                note_lines.append(f"Teléfono cliente final: {phone}")
            email = (customer.get("email") or "").strip()
            if email:
                note_lines.append(f"Email cliente final: {email}")
            street = (customer.get("street") or "").strip()
            city = (customer.get("city") or "").strip()
            if street or city:
                direccion = " - ".join(filter(None, [street, city]))
                note_lines.append(f"Dirección cliente final: {direccion}")
            if notes:
                note_lines.append("")
                note_lines.append("Notas del distribuidor:")
                note_lines.append(notes)
            internal_note = "\n".join(note_lines) if note_lines else False

            order_lines = []

            for line in lines:
                product_id = line.get("product_id")
                qty = float(line.get("quantity") or 0.0)

                if not product_id or qty <= 0:
                    continue

                product = Product.browse(int(product_id))
                if not product.exists():
                    continue

                # Buscar precio de la lista VIP para este producto
                price = product.list_price

                # Intentar encontrar una regla específica en la lista VIP
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
                    # Usamos el precio fijo si está definido, si no, fallback al precio de lista del producto
                    price = item.fixed_price or price

                order_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty": qty,
                            "price_unit": price,
                        },
                    )
                )

            if not order_lines:
                return self._json_response(
                    {
                        "error": "no_valid_lines",
                        "message": "No se pudo generar ninguna línea de pedido (verificar productos y cantidades).",
                    },
                    status=400,
                )

            order_vals = {
                "partner_id": distributor.id,
                "company_id": company.id,
                "pricelist_id": vip_pricelist.id,
                "note": internal_note,
                # El cliente final no se crea como contacto separado por simplicidad.
            }

            order = SaleOrder.create({**order_vals, "order_line": order_lines})

            return self._json_response(
                {
                    "success": True,
                    "order_id": order.id,
                    "name": order.name,
                },
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
