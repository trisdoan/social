# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    # FIXME: not working
    def _get_message_create_valid_field_names(self):
        """
        add cc and bcc field to create record in mail.mail
        """
        field_names = super()._get_message_create_valid_field_names()
        field_names.update({"partner_cc_ids", "partner_bcc_ids"})
        return field_names
