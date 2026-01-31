# -*- coding: utf-8 -*-
# from odoo import http


# class DwStockRequisition(http.Controller):
#     @http.route('/dw__stock_requisition/dw__stock_requisition', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dw__stock_requisition/dw__stock_requisition/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dw__stock_requisition.listing', {
#             'root': '/dw__stock_requisition/dw__stock_requisition',
#             'objects': http.request.env['dw__stock_requisition.dw__stock_requisition'].search([]),
#         })

#     @http.route('/dw__stock_requisition/dw__stock_requisition/objects/<model("dw__stock_requisition.dw__stock_requisition"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dw__stock_requisition.object', {
#             'object': obj
#         })

