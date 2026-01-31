from odoo import models, fields, api

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    x_min_qty = fields.Float(
        string='Minimum Quantity',
        help="Alert when inventory goes below this quantity",
        default=0.0
    )


# from odoo import models, fields, api

# class ProductProduct(models.Model):
#     _inherit = 'product.product'
    
#     x_min_qty = fields.Float(
#         string='Minimum Quantity',
#         help="Alert when inventory goes below this quantity",
#         default=0.0
#     )

#     x_is_low_stock = fields.Boolean(
#         string='Low Stock',
#         compute='_compute_is_low_stock',
#         store=False,  # Not stored in database, computed on the fly
#         help="True when quantity is below minimum quantity"
#     )
    
#     @api.depends('qty_available', 'x_min_qty')
#     def _compute_is_low_stock(self):
#         for product in self:
#             # Check if product has stock and min quantity is set
#             if product.x_min_qty > 0 and product.qty_available <= product.x_min_qty:
#                 product.x_is_low_stock = True
#             else:
#                 product.x_is_low_stock = False