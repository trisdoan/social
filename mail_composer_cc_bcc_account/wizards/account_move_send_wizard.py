# Copyright 2024 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
#
from odoo import Command, api, fields, models
from odoo.tools.mail import email_split


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "account_move_send_wizard_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
        compute="_compute_mail_partner_cc_bcc_ids",
        store=True,
        readonly=False,
    )

    # -------------------------------------------------------------------------
    # DEFAULTS
    # -------------------------------------------------------------------------

    @api.model
    def default_get(self, fields_list):
        # EXTENDS 'base'
        results = super().default_get(fields_list)
        company = self.env.company
        partner_cc = company.default_partner_cc_ids
        if partner_cc:
            results["partner_cc_ids"] = [Command.set(partner_cc.ids)]
        partner_bcc = company.default_partner_bcc_ids
        if partner_bcc:
            results["partner_bcc_ids"] = [Command.set(partner_bcc.ids)]
        return results

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------
    def _get_partner_ids_from_mail(self, move, emails):
        partners = self.env["res.partner"].with_company(move.company_id)
        for mail_data in email_split(emails):
            partners |= partners.find_or_create(mail_data)
        return partners

    @api.depends("mail_template_id")
    def _compute_mail_partner_cc_bcc_ids(self):
        for wizard in self:
            if wizard.mail_template_id:
                wizard.partner_cc_ids = self._get_partner_ids_from_mail(
                    wizard.move_id, wizard.mail_template_id.email_cc
                )
                wizard.partner_bcc_ids = self._get_partner_ids_from_mail(
                    wizard.move_id, wizard.mail_template_id.email_bcc
                )
            else:
                wizard.partner_cc_ids = wizard.partner_bcc_ids = None

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        # Completely override Base to attach extra context to move
        partner_ids = kwargs.get("partner_ids", [])
        author_id = kwargs.pop("author_id")
        move_with_context = move.with_context(
            no_new_invoice=True,
            mail_notify_author=author_id in partner_ids,
            is_from_composer=True,
            partner_cc_ids=self.partner_cc_ids,
            partner_bcc_ids=self.partner_bcc_ids,
        )
        extra_args = {
            "email_layout_xmlid": "mail.mail_notification_layout_with_responsible_signature",  # noqa: E501
            "email_add_signature": not mail_template,
            "mail_auto_delete": mail_template.auto_delete,
            "mail_server_id": mail_template.mail_server_id.id,
            "reply_to_force_new": False,
        }
        kwargs.update(extra_args)
        new_message = move_with_context.message_post(**kwargs)

        # Prevent duplicated attachments linked to the invoice.
        new_message.attachment_ids.invalidate_recordset(
            ["res_id", "res_model"], flush=False
        )
        if new_message.attachment_ids.ids:
            self.env.cr.execute(
                "UPDATE ir_attachment SET res_id = NULL WHERE id IN %s",
                [tuple(new_message.attachment_ids.ids)],
            )
        new_message.attachment_ids.write(
            {
                "res_model": new_message._name,
                "res_id": new_message.id,
            }
        )
