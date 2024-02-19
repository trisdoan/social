# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo import fields, models, tools

from odoo.addons.base.models.ir_mail_server import extract_rfc2822_addresses


def format_emails(partners):
    emails = [tools.formataddr((p.name or "", p.email)) for p in partners if p.email]
    return ", ".join(emails)


class MailMail(models.Model):
    _inherit = "mail.mail"

    email_bcc = fields.Char("Bcc", help="Blind Cc message recipients")

    def _prepare_outgoing_list(self, recipients_follower_status=None):
        # First, return if we're not coming from the Mail Composer
        res = super()._prepare_outgoing_list(
            recipients_follower_status=recipients_follower_status
        )
        is_out_of_scope = len(self.ids) > 1
        is_from_composer = self.env.context.get("is_from_composer", False)

        if is_out_of_scope or not is_from_composer:
            return res

        # Prepare values for To, Cc, Bcc headers
        partners_cc_bcc = self.recipient_cc_ids + self.recipient_bcc_ids
        partner_to_ids = [r.id for r in self.recipient_ids if r not in partners_cc_bcc]
        partner_to = self.env["res.partner"].browse(partner_to_ids)
        email_to = format_emails(partner_to)
        email_cc = format_emails(self.recipient_cc_ids)
        email_bcc = format_emails(self.recipient_bcc_ids)

        # Collect recipients (RCPT TO) and update all emails
        # with the same To, Cc, Bcc headers
        # (to be shown by email client as users expect)
        recipients = []
        for m in res:
            rcpt_to = None
            if m["email_to"]:
                rcpt_to = extract_rfc2822_addresses(m["email_to"][0])[0]
            # in the absence of self.email_to, Odoo creates one special mail for CC
            # see https://github.com/odoo/odoo/commit/46bad8f0
            elif m["email_cc"]:
                rcpt_to = extract_rfc2822_addresses(m["email_cc"][0])[0]
            if rcpt_to:
                recipients.append(rcpt_to)

            m.update(
                {
                    "email_to": email_to,
                    "email_to_raw": email_to,
                    "email_cc": email_cc,
                    # mail server removes it when not relevant
                    "email_bcc": email_bcc,
                }
            )

        self.env.context = {**self.env.context, "recipients": recipients}
        return res
