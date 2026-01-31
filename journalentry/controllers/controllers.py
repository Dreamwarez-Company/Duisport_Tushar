# -*- coding: utf-8 -*-
# from odoo import http


# class Journalentry(http.Controller):
#     @http.route('/journalentry/journalentry', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/journalentry/journalentry/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('journalentry.listing', {
#             'root': '/journalentry/journalentry',
#             'objects': http.request.env['journalentry.journalentry'].search([]),
#         })

#     @http.route('/journalentry/journalentry/objects/<model("journalentry.journalentry"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('journalentry.object', {
#             'object': obj
#         })

