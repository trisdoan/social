from odoo import models


class Users(models.Model):
    _inherit = "res.users"

    def _init_messaging(self):
        res = super()._init_messaging()
        res["failed_counter"] = self.env["mail.message"].get_failed_count()
        return res
