from odoo import http
from odoo.http import request

class RFQComparisonController(http.Controller):

    @http.route('/rfq/comparison/<int:rfq_id>', type='http', auth='user', website=True)
    def rfq_comparison_view(self, rfq_id, **kwargs):
        rfq = request.env['rfq.request'].browse(rfq_id)
        if not rfq.exists():
            return request.not_found()
        products = rfq.mapped('vendor_quote_ids.product_id')
        quotes = rfq.vendor_quote_ids.sorted(lambda q: (q.product_id.name, q.vendor_id.name))
        vendors = quotes.mapped('vendor_id')

        return request.render('product_vendor_rfq.rfq_vertical_comparison_template', {
            'rfq': rfq,
            'products': products,
            'vendors': vendors,
            'quotes': quotes,
        })
