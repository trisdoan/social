# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.tests import tagged

from odoo.addons.account.tests.test_account_move_send import TestAccountMoveSendCommon
from odoo.addons.mail.tests.common import MailCommon


@tagged("post_install_l10n", "post_install", "-at_install")
class TestMailCcBccInvoice(TestAccountMoveSendCommon, MailCommon):
    def test_invoice_mail_cc_bcc(self):
        invoice = self.init_invoice("out_invoice", amounts=[1000], post=True)
        wizard = self.create_send_and_print(
            invoice, sending_methods=["email", "manual"]
        )
        wizard.partner_cc_ids = self.partner_b
        with self.mock_mail_gateway():
            wizard.action_send_and_print()

        message = self._get_mail_message(invoice)
        self.assertTrue(message)

        # FIXME: return 2 email
        self.assertEqual(len(message.mail_ids), 1)

        # Only 2 partners (from default_cc/bcc of company) notified
        self.assertEqual(len(message.notified_partner_ids), 2)
        self.assertEqual(len(message.notification_ids), 2)
