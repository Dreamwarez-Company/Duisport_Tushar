from odoo import models, fields, api

class VendorCompareLine(models.TransientModel):
    _name = 'vendor.compare.line'
    _description = 'Vendor compare line (transient)'

    wizard_id = fields.Many2one('vendor.compare.wizard', string='Wizard')
    vendor_id = fields.Many2one('res.partner', string='Vendor')
    price = fields.Float(string='Price')
    min_qty = fields.Float(string='Min Qty')

class VendorCompareWizard(models.TransientModel):
    _name = 'vendor.compare.wizard'
    _description = 'Vendor Compare Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Quantity', default=1.0)
    line_ids = fields.One2many('vendor.compare.line', 'wizard_id', string='Vendors')

    def action_populate(self):
        self.line_ids.unlink()
        sellers = self.product_id.seller_ids.sorted(key=lambda s: s.price or 0.0)
        lines = []
        for s in sellers:
            lines.append((0, 0, {
                'vendor_id': s.name.id,
                'price': s.price or 0.0,
                'min_qty': s.min_qty or 0.0,
            }))
        self.line_ids = lines
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.compare.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_best(self):
        # choose the lowest price vendor (could be extended)
        if not self.line_ids:
            return {'type': 'ir.actions.act_window_close'}
        best = sorted(self.line_ids, key=lambda l: (l.price or 0.0, l.min_qty or 0.0))[0]
        # create a RFQ / PO using this vendor (example simple)
        po = self.env['purchase.order'].create({'partner_id': best.vendor_id.id})
        self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': self.product_id.id,
            'name': self.product_id.display_name,
            'product_uom_qty': self.qty,
            'product_uom': self.product_id.uom_id.id,
            'price_unit': best.price,
        })
        return {'type': 'ir.actions.act_window_close'}
