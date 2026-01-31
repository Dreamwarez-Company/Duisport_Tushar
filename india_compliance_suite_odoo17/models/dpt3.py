
from odoo import models, fields

class McaDpt3(models.Model):
    _name = "mca.dpt3"
    _description = "MCA DPT-3"

    financial_year = fields.Char(required=True)
    outstanding_amount = fields.Float()
    auditor_certificate = fields.Binary()
