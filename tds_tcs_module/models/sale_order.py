from odoo import models, api

class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.onchange('partner_id')
    def _onchange_partner_apply_customer_specific_tax(self):
        """When customer is selected, apply the customer-specific tax."""
        for order in self:
            customer_tax = order.partner_id.customer_specific_tax_id
            if customer_tax:
                for line in order.order_line:
                    if customer_tax not in line.tax_id:
                        line.tax_id = [(4, customer_tax.id)]





class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id')
    def _onchange_product_customer_tax(self):
        """When product is selected, apply customer-specific tax."""
        if self.order_id.partner_id.customer_specific_tax_id:
            tax = self.order_id.partner_id.customer_specific_tax_id
            if tax not in self.tax_id:
                self.tax_id = [(4, tax.id)]
