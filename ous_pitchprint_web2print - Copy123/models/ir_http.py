# Copyright 2022 Open User Systems - Chris Mann
# See LICENSE file for full copyright and licensing details.
from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        modules = super()._get_translation_frontend_modules_name()
        return modules + ["ous_pitchprint_web2print"]
