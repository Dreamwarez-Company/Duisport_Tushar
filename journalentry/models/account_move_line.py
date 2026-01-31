from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id'
    )

    dr_cr = fields.Selection(
        [('dr', 'Dr'), ('cr', 'Cr')],
        string='Dr / Cr'
    )

    @api.onchange('amount', 'dr_cr')
    def _onchange_amount_drcr(self):
        for line in self:
            if not line.amount or not line.dr_cr:
                continue

            if line.dr_cr == 'dr':
                line.debit = line.amount
                line.credit = 0.0
            else:
                line.credit = line.amount
                line.debit = 0.0
