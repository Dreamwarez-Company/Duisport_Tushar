from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    is_journal_voucher = fields.Boolean(default=False)
    voucher_type = fields.Selection(
        [('receipt', 'Receipt'), ('payment', 'Payment'), ('contra', 'Contra')],
        string='Default Type'
    )
    mode = fields.Selection(
        [('cash', 'Cash'), ('bank', 'Bank'), ('cheque', 'Cheque')],
        string='Mode'
    )
    form_status = fields.Selection(
        [('draft', 'Draft'), ('other', 'Other')],
        string='Form Status',
        default='draft'
    )
    is_cheque = fields.Boolean(string='Is Cheque')
    cheque_ref = fields.Char(string='Cheque Ref')
    salesperson_id = fields.Many2one('res.users', string='Salesperson')
    sales_team_id = fields.Many2one('crm.team', string='Sales Team')
    salesperson_ids = fields.Many2many('res.users', string='Salesperson(s)')
    
    # Custom memo field with selection/dropdown
    memo_selection = fields.Selection(
        selection='_get_memo_selection',
        string='Memo',
        help='Select memo from suggestions'
    )
    
    # Keep original narration field
    narration = fields.Text(string='Custom Memo')
    
    def _get_memo_selection(self):
        """Return memo suggestions"""
        return [
            ('CASH RT.NO.6579 TOWARDS A/C', 'CASH RT.NO.6579 TOWARDS A/C'),
            ('BANK TRANSFER FOR SUPPLIES', 'BANK TRANSFER FOR SUPPLIES'),
            ('CASH WITHDRAWAL FOR EXPENSES', 'CASH WITHDRAWAL FOR EXPENSES'),
            ('CONTRA ENTRY FOR BANK TRANSFER', 'CONTRA ENTRY FOR BANK TRANSFER'),
            ('SALARY PAYMENT FOR DECEMBER', 'SALARY PAYMENT FOR DECEMBER'),
            ('OTHER', 'Other (Enter custom memo)'),
        ]
    
    @api.onchange('memo_selection')
    def _onchange_memo_selection(self):
        """When memo is selected from dropdown, update narration"""
        if self.memo_selection and self.memo_selection != 'OTHER':
            self.narration = self.memo_selection
    
    @api.model
    def create(self, vals):
        if self.env.context.get('default_is_journal_voucher'):
            vals['is_journal_voucher'] = True
        return super().create(vals)



# from odoo import models, fields, api

# class AccountMove(models.Model):
#     _inherit = 'account.move'
    
#     is_journal_voucher = fields.Boolean(default=False)
#     voucher_type = fields.Selection(
#         [
#             ('receipt', 'Receipt'),
#             ('payment', 'Payment'),
#             ('contra', 'Contra'),
#             ('journal', 'Journal')
#         ],
#         string='Default Type',
#         default='receipt'
#     )
#     mode = fields.Selection(
#         [
#             ('cash', 'Cash'),
#             ('bank', 'Bank'),
#             ('cheque', 'Cheque'),
#             ('other', 'Other')
#         ],
#         string='Mode',
#         default='cash'
#     )
#     is_cheque = fields.Boolean(string='Is Cheque')
#     cheque_ref = fields.Char(string='Cheque Ref')
#     form_status = fields.Selection(
#         [
#             ('draft', 'Draft'),
#             ('submitted', 'Submitted'),
#             ('approved', 'Approved'),
#             ('rejected', 'Rejected'),
#             ('other', 'Other')
#         ],
#         string='Form Status',
#         default='draft'
#     )
#     salesperson_id = fields.Many2one('res.users', string='Salesperson')
#     sales_team_id = fields.Many2one('crm.team', string='Sales Team')
#     salesperson_ids = fields.Many2many('res.users', string='Salesperson(s)')
    
#     @api.model
#     def create(self, vals):
#         if self.env.context.get('default_is_journal_voucher'):
#             vals['is_journal_voucher'] = True
#             # Set default journal for journal vouchers
#             if 'journal_id' not in vals:
#                 journal = self.env['account.journal'].search([
#                     ('type', '=', 'general'),
#                     ('company_id', '=', self.env.company.id)
#                 ], limit=1)
#                 if journal:
#                     vals['journal_id'] = journal.id
#         return super().create(vals)