from odoo import api, models, fields

class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    @api.model
    def create(self, vals):
        # If product provided and partner not set, pick best vendor (lowest price)
        if vals.get('product_id') and not vals.get('partner_id'):
            product = self.env['product.product'].browse(vals['product_id'])
            # use supplierinfo (seller_ids) for vendor info
            sellers = product.seller_ids.sorted(key=lambda s: s.price or 0.0)
            if sellers:
                best = sellers[0]
                vals['partner_id'] = best.partner_id.id
                vals['price_unit'] = best.price or vals.get('price_unit', 0.0)
        return super().create(vals)

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        # ensure lines have vendor & computed price before confirm
        for order in self:
            for line in order.order_line:
                if line.product_id and not line.partner_id:
                    sellers = line.product_id.seller_ids.sorted(key=lambda s: s.price or 0.0)
                    if sellers:
                        best = sellers[0]
                        line.partner_id = best.name.id
                        line.price_unit = best.price or line.price_unit
        return super().button_confirm()
