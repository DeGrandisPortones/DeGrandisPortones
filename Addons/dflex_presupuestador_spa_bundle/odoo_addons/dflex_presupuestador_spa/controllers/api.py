# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import AccessError


class PresupuestadorApiController(http.Controller):

    def _portal_domain(self):
        partner = request.env.user.partner_id
        return [("partner_id", "child_of", partner.id)]

    def _check_access_pedido(self, pedido):
        dom = self._portal_domain() + [("id", "=", pedido.id)]
        if not request.env["presupuestador.pedido"].sudo().search_count(dom):
            raise AccessError(_("No tiene permisos para acceder a este presupuesto."))

    @http.route("/api/presupuestador/session", type="json", auth="user", csrf=False)
    def session_info(self):
        website = request.website
        pricelist = website.pricelist_id
        user = request.env.user
        return {
            "user": {"id": user.id, "name": user.name},
            "partner": {"id": user.partner_id.id, "name": user.partner_id.display_name},
            "pricelist": {"id": pricelist.id if pricelist else False, "name": pricelist.name if pricelist else False},
            "currency": {
                "id": pricelist.currency_id.id if pricelist else user.company_id.currency_id.id,
                "name": (pricelist.currency_id.name if pricelist else user.company_id.currency_id.name),
                "symbol": (pricelist.currency_id.symbol if pricelist else user.company_id.currency_id.symbol),
            },
            "routes": {"app": "/presupuestador"},
        }

    @http.route("/api/presupuestador/rubros", type="json", auth="user", csrf=False)
    def rubros(self):
        rubros = request.env["presupuestador.rubro"].search([("active", "=", True)], order="sequence, name")
        return [{
            "id": r.id,
            "name": r.name,
            "qty_mode": r.qty_mode,
        } for r in rubros]

    @http.route("/api/presupuestador/productos", type="json", auth="user", csrf=False)
    def productos(self, rubro_id=None, q=None, limit=50):
        dom = [("sale_ok", "=", True)]
        if q:
            dom += [("name", "ilike", q)]
        if rubro_id:
            rubro = request.env["presupuestador.rubro"].browse(int(rubro_id))
            if rubro.product_category_id:
                dom += [("categ_id", "child_of", rubro.product_category_id.id)]
            if rubro.product_tag_ids:
                dom += [("product_tag_ids", "in", rubro.product_tag_ids.ids)]
        products = request.env["product.product"].search(dom, limit=min(int(limit), 200))
        return [{
            "id": p.id,
            "name": p.display_name,
            "uom": p.uom_id.name,
        } for p in products]

    @http.route("/api/presupuestador/pedidos", type="json", auth="user", csrf=False)
    def pedidos(self):
        pedidos = request.env["presupuestador.pedido"].search(self._portal_domain(), order="create_date desc", limit=200)
        return [{
            "id": p.id,
            "name": p.name,
            "state": p.state,
            "coeficiente": p.coeficiente,
            "m2": p.m2,
            "amount_total": p.amount_total,
            "currency_symbol": p.currency_id.symbol,
            "create_date": p.create_date.isoformat() if p.create_date else None,
        } for p in pedidos]

    @http.route("/api/presupuestador/pedidos/create", type="json", auth="user", csrf=False)
    def pedidos_create(self, coeficiente=25.0):
        website = request.website
        partner = request.env.user.partner_id
        pricelist = website.pricelist_id
        pedido = request.env["presupuestador.pedido"].create({
            "partner_id": partner.id,
            "pricelist_id": pricelist.id,
            "coeficiente": float(coeficiente or 0.0),
        })
        return {"id": pedido.id}

    @http.route("/api/presupuestador/pedidos/get", type="json", auth="user", csrf=False)
    def pedidos_get(self, pedido_id):
        pedido = request.env["presupuestador.pedido"].browse(int(pedido_id))
        if not pedido.exists():
            return {"error": "not_found"}
        self._check_access_pedido(pedido)
        return {
            "id": pedido.id,
            "name": pedido.name,
            "state": pedido.state,
            "coeficiente": pedido.coeficiente,
            "sistema": pedido.sistema,
            "ancho": pedido.ancho,
            "alto": pedido.alto,
            "peso_m2": pedido.peso_m2,
            "m2": pedido.m2,
            "peso_total": pedido.peso_total,
            "totals": {
                "untaxed": pedido.amount_untaxed,
                "tax": pedido.amount_tax,
                "total": pedido.amount_total,
                "currency_symbol": pedido.currency_id.symbol,
            },
            "lines": [{
                "id": l.id,
                "rubro": {"id": l.rubro_id.id, "name": l.rubro_id.name},
                "product": {"id": l.product_id.id, "name": l.product_id.display_name},
                "qty": l.qty,
                "precio_distr": l.precio_distr,
                "price_unit": l.price_unit,
                "price_total": l.price_total,
                "obs": l.obs,
            } for l in pedido.line_ids],
        }

    @http.route("/api/presupuestador/pedidos/update", type="json", auth="user", csrf=False)
    def pedidos_update(self, pedido_id, values):
        pedido = request.env["presupuestador.pedido"].browse(int(pedido_id))
        if not pedido.exists():
            return {"error": "not_found"}
        self._check_access_pedido(pedido)

        allowed = {"sistema", "ancho", "alto", "peso_m2", "coeficiente"}
        vals = {k: values[k] for k in values if k in allowed}
        # Cast numerics safely
        for f in ("ancho", "alto", "peso_m2", "coeficiente"):
            if f in vals:
                try:
                    vals[f] = float(vals[f] or 0.0)
                except Exception:
                    vals[f] = 0.0

        pedido.write(vals)
        if "coeficiente" in vals or "ancho" in vals or "alto" in vals:
            pedido.action_recompute_lines()
        return {"ok": True}

    @http.route("/api/presupuestador/lineas/add", type="json", auth="user", csrf=False)
    def lineas_add(self, pedido_id, rubro_id, product_id, qty=None, obs=None):
        pedido = request.env["presupuestador.pedido"].browse(int(pedido_id))
        if not pedido.exists():
            return {"error": "not_found"}
        self._check_access_pedido(pedido)

        rubro = request.env["presupuestador.rubro"].browse(int(rubro_id))
        product = request.env["product.product"].browse(int(product_id))

        if rubro.qty_mode == "m2":
            q = pedido.m2 or 0.0
        elif rubro.qty_mode == "one":
            q = 1.0
        else:
            q = float(qty or 1.0)

        line = request.env["presupuestador.linea"].create({
            "pedido_id": pedido.id,
            "rubro_id": rubro.id,
            "product_id": product.id,
            "qty": q,
            "obs": obs or False,
            "tax_ids": [(6, 0, product.taxes_id.filtered(lambda t: t.type_tax_use in ("sale", "none")).ids)],
        })
        return {"id": line.id}

    @http.route("/api/presupuestador/lineas/delete", type="json", auth="user", csrf=False)
    def lineas_delete(self, pedido_id, line_id):
        pedido = request.env["presupuestador.pedido"].browse(int(pedido_id))
        if not pedido.exists():
            return {"error": "not_found"}
        self._check_access_pedido(pedido)

        line = request.env["presupuestador.linea"].browse(int(line_id))
        if line.exists() and line.pedido_id.id == pedido.id:
            line.unlink()
        return {"ok": True}
