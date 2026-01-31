# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class dw_customer_credit(models.Model):
#     _name = 'dw_customer_credit.dw_customer_credit'
#     _description = 'dw_customer_credit.dw_customer_credit'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

