# # models/delivery_challan_report.py
# from odoo import models, fields, api

# class DeliveryChallanReport(models.Model):
#     _name = 'delivery.challan.report'
#     _description = 'Delivery Challan Report'

#     picking_id = fields.Many2one('stock.picking', string='Picking')
#     ewaybill_id = fields.Many2one('l10n.in.ewaybill', string='E-Way Bill')

#     # ------------------ Company / Header Info ------------------
#     company_id = fields.Many2one('res.company', string='Company', related='picking_id.company_id', store=True)
#     company_name = fields.Char(string='Company Name', related='company_id.name', store=True)
#     company_address = fields.Text(string='Company Address', compute='_compute_company_address', store=True)
#     company_gstin = fields.Char(string='Company GSTIN', related='company_id.vat', store=True)
#     # company_cin = fields.Char(string='Company CIN', related='company_id.cin', store=True)
#     company_email = fields.Char(string='Company Email', related='company_id.email', store=True)
#     company_website = fields.Char(string='Company Website', related='company_id.website', store=True)

#     # Contact Person / Contact Details
#     # FIXED: Changed from company_name to name (partner doesn't have company_name field)
#     contact_person = fields.Char(string='Contact Person', related='company_id.partner_id.name', store=True)
#     contact_mobile = fields.Char(string='Contact Mobile', related='company_id.partner_id.mobile', store=True)
#     contact_phone = fields.Char(string='Contact Phone', related='company_id.partner_id.phone', store=True)
#     contact_email = fields.Char(string='Contact Email', related='company_id.partner_id.email', store=True)

#     # ------------------ Customer Info ------------------
#     customer_name = fields.Char(string='Customer Name', related='picking_id.partner_id.name', store=True)
#     customer_street = fields.Char(string='Street', related='picking_id.partner_id.street', store=True)
#     customer_street2 = fields.Char(string='Street2', related='picking_id.partner_id.street2', store=True)
#     customer_city = fields.Char(string='City', related='picking_id.partner_id.city', store=True)
#     customer_state = fields.Many2one('res.country.state', string='State', related='picking_id.partner_id.state_id', store=True)
#     customer_zip = fields.Char(string='Zip', related='picking_id.partner_id.zip', store=True)
#     customer_country = fields.Many2one('res.country', string='Country', related='picking_id.partner_id.country_id', store=True)
#     customer_address = fields.Text(string='Customer Address', compute='_compute_customer_address', store=True)
#     customer_gstin = fields.Char(string='Customer GSTIN', related='picking_id.partner_id.vat', store=True)
#     customer_email = fields.Char(string='Customer Email', related='picking_id.partner_id.email', store=True)
#     customer_phone = fields.Char(string='Customer Phone', related='picking_id.partner_id.phone', store=True)
#     customer_mobile = fields.Char(string='Customer Mobile', related='picking_id.partner_id.mobile', store=True)

#     # ------------------ Picking / Delivery Info ------------------
#     document_date = fields.Date(string='Challan Date', related='picking_id.challan_date', store=True)
#     vehicle_no = fields.Char(string='Vehicle No', related='picking_id.vehicle_no', store=True)
#     transport_mode = fields.Selection([('road','Road'), ('air','Air'), ('sea','Sea'), ('rail','Rail')],
#                                       string='Transport Mode', related='picking_id.transport_mode', store=True)
#     transportation_document_no = fields.Char(string='Transport Document')

#     challan_type = fields.Selection([('foc','FOC'), ('paid','Paid')], string='Challan Type', default='paid')

#     # ------------------ Line Items ------------------
#     # FIXED: This should be related field, not One2many with picking_id
#     # One2many requires inverse_name which points back to this model
#     # Since stock.move doesn't have a field pointing to delivery.challan.report,
#     # we use a related field instead
#     move_line_ids = fields.One2many(related='picking_id.move_ids_without_package', string='Move Lines', readonly=True)

#     # ------------------ Charges ------------------
#     freight_charge = fields.Monetary(string='Freight Charge', currency_field='currency_id')
#     packing_charge = fields.Monetary(string='Packing Charge', currency_field='currency_id')
#     currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True)

#     # ------------------ Taxes ------------------
#     sgst_total = fields.Monetary(string='SGST', compute='_compute_taxes', store=True, currency_field='currency_id')
#     cgst_total = fields.Monetary(string='CGST', compute='_compute_taxes', store=True, currency_field='currency_id')
#     igst_total = fields.Monetary(string='IGST', compute='_compute_taxes', store=True, currency_field='currency_id')

#     # ------------------ Grand Total & Amount in Words ------------------
#     grand_total = fields.Monetary(string='Grand Total', compute='_compute_grand_total', store=True, currency_field='currency_id')
#     amount_in_words = fields.Char(string='Amount in Words', compute='_compute_amount_in_words', store=True)

