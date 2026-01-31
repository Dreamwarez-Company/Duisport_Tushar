from odoo import models, fields

class VoucherType(models.Model):
    _name = 'voucher.type'
    _description = 'Voucher Type'

    name = fields.Char(required=True)
    code = fields.Selection([
        ('receipt', 'Receipt'),
        ('payment', 'Payment'),
        ('contra', 'Contra'),
        ('journal', 'Journal'),
    ], required=True)

    active = fields.Boolean(default=True)
