# -*- coding: utf-8 -*-
# from odoo import http


# class DwInventoryRule(http.Controller):
#     @http.route('/dw_inventory_rule/dw_inventory_rule', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/dw_inventory_rule/dw_inventory_rule/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('dw_inventory_rule.listing', {
#             'root': '/dw_inventory_rule/dw_inventory_rule',
#             'objects': http.request.env['dw_inventory_rule.dw_inventory_rule'].search([]),
#         })

#     @http.route('/dw_inventory_rule/dw_inventory_rule/objects/<model("dw_inventory_rule.dw_inventory_rule"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('dw_inventory_rule.object', {
#             'object': obj
#         })

