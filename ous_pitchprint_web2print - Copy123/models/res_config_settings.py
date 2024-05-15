# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pp_api_key = fields.Char(
        "PitchPrint API Key", config_parameter="ous_pitchprint_web2print.api_key"
    )
    pp_secret_key = fields.Char(
        "PitchPrint Secret Key", config_parameter="ous_pitchprint_web2print.secret_key"
    )
    pp_mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Confirmation Email Template",
        domain="[('model', '=', 'sale.order')]",
        config_parameter="ous_pitchprint_web2print.default_confirmation_template",
        help="Email to send when sale order confirmed with a custom design.",
    )
    require_login_checkout = fields.Boolean(
        "Require Login To Checkout",
        config_parameter="ous_pitchprint_web2print.login_checkout",
    )

    def fetch_pitchprint_data(self):
        self.env["product.design"].fetch_designs(user_mode=True)
