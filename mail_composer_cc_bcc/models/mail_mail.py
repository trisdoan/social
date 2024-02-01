# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models, tools


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    # ------------------------------------------------------
    # mail_mail formatting, tools and send mechanism
    # ------------------------------------------------------

    def _prepare_outgoing_list(self, recipients_follower_status=None):
        """
        This method is override to do 2 tasks
            - Add Bcc recipients to the list of recipients.
            - If the email is being sent from the composer, then only send one email.

        """
        res = super()._prepare_outgoing_list(
            recipients_follower_status=recipients_follower_status
        )
        is_out_of_scope = len(self.ids) > 1
        is_from_composer = self.env.context.get("is_from_composer", False)

        if is_out_of_scope or not is_from_composer:
            return res

        one_email = res[0]
        if self.mail_message_id.partner_ids:
            partner = self.mail_message_id.partner_ids[0]
            email_to = tools.email_normalize(partner.email)
            if email_to:
                email_to_formatted = tools.formataddr((partner.name or "", email_to))
            else:
                email_to_formatted = tools.formataddr(
                    (partner.name or "", partner.email or "False")
                )
            one_email.update(
                {
                    "email_to": [email_to_formatted],
                    "email_to_raw": partner.email or "",
                    "partner_id": partner,
                }
            )
        elif self.email_to:
            one_email.update(
                {
                    "email_to": tools.email_split_and_format(self.email_to),
                    "email_to_raw": self.email_to or "",
                    "partner_id": False,
                }
            )

        if self.email_cc:
            one_email.update({"email_cc": tools.email_split(self.email_cc)})
        else:
            one_email.update({"email_cc": []})

        if self.email_bcc:
            one_email.update({"email_bcc": tools.email_split(self.email_bcc)})
        else:
            one_email.update({"email_bcc": []})
        res = [one_email]
        return res
