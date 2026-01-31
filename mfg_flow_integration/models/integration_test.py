from odoo import models, fields

class IntegrationTestWizard(models.TransientModel):
    _name = "integration.test.wizard"
    _description = "End-to-End Flow Tester"

    def action_run_test(self):
        partner = self.env['res.partner'].search([], limit=1)
        product = self.env['product.product'].search([('bom_ids', '!=', False)], limit=1)
        if not partner or not product:
            return {'type': 'ir.actions.act_window_close'}

        sale_order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': product.list_price,
            })]
        })
        sale_order.action_confirm()
        return {'type': 'ir.actions.act_window_close'}
