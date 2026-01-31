from odoo import models, fields, api
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

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()

        for order in self:
            # If the SO is linked to a CRM Lead
            lead = order.opportunity_id

            # 1️⃣ Close last CRM "Quotation Sent" tracking entry
            if lead:
                open_track = self.env['department.time.tracking'].search([
                    ('target_model', '=', f'crm.lead,{lead.id}'),
                    ('status', '=', 'in_progress')
                ], limit=1)

                if open_track:
                    open_track.write({
                        'end_time': fields.Datetime.now(),
                        'status': 'done'
                    })

            # 2️⃣ Create NEW tracking for Sale Order Confirmation
            self.env['department.time.tracking'].create({
                'target_model': f'sale.order,{order.id}',
                'stage_name': 'Sale Order Confirmed',
                'user_id': self.env.user.id,
                'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'start_time': fields.Datetime.now(),
                'status': 'in_progress',
                'lead_id': lead.id if lead else False,
            })

        return res