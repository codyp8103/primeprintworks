# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplateInherit(models.Model):
    _inherit = "product.template"

    is_pitchprint_design = fields.Boolean(string="PitchPrint Design")
    pitchprint_design_id = fields.Many2one(
        "product.design", string="PitchPrint Design ID", ondelete="set null"
    )

    def get_product_image(self, design_id=False):
        # Get product image from PP design
        res = False
        if design_id:
            res = self.env["product.design"].search([("id", "=", design_id)]).image
        return res

    def write(self, vals):
        # When print design ID changes, update image
        design_id = vals.get("pitchprint_design_id", False)
        if design_id:
            for product in self:
                vals["image_1920"] = product.get_product_image(design_id)
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            design_id = vals.get("pitchprint_design_id", False)
            if design_id:
                vals["image_1920"] = self.get_product_image(design_id)
        return super().create(vals_list)
