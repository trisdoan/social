# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


import itertools

from odoo import fields, models, tools


class MailTemplate(models.Model):
    _inherit = "mail.template"

    email_bcc = fields.Char(
        "Bcc", help="Blind cc recipients (placeholders may be used here)"
    )

    # ------------------------------------------------------------
    # MESSAGE/EMAIL VALUES GENERATION
    # ------------------------------------------------------------
    def _generate_template_recipients(
        self, res_ids, render_fields, find_or_create_partners=False, render_results=None
    ):
        self.ensure_one()
        if render_results is None:
            render_results = {}
        ModelSudo = self.env[self.model].with_prefetch(res_ids).sudo()

        # if using default recipients -> ``_message_get_default_recipients`` gives
        # values for email_to, email_cc and partner_ids
        if self.use_default_to and self.model:
            default_recipients = ModelSudo.browse(
                res_ids
            )._message_get_default_recipients()
            for res_id, recipients in default_recipients.items():
                render_results.setdefault(res_id, {}).update(recipients)
        # render fields dynamically which generates recipients
        else:
            for field in set(render_fields) & {
                "email_cc",
                "email_to",
                "partner_to",
                "email_bcc",
            }:
                generated_field_values = self._render_field(field, res_ids)
                for res_id in res_ids:
                    render_results.setdefault(res_id, {})[
                        field
                    ] = generated_field_values[res_id]


        if find_or_create_partners:
            self._create_partners_from_emails(ModelSudo, res_ids, render_results)

         # update 'partner_to' rendered value to 'partner_ids'
        self._update_partner_ids_from_partner_to(render_results)

        self._update_partner_ids_from_email_fields(
            render_results, "email_cc", "partner_cc_ids"
        )
        self._update_partner_ids_from_email_fields(
            render_results, "email_bcc", "partner_bcc_ids"
        )

        return render_results
    
    def _create_partners_from_emails(self, ModelSudo, res_ids, render_results):
        res_id_to_company = {}
        if self.model and "company_id" in ModelSudo._fields:
            for rec in ModelSudo.browse(res_ids).read(["company_id"]):
                company_id = (
                    rec["company_id"][0] if rec["company_id"] else False
                )
                res_id_to_company[rec["id"]] = company_id

        all_emails = []
        email_to_res_ids = {}
        email_to_company = {}
        for res_id in res_ids:
            record_values = render_results.setdefault(res_id, {})
            if record_values.get("email_cc"):
                continue
            mails = tools.email_split(record_values.pop("email_to", ""))
            all_emails += mails
            record_company = res_id_to_company.get(res_id)
            for mail in mails:
                email_to_res_ids.setdefault(mail, []).append(res_id)
                if record_company:
                    email_to_company[mail] = record_company

        if all_emails:
            customers_information = ModelSudo.browse(
                res_ids
            )._get_customer_information()
            partners = self.env["res.partner"]._find_or_create_from_emails(
                all_emails,
                additional_values={
                    email: {
                        "company_id": email_to_company.get(email),
                        **customers_information.get(email, {}),
                    }
                    for email in itertools.chain(all_emails, [False])
                },
            )
            for original_email, partner in zip(all_emails, partners, strict=False):
                if not partner:
                    continue
                for res_id in email_to_res_ids[original_email]:
                    render_results[res_id].setdefault("partner_ids", []).append(
                        partner.id
                    )

    def _update_partner_ids_from_partner_to(self, render_results):
        all_partner_to = {
            pid
            for record_values in render_results.values()
            for pid in self._parse_partner_to(record_values.get("partner_to", ""))
        }
        existing_pids = set()
        if all_partner_to:
            existing_pids = set(
                self.env["res.partner"].sudo().browse(list(all_partner_to)).exists().ids
            )
        for _, record_values in render_results.items():
            partner_to = record_values.pop("partner_to", "")
            if partner_to:
                tpl_partner_ids = (
                    set(self._parse_partner_to(partner_to)) & existing_pids
                )
                record_values.setdefault("partner_ids", []).extend(tpl_partner_ids)

    def _update_partner_ids_from_email_fields(
        self, render_results, email_field, partner_field
    ):
        ModelSudo = self.env[self.model].sudo()
        all_emails = set()
        email_to_res_ids = {}
        for res_id, record_values in render_results.items():
            emails = tools.email_split(record_values.pop(email_field, ""))
            for email in emails:
                all_emails.add(email)
                email_to_res_ids.setdefault(email, []).append(res_id)

        if not all_emails:
            return

        customers_information = ModelSudo.browse(
            list(render_results.keys())
        )._get_customer_information()
        partners = self.env["res.partner"]._find_or_create_from_emails(
            list(all_emails),
            additional_values={
                email: {
                    **customers_information.get(email, {}),
                }
                for email in all_emails
            },
        )

        for email, partner in zip(all_emails, partners, strict=False):
            if not partner:
                continue
            for res_id in email_to_res_ids[email]:
                render_results[res_id].setdefault(partner_field, []).append(partner.id)

    def _generate_template(self, res_ids, render_fields, find_or_create_partners=False):
        res = super()._generate_template(
            res_ids, render_fields, find_or_create_partners=find_or_create_partners
        )

        for _lang, (template, template_res_ids) in self._classify_per_lang(
            res_ids
        ).items():
            if "email_bcc" in render_fields:
                template._generate_template_recipients(
                    template_res_ids,
                    set("email_bcc"),
                    render_results=res,
                    find_or_create_partners=find_or_create_partners,
                )
        return res
