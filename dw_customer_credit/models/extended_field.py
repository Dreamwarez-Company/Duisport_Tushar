from odoo import models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'

    def print_dreamwarez_invoice(self):
        self.ensure_one()
        return self.env.ref('dw_customer_credit.action_report_delivery_challan').report_action(self)

    # Existing fields
    delivery_challan_no = fields.Char(string="Delivery Challan No")
    challan_date = fields.Date(string="Challan Date")
    transport_name = fields.Char(string="Transport Name")
    transport_mode = fields.Selection(
        [('road', 'Road'), ('air', 'Air'), ('sea', 'Sea'), ('rail', 'Rail')],
        string="Transport Mode"
    )
    vehicle_no = fields.Char(string="Vehicle No")
    eway_bill_no = fields.Char(string="E-Way Bill No")
    challan_type = fields.Selection(
        [('foc', 'FOC'), ('paid', 'Paid')],
        string="Challan Type"
    )
    contact_person = fields.Char(string="Contact Person")
    delivery_address = fields.Text(string="Delivery Address")
    irn_number = fields.Char(string='IRN Number', copy=False)
    ack_number = fields.Char(string='Ack Number', copy=False)
    ack_date = fields.Datetime(string='Ack Date', copy=False)

    # Payment terms selection field
    payment_terms_selection = fields.Selection(
        selection=[
            ('5_days', '5 Days'),
            ('10_days', '10 Days'),
            ('15_days', '15 Days'),
            ('20_days', '20 Days'),
            ('30_days', '30 Days'),
            ('45_days', '45 Days'),
            ('60_days', '60 Days'),
            ('90_days', '90 Days'),
            ('custom', 'Custom'),
        ],
        string='Mode/Terms of Payment',
        default='45_days',
        copy=False,
        help='Select payment terms for the invoice'
    )
    
    # Custom payment terms field
    payment_terms_custom = fields.Char(
        string='Custom Payment Terms',
        copy=False,
        help='Enter custom payment terms if "Custom" is selected'
    )

    # NEW FIELDS FOR INVOICE DETAILS
    delivery_note = fields.Char(string="Delivery Note")
    other_references = fields.Char(string="Other References")
    buyers_order_no = fields.Char(string="Buyers Order No")
    buyers_order_date = fields.Date(string="Buyers Order Date")
    dispatch_doc_no = fields.Char(string="Dispatch Doc No")
    delivery_note_date = fields.Date(string="Delivery Note Date")
    dispatched_through = fields.Char(string="Dispatched through")
    destination = fields.Char(string="Destination")
    terms_of_delivery = fields.Char(string="Terms of Delivery", default="Door Delivery")
    bill_of_lading_no = fields.Char(string="Bill of Lading/LR-RR No")
    company_pan_no = fields.Char(
        string="Company PAN No",
        help="Company PAN Number for Invoice"
    )

        # ✅ NEW DATE FIELD
    invoice_reference_date = fields.Date(
        string="Invoice Reference Date",
        help="Reference date for invoice"
    )

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    hsn_code = fields.Char(
        string="HSN Code",
        related='product_id.l10n_in_hsn_code',
        store=True,
        readonly=True
    )


