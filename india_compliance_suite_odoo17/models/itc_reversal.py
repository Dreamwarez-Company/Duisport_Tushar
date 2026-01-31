
from odoo import models, fields, api

class GstItcReversal(models.Model):
    _name = "gst.itc.reversal"
    _description = "GST ITC Reversal (Rule 42 & 43)"

    period_month = fields.Selection(
        [(str(i), str(i)) for i in range(1,13)], string="Month", required=True
    )
    period_year = fields.Integer(string="Year", required=True)

    total_itc = fields.Float()
    exempt_turnover = fields.Float()
    total_turnover = fields.Float()

    reversal_amount = fields.Float(compute="_compute_reversal", store=True)

    @api.depends("total_itc", "exempt_turnover", "total_turnover")
    def _compute_reversal(self):
        for rec in self:
            rec.reversal_amount = (
                (rec.exempt_turnover / rec.total_turnover) * rec.total_itc
                if rec.total_turnover else 0.0
            )
