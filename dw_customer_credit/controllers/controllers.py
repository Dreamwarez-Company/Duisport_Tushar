# -*- coding: utf-8 -*-
# from odoo import http


# class DwCustomerCredit(http.Controller):
#     @http.route('/dw_customer_credit/dw_customer_credit', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dw_customer_credit/dw_customer_credit/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dw_customer_credit.listing', {
#             'root': '/dw_customer_credit/dw_customer_credit',
#             'objects': http.request.env['dw_customer_credit.dw_customer_credit'].search([]),
#         })

#     @http.route('/dw_customer_credit/dw_customer_credit/objects/<model("dw_customer_credit.dw_customer_credit"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dw_customer_credit.object', {
#             'object': obj
#         })

