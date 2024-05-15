# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductProductInherit(models.Model):
    _inherit = "product.product"

    is_pitchprint_design = fields.Boolean(
        string="PitchPrint Design",
        default=lambda self: self.pitchprint_design_id is not False,
        readonly=False,
        store=True,
    )
    pitchprint_design_id = fields.Many2one(
        "product.design",
        string="PitchPrint Design ID",
        ondelete="set null",
        compute="_compute_pitchprint_design_id",
        readonly=True,
        store=False,
    )
    variant_design_id = fields.Many2one(
        "product.design",
        string="PitchPrint Variant Design ID",
        help="Set to overwrite the design specified on product template",
        ondelete="set null",
    )

    @api.depends("product_tmpl_id.pitchprint_design_id", "variant_design_id")
    def _compute_pitchprint_design_id(self):
        res = False
        for record in self:
            if record.is_pitchprint_design:
                res = (
                    record.variant_design_id
                    or record.product_tmpl_id.pitchprint_design_id
                )
            record.pitchprint_design_id = res

    def get_product_image(self, design_id=False):
        # Get product image from PP design
        res = False
        if design_id:
            res = self.env["product.design"].search([("id", "=", design_id)]).image
        return res

    def write(self, vals):
        # When print design ID changes, update image
        design_id = vals.get("variant_design_id", False)
        if design_id:
            for product in self:
                vals["image_1920"] = product.get_product_image(design_id)
        return super().write(vals)
