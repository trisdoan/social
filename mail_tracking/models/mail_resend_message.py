# Copyright 2019 Alexandre Díaz
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, models


class MailResendMessage(models.TransientModel):
    _inherit = "mail.resend.message"

    @api.model
    def default_get(self, fields):
        rec = super().default_get(fields)
        message_id = self._context.get("mail_message_to_resend")
        if message_id:
            MailMessageObj = self.env["mail.message"]
            mail_message_id = MailMessageObj.browse(message_id)
            failed_states = MailMessageObj.get_failed_states()
            tracking_ids = mail_message_id.mail_tracking_ids.filtered(
                lambda x: x.state in failed_states
            )
            if any(tracking_ids):
                partner_values = []
                for tracking in tracking_ids:
                    notification_id = (
                        tracking.mail_message_id.notification_ids.filtered(
                            lambda x: x.res_partner_id == tracking.partner_id  # noqa: B023
                        )
                    )
                    partner_values.append(
                        {
                            "notification_id": notification_id.id,
                            "resend": True,
                            "message": tracking.error_description,
                        }
                    )
                if partner_values:
                    partner_ids = (
                        self.env["mail.resend.partner"].create(partner_values).ids
                    )
                    partner_commands = [
                        Command.link(partner_id) for partner_id in partner_ids
                    ]
                    rec["partner_ids"].extend(partner_commands)
        return rec

    def resend_mail_action(self):
        for wizard in self:
            to_send = wizard.partner_ids.filtered("resend").mapped("partner_id")
            if to_send:
                # Set as reviewed
                wizard.mail_message_id.mail_tracking_needs_action = False
                # Reset mail.tracking.email state
                tracking_ids = wizard.mail_message_id.mail_tracking_ids.filtered(
                    lambda x: x.partner_id in to_send  # noqa B023
                )
                tracking_ids.sudo().write({"state": False})
                # Send bus notifications to update Discuss and
                # mail_failed_messages widget
                self.env["bus.bus"]._sendone(
                    self.env.user.partner_id.id,
                    "toggle_tracking_status",
                    self.mail_message_id.id,
                )
        return super().resend_mail_action()
