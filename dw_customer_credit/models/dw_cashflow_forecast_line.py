from odoo import fields, models

class DwCashflowForecastLine(models.Model):
    _name = 'dw.cashflow.forecast.line'
    _description = 'Cash Flow Forecast Line'

    forecast_id = fields.Many2one(
        'dw.cashflow.forecast',
        ondelete='cascade'
    )

    date = fields.Date()
    description = fields.Char()
    inflow = fields.Float()
    outflow = fields.Float()
