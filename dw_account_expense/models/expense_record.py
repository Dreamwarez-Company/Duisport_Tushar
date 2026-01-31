from odoo import models, fields

class ExpenseRecord(models.Model):
    _name = 'expense.record'
    _description = 'Expense Record'

    name = fields.Char('Reference', required=True)
    amount = fields.Monetary('Amount', required=True)
    move_id = fields.Many2one('account.move', string='Related Journal Entry')
    payment_id = fields.Many2one('account.payment', string='Related Payment')
    expense_tag_id = fields.Many2one('expense.tag', string='Expense Tag')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
