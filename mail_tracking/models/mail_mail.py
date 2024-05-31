# Copyright 2016 Antonio Espinosa - <antonio.espinosa@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import time
from datetime import datetime
from email.utils import COMMASPACE

from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    def _tracking_email_prepare(self, partner, email):
        """Prepare email.tracking.email record values"""
        ts = time.time()
        dt = datetime.utcfromtimestamp(ts)
        email_to_list = email.get("email_to", [])
        email_to = COMMASPACE.join(email_to_list)
        return {
            "name": self.subject,
            "timestamp": "%.6f" % ts,
            "time": fields.Datetime.to_string(dt),
            "mail_id": self.id,
            "mail_message_id": self.mail_message_id.id,
            "partner_id": partner.id if partner else False,
            "recipient": email_to,
            "sender": self.email_from,
        }

    def _prepare_outgoing_list(self, recipients_follower_status=None):
        email_dicts = super()._prepare_outgoing_list(
            recipients_follower_status=recipients_follower_status
        )
        vals = []
        for email in email_dicts:
            sub_email = self._tracking_email_prepare(email.get("partner_id"), email)
            vals.append(sub_email)

        tracking_emails = self.env["mail.tracking.email"].sudo().create(vals)
        return tracking_emails.tracking_img_add(email_dicts)
