# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CollectionRegisterWizard(models.TransientModel):
    _name = "collection.register.wizard"
    _description = "Collection Register Report Wizard"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    partner_ids = fields.Many2many(
        "res.partner",
        string="Customers",
        domain=[("customer_rank", ">", 0)]
    )
    payment_ids = fields.Many2many(
        "account.payment",
        string="Payment Records",
        compute="_compute_payment_ids",
        store=False
    )
   
    @api.depends('date_from', 'date_to', 'partner_ids')
    def _compute_payment_ids(self):
        for rec in self:
            rec.payment_ids = False

            if not rec.date_from or not rec.date_to:
                continue

            domain = [
                ('payment_type', '=', 'inbound'),
                ('state', '=', 'posted'),
                ('move_id.date', '>=', rec.date_from),
                ('move_id.date', '<=', rec.date_to),
            ]

            if rec.partner_ids:
                domain.append(('partner_id', 'in', rec.partner_ids.ids))

            payments = self.env['account.payment'].search(domain)
            rec.payment_ids = payments.sorted(lambda p: p.move_id.date)   
    
    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_view_payments(self):
        self._compute_payment_ids()
        return self._reopen()

    def action_print_collection_register(self):
        """Generates the PDF report using Odoo’s report action."""
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'partner_ids': self.partner_ids.ids,
        }
        return self.env.ref(
            "all_reports_full.collection_register_pdf_report_action"
        ).report_action(self, data=data)


class CollectionRegisterReport(models.AbstractModel):
    _name = "report.all_reports_full.collection_register_template"
    _description = "Collection Register QWeb Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get("date_from")
        date_to = data.get("date_to")
        partner_ids = data.get("partner_ids")

        # Domain for inbound payments (collections)
        domain = [
            ('payment_type', '=', 'inbound'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ]

        if partner_ids:
            domain.append(('partner_id', 'in', partner_ids))

        payments = self.env['account.payment'].search(domain, order="date")

        return {
            'doc_ids': docids,
            'doc_model': "collection.register.wizard",
            'data': data,
            'payments': payments,
            'date_from': date_from,
            'date_to': date_to,
        }



#  parent="menu_hr_payroll_community_root"