from odoo import models, api, _
from odoo.exceptions import UserError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        order = super().create(vals)
        if self.env.user.has_group('purchase_restriction_store.group_store_department'):
            order.state = 'draft'
        return order

    # def button_confirm(self):
    #     if self.env.user.has_group('purchase_restriction_store.group_store_department'):
    #         raise UserError(_("You are not allowed to confirm RFQs. Please request the Purchase Department to confirm."))
    #     return super(PurchaseOrder, self).button_confirm()

    # def action_rfq_send(self):
    #     if self.env.user.has_group('purchase_restriction_store.group_store_department'):
    #         raise UserError(_("You are not allowed to send RFQs. Please request the Purchase Department to handle this action."))
    #     return super(PurchaseOrder, self).action_rfq_send()
