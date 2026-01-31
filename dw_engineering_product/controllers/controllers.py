# -*- coding: utf-8 -*-
# from odoo import http


# class DwEngineeringProduct(http.Controller):
#     @http.route('/dw_engineering_product/dw_engineering_product', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dw_engineering_product/dw_engineering_product/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dw_engineering_product.listing', {
#             'root': '/dw_engineering_product/dw_engineering_product',
#             'objects': http.request.env['dw_engineering_product.dw_engineering_product'].search([]),
#         })

#     @http.route('/dw_engineering_product/dw_engineering_product/objects/<model("dw_engineering_product.dw_engineering_product"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dw_engineering_product.object', {
#             'object': obj
#         })

