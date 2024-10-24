# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import api, models, tools


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _get_default_mail_partner_ids(self, move, mail_template, mail_lang):
        partners = super()._get_default_mail_partner_ids(move, mail_template, mail_lang)
        if mail_template.email_bcc:
            email_bcc = self._get_mail_default_field_value_from_template(
                mail_template, mail_lang, move, "email_bcc"
            )
            for mail_data in tools.email_split(email_bcc):
                partners |= partners.find_or_create(mail_data)
        return partners
