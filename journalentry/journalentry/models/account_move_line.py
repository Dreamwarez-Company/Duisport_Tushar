from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    dr_cr = fields.Selection([
        ('debit', 'Debit'),
        ('credit', 'Credit')
    ], string='Dr/Cr', default='debit')
    
    amount = fields.Float(string='Amount')
    
    @api.onchange('amount', 'dr_cr')
    def _onchange_amount_dr_cr(self):
        for line in self:
            if line.dr_cr == 'debit':
                line.debit = line.amount
                line.credit = 0.0
            else:
                line.debit = 0.0
                line.credit = line.amount
    
    @api.onchange('debit')
    def _onchange_debit(self):
        for line in self:
            if line.debit > 0:
                line.amount = line.debit
                line.dr_cr = 'debit'
    
    @api.onchange('credit')
    def _onchange_credit(self):
        for line in self:
            if line.credit > 0:
                line.amount = line.credit
                line.dr_cr = 'credit'


# from odoo import models, fields, api

# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'
    
#     amount = fields.Monetary(
#         string='Amount',
#         currency_field='currency_id',
#         compute='_compute_amount',
#         inverse='_inverse_amount',
#         store=True
#     )
    
#     dr_cr = fields.Selection(
#         [('dr', 'Dr'), ('cr', 'Cr')],
#         string='Dr/Cr',
#         default='dr'
#     )
    
#     @api.depends('debit', 'credit')
#     def _compute_amount(self):
#         for line in self:
#             if line.debit > 0:
#                 line.amount = line.debit
#                 line.dr_cr = 'dr'
#             elif line.credit > 0:
#                 line.amount = line.credit
#                 line.dr_cr = 'cr'
#             else:
#                 line.amount = 0.0
#                 line.dr_cr = 'dr'
    
#     def _inverse_amount(self):
#         for line in self:
#             if line.dr_cr == 'dr':
#                 line.debit = line.amount or 0.0
#                 line.credit = 0.0
#             else:
#                 line.credit = line.amount or 0.0
#                 line.debit = 0.0
    
#     @api.onchange('amount', 'dr_cr')
#     def _onchange_amount_drcr(self):
#         self._inverse_amount()