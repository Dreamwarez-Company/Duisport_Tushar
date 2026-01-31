from odoo import models, fields, api

class AccountMove(models.Model):
    """Inherits from the account.move model for adding the depreciation
    field to the account"""
    _inherit = 'account.move'

    # ---------------------------------------------------------
    # Logistics / Reference Fields
    # ---------------------------------------------------------
    other_references = fields.Char(string="Other References")
    dispatched_through = fields.Char(string="Dispatched through")
    destination = fields.Char(string="Destination")
    terms_of_delivery = fields.Char(string="Terms of Delivery")

    # ---------------------------------------------------------
    # Ship To / Consignee Fields
    # ---------------------------------------------------------
    ship_to_address = fields.Text(
        string="Ship To",
        help="Consignee / Ship To Address"
    )

    ship_to_name = fields.Char(string="Consignee (Ship to)")
    ship_to_street = fields.Char(string="Address Line 1")
    ship_to_street2 = fields.Char(string="Address Line 2")
    ship_to_city = fields.Char(string="City")
    ship_to_state_id = fields.Many2one(
        'res.country.state',
        string="State"
    )
    ship_to_zip = fields.Char(string="ZIP")
    ship_to_gstin = fields.Char(string="GSTIN/UIN")

    company_pan = fields.Char(
        string="Company PAN",
        compute="_compute_company_pan",
        help="Derived from Company GSTIN"
    )

    @api.depends('company_id.vat')
    def _compute_company_pan(self):
        for move in self:
            vat = move.company_id.vat or ''
            # PAN is chars 3-12 of GSTIN (skip state code)
            move.company_pan = vat[2:12] if len(vat) >= 12 else ''

    # If branch isn't in bank_id.name, add a custom field on res.partner.bank or use a related field.

    # ---------------------------------------------------------
    # Default Values (Company Address → Ship To)
    # ---------------------------------------------------------
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        company = self.env.company

        res.setdefault('ship_to_name', company.name)
        res.setdefault('ship_to_street', company.street)
        res.setdefault('ship_to_street2', company.street2)
        res.setdefault('ship_to_city', company.city)
        res.setdefault(
            'ship_to_state_id',
            company.state_id.id if company.state_id else False
        )
        res.setdefault('ship_to_zip', company.zip)
        res.setdefault('ship_to_gstin', company.vat)

        return res

    
