from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'



    # partner_id = fields.Many2one('res.partner', string="Consignee Name")
    is_consignee_same_as_biling = fields.Boolean(string="Is Consignee Same as Customer")
    billing_address = fields.Many2one('res.partner', string="Billing Address")



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

   
   
   
   
   
   
    freight_charge_x = fields.Float(string="Freight Charge")
    packing_charge_x = fields.Float(string="Packing Charge")




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


    @api.onchange('is_consignee_same_as_biling', 'partner_id')
    def _onchange_consignee_same_as_billing(self):
        for move in self:
            if move.is_consignee_same_as_biling and move.partner_id:
                move.billing_address = move.partner_id
            elif not move.is_consignee_same_as_biling:
                move.billing_address = False



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    hsn_code = fields.Char(
        string="HSN Code",
        related='product_id.l10n_in_hsn_code',
        store=True,
        readonly=True
    )





class AccountMove(models.Model):
    _inherit = 'account.move'

    buyers_order_no = fields.Char(string="Buyer's Order No.")
    other_references = fields.Char(string="Other References")
    dispatch_doc_no = fields.Char(string="Dispatch Doc No.")
    dispatched_through = fields.Char(string="Dispatched through")
    destination = fields.Char(string="Destination")
    terms_of_delivery = fields.Text(string="Terms of Delivery")

    credit_dated = fields.Date(string="Dated")

    show_delivery_challan_tab = fields.Boolean(
        compute='_compute_show_delivery_challan_tab',
        store=False
    )

    @api.depends('state', 'move_type')
    def _compute_show_delivery_challan_tab(self):
        for move in self:
            move.show_delivery_challan_tab = (
                move.state == 'posted' and
                move.move_type in ('out_refund', 'in_refund')
            )


    def _get_report_base_filename(self):
        self.ensure_one()


        # If not a Credit Note, prevent Credit Note report
        if self.env.context.get('report_name') == 'all_reports_full.report_credit_note_document':
            if self.move_type != 'out_refund':
                return False


        return super()._get_report_base_filename()
    







class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_consignee_same_as_biling = fields.Boolean(
        string="Is Consignee Same as Customer"
    )
    billing_address = fields.Many2one(
        'res.partner',
        string="Billing Address"
    )

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


    @api.onchange('is_consignee_same_as_biling', 'partner_id')
    def _onchange_consignee_same_as_billing(self):
        """
        If consignee is same as customer:
        - auto set billing address
        - auto copy address to delivery address
        """
        for picking in self:
            # Apply ONLY for Delivery Orders
            if picking.picking_type_code != 'outgoing':
                continue

            if picking.is_consignee_same_as_biling and picking.partner_id:
                picking.billing_address = picking.partner_id

                # Build formatted address
                address = picking.partner_id._display_address()
                picking.delivery_address = address

            elif not picking.is_consignee_same_as_biling:
                picking.billing_address = False
                picking.delivery_address = False





class L10nInEwaybill(models.Model):
    _inherit = 'l10n.in.ewaybill'


    def action_print(self):
        self.ensure_one()

        return self.env.ref('all_reports_full.action_report_delivery_challan_ewaybill').report_action(self)