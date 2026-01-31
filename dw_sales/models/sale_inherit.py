from odoo import models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_quotation_send(self):
        """Override: when sending quotation by email, update CRM lead stage"""
        res = super(SaleOrder, self).action_quotation_send()

        for order in self:
            lead = order.opportunity_id
            if lead:
                stage_analysis_done = self.env.ref('dw_crm.stage_analysis_done')
                stage_quotation_sent = self.env.ref('dw_crm.stage_quotation_sent')
                if lead.stage_id.id == stage_analysis_done.id:
                    lead.stage_id = stage_quotation_sent.id

        return res
