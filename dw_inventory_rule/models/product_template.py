# product.py
from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    x_min_qty = fields.Float(
        string='Minimum Quantity',
        help="Alert when inventory goes below this quantity",
        default=0.0
    )

    x_below_min = fields.Boolean(
        string="Below Minimum",
        compute="_compute_below_min",
        store=False
    )

    @api.depends('x_min_qty', 'qty_available')
    def _compute_below_min(self):
        for rec in self:
            rec.x_below_min = rec.qty_available < rec.x_min_qty
