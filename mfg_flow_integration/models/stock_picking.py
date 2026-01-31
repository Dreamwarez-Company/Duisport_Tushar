from odoo import models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def action_print_challan(self):
        return self.env.ref('mfg_flow_integration.report_delivery_challan').report_action(self)
