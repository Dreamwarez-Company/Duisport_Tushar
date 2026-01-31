from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    is_journal_voucher = fields.Boolean(default=False)

    # voucher_type_id = fields.Selection(
    #     [('receipt','Receipt'), ('payment','Payment'), ('contra','Contra')],
    #     string='Default Type'
    # )
    voucher_type = fields.Selection(
        [
            ('receipt', 'Receipt'),
            ('payment', 'Payment'),
            ('contra', 'Contra')
        ],
        string='Default Type'
    )
    memo = fields.Text(string="Memo")

    mode = fields.Selection(
        [('cash','Cash'), ('bank','Bank'), ('cheque','Cheque')],
        string='Mode'
    )

    is_cheque = fields.Boolean(string='Is Cheque')
    cheque_ref = fields.Char(string='Cheque Ref')

    salesperson_id = fields.Many2one(
        'res.users',
        string='Salesperson'
    )

    sales_team_id = fields.Many2one(
        'crm.team',
        string='Sales Team'
    )

    salesperson_ids = fields.Many2many(
        'res.users',
        string='Salesperson(s)'
    )

    form_status = fields.Selection(
        [('draft','Draft'), ('other','Other')],
        string='Form Status',
        default='draft'
    )

    @api.model
    def create(self, vals):
        if self.env.context.get('default_is_journal_voucher'):
            vals['is_journal_voucher'] = True
        return super().create(vals)
