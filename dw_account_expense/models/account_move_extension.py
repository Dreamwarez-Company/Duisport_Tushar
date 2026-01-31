from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    x_expense_tag_id = fields.Many2one('expense.tag', string='Expense Tag')



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    x_expense_tag_id = fields.Many2one('expense.tag', string='Expense Tag')



class ExpenseTag(models.Model):
    _name = 'expense.tag'
    _description = 'Expense Tag'

    name = fields.Char('Tag Name', required=True)

    
        