#     # ------------------ Computed Methods ------------------
#     @api.depends('picking_id.partner_id', 'picking_id.partner_id.street', 'picking_id.partner_id.street2',
#                  'picking_id.partner_id.city', 'picking_id.partner_id.state_id', 
#                  'picking_id.partner_id.zip', 'picking_id.partner_id.country_id')
#     def _compute_customer_address(self):
#         for rec in self:
#             if not rec.picking_id or not rec.picking_id.partner_id:
#                 rec.customer_address = ''
#                 continue
                
#             partner = rec.picking_id.partner_id
#             address_parts = []
#             if partner.street:
#                 address_parts.append(partner.street)
#             if partner.street2:
#                 address_parts.append(partner.street2)
#             city_state_zip = ''
#             if partner.city:
#                 city_state_zip += partner.city
#             if partner.state_id:
#                 city_state_zip += ', ' + partner.state_id.name
#             if partner.zip:
#                 city_state_zip += ' - ' + partner.zip
#             if city_state_zip:
#                 address_parts.append(city_state_zip)
#             if partner.country_id:
#                 address_parts.append(partner.country_id.name)
#             rec.customer_address = '\n'.join(address_parts)

#     @api.depends('company_id', 'company_id.partner_id', 'company_id.partner_id.street',
#                  'company_id.partner_id.street2', 'company_id.partner_id.city',
#                  'company_id.partner_id.state_id', 'company_id.partner_id.zip',
#                  'company_id.partner_id.country_id')
#     def _compute_company_address(self):
#         for rec in self:
#             if not rec.company_id or not rec.company_id.partner_id:
#                 rec.company_address = ''
#                 continue
                
#             parts = []
#             partner = rec.company_id.partner_id
#             if partner.street:
#                 parts.append(partner.street)
#             if partner.street2:
#                 parts.append(partner.street2)
#             city_state_zip = ''
#             if partner.city:
#                 city_state_zip += partner.city
#             if partner.state_id:
#                 city_state_zip += ', ' + partner.state_id.name
#             if partner.zip:
#                 city_state_zip += ' - ' + partner.zip
#             if city_state_zip:
#                 parts.append(city_state_zip)
#             if partner.country_id:
#                 parts.append(partner.country_id.name)
#             rec.company_address = '\n'.join(parts)

#     @api.depends('picking_id.sale_id', 'picking_id.sale_id.order_line',
#                  'picking_id.sale_id.order_line.price_subtotal',
#                  'picking_id.sale_id.order_line.tax_id')
#     def _compute_taxes(self):
#         for rec in self:
#             sgst = cgst = igst = 0.0
#             if rec.picking_id and rec.picking_id.sale_id:
#                 for line in rec.picking_id.sale_id.order_line:
#                     for tax in line.tax_id:
#                         tax_amount = line.price_subtotal * tax.amount / 100
#                         # Check for SGST
#                         if 'SGST' in tax.name.upper() or 'S.G.S.T' in tax.name.upper():
#                             sgst += tax_amount
#                         # Check for CGST
#                         elif 'CGST' in tax.name.upper() or 'C.G.S.T' in tax.name.upper():
#                             cgst += tax_amount
#                         # Check for IGST
#                         elif 'IGST' in tax.name.upper() or 'I.G.S.T' in tax.name.upper():
#                             igst += tax_amount
#             rec.sgst_total = sgst
#             rec.cgst_total = cgst
#             rec.igst_total = igst

#     @api.depends('picking_id.sale_id', 'picking_id.sale_id.amount_total',
#                  'freight_charge', 'packing_charge')
#     def _compute_grand_total(self):
#         for rec in self:
#             # Base amount from sale order
#             total = 0.0
#             if rec.picking_id and rec.picking_id.sale_id:
#                 total = rec.picking_id.sale_id.amount_total
            
#             # Add freight and packing charges
#             rec.grand_total = total + (rec.freight_charge or 0.0) + (rec.packing_charge or 0.0)

#     @api.depends('grand_total', 'currency_id')
#     def _compute_amount_in_words(self):
#         for rec in self:
#             if rec.currency_id and rec.grand_total:
#                 rec.amount_in_words = rec.currency_id.amount_to_text(rec.grand_total)
#             else:
#                 rec.amount_in_words = ''
    
#     @api.model
#     def create(self, vals):
#         """
#         Override create to auto-populate freight and packing charges from sale order if not provided
#         """
#         # Auto-populate freight and packing from sale order if picking_id is provided
#         if vals.get('picking_id'):
#             picking = self.env['stock.picking'].browse(vals['picking_id'])
#             if picking.sale_id:
#                 # Only set if not already provided in vals
#                 if 'freight_charge' not in vals and hasattr(picking.sale_id, 'freight_charge_x'):
#                     vals['freight_charge'] = picking.sale_id.freight_charge_x or 0.0
#                 if 'packing_charge' not in vals and hasattr(picking.sale_id, 'packing_charge_x'):
#                     vals['packing_charge'] = picking.sale_id.packing_charge_x or 0.0
        
#         return super(DeliveryChallanReport, self).create(vals)