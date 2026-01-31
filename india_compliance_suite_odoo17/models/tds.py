
from odoo import models, fields

class TdsReturn(models.Model):
    _name = "tds.return"
    _description = "TDS Return"

    name = fields.Char(required=True)
    form_type = fields.Selection([
        ("24Q","24Q"),
        ("26Q","26Q"),
        ("27Q","27Q"),
        ("27EQ","27EQ")
    ], required=True)
    quarter = fields.Selection([("Q1","Q1"),("Q2","Q2"),("Q3","Q3"),("Q4","Q4")])
    year = fields.Integer()
