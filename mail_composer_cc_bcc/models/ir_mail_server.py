# Copyright 2024 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from .mail_thread import format_emails

class IrMailServer(models.Model):
    _inherit = 'ir.mail_server'

    def build_email(self, email_from, email_to, subject, body, email_cc=None, email_bcc=None, reply_to=False,
                        attachments=None, message_id=None, references=None, object_id=False, subtype='plain', headers=None,
                        body_alternative=None, subtype_alternative='plain'):
            context = self.env.context

            res = super().build_email(email_from, email_to, subject, body, email_cc=email_cc, email_bcc=email_bcc, reply_to=reply_to,
                        attachments=attachments, message_id=message_id, references=references, object_id=object_id, subtype=subtype, headers=headers,
                        body_alternative=body_alternative, subtype_alternative=subtype_alternative)
            
            if context.get('partner_bcc_ids'):
                  res['Bcc'] = format_emails(context.get('partner_bcc_ids'))
            
            return res