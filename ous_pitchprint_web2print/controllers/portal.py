# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class RepeatOrderController(http.Controller):
    @http.route("/orders/repeat", type="http", auth="user", website=True, csrf=False)
    def repeat_order(self, **kwargs):
        # Repeat sale order by duplicating items into the cart
        add_qty = 0
        set_qty = 0
        order_id = kwargs.get("id")
        repeat_order_id = request.env["sale.order"].sudo().browse(int(order_id))
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != "draft":
            request.session["sale_order_id"] = None
            sale_order = request.website.sale_get_order(force_create=True)
        for old_line in repeat_order_id.order_line:
            if old_line.product_id and old_line.product_id.detailed_type != "service":
                add_qty = old_line.product_uom_qty
                set_qty = add_qty
                # Add line to cart
                sale_order.web2print_cart_update(
                    pitchprint_project_id=old_line.pitchprint_project_id,
                    product_id=old_line.product_id.id,
                    add_qty=add_qty,
                    set_qty=set_qty,
                    **kwargs,
                )
        return request.redirect("/shop/cart")
