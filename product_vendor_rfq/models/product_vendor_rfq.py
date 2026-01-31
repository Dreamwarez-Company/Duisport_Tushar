from odoo import models, fields, api
from odoo.exceptions import UserError


# =========================================================
# RFQ REQUEST
# =========================================================
class RFQ(models.Model):
    _name = 'rfq.request'
    _description = 'Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(
        string='RFQ Number',
        required=True,
        copy=False,
        readonly=True,
        default='New'
    )

    date = fields.Date(
        string='RFQ Date',
        default=fields.Date.today,
        required=True,
        tracking=True
    )

    deadline = fields.Date(string='Deadline', tracking=True)
    is_l1 = fields.Boolean(string="L1 Vendor", default=False)

    rfq_line_ids = fields.One2many(
        'rfq.request.line',
        'rfq_id',
        string='Products',
        copy=True
    )

    vendor_line_ids = fields.One2many(
        'rfq.vendor.line',
        'rfq_id',
        string='Vendors'
    )

    vendor_quote_ids = fields.One2many(
        'rfq.vendor.quote',
        'rfq_id',
        string='Vendor Quotes'
    )

    purchase_order_ids = fields.One2many(
        'purchase.order',
        'rfq_request_id',
        string='Purchase Orders'
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('received', 'Quotes Received'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled')
    ], default='draft', tracking=True)

    confirmed_quote_id = fields.Many2one(
        'rfq.vendor.quote',
        string='Confirmed Quote'
    )

   
    def action_send_rfq(self):
        for vendor_line in self.vendor_line_ids:
            po = self.env['purchase.order'].create({
                'partner_id': vendor_line.vendor_id.id,
                'rfq_request_id': self.id,
                'origin': self.name,
                'order_line': [
                    (0, 0, {
                        'product_id': l.product_id.id,
                        'product_qty': l.quantity,
                        'product_uom': l.uom_id.id,
                        'price_unit': 0,
                    }) for l in self.rfq_line_ids
                ]
            })

            quote = self.env['rfq.vendor.quote'].create({
                'rfq_id': self.id,
                'vendor_id': vendor_line.vendor_id.id,
                'purchase_order_id': po.id,
            })

            for line in self.rfq_line_ids:
                self.env['rfq.vendor.quote.line'].create({
                    'quote_id': quote.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                })

        self.state = 'sent'
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'rfq.request'
            ) or 'New'
        return super().create(vals)
   
   
   
   
    def action_view_comparison(self):
        for rec in self:
            rec.vendor_quote_ids.update_l_rankings()

        return {
            'name': 'Vendor Quote Comparison',
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.vendor.quote',
            'view_mode': 'tree,form',
            'domain': [('rfq_id', '=', self.id)],
        }


# =========================================================
# RFQ LINE (MULTIPLE PRODUCTS)
# =========================================================
class RFQRequestLine(models.Model):
    _name = 'rfq.request.line'
    _description = 'RFQ Product Line'

    rfq_id = fields.Many2one(
        'rfq.request',
        ondelete='cascade',
        required=True
    )

    product_id = fields.Many2one(
        'product.product',
        required=True
    )

    quantity = fields.Float(default=1.0, required=True)

    uom_id = fields.Many2one(
        'uom.uom',
        related='product_id.uom_id',
        readonly=True
    )

    description = fields.Text()


# =========================================================
# RFQ VENDOR LINE
# =========================================================
class RFQVendorLine(models.Model):
    _name = 'rfq.vendor.line'
    _description = 'RFQ Vendor Line'

    rfq_id = fields.Many2one(
        'rfq.request',
        ondelete='cascade'
    )

    vendor_id = fields.Many2one(
        'res.partner',
        domain=[('supplier_rank', '>', 0)],
        required=True
    )

    email = fields.Char(
        related='vendor_id.email',
        readonly=True
    )

    phone = fields.Char(
        related='vendor_id.phone',
        readonly=True
    )


# =========================================================
# RFQ VENDOR QUOTE (HEADER LEVEL)
# =========================================================
class RFQVendorQuote(models.Model):
    _name = 'rfq.vendor.quote'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Quote Reference', compute='_compute_name', 
                       store=True)
    rfq_id = fields.Many2one('rfq.request', required=True)
    vendor_id = fields.Many2one('res.partner', required=True)

    purchase_order_id = fields.Many2one('purchase.order')

    quote_line_ids = fields.One2many(
        'rfq.vendor.quote.line',
        'quote_id',
        string='Quoted Products'
    )

    total_amount = fields.Float(
        compute='_compute_total_amount',
        store=True
    )

    state = fields.Selection([
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
    ], default='sent', tracking=True)

    delivery_time = fields.Integer()
    payment_terms = fields.Char()
    notes = fields.Text()
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True
    )



    total_amount = fields.Float(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
        currency_field='currency_id'
    )

    is_l1 = fields.Boolean(string="L1")
    is_l2 = fields.Boolean(string="L2")
    is_l3 = fields.Boolean(string="L3")
    is_l4 = fields.Boolean(string="L4")

    @api.depends('rfq_id', 'vendor_id')
    def _compute_name(self):
        for rec in self:
            if rec.rfq_id and rec.vendor_id:
                rec.name = f"{rec.rfq_id.name}/{rec.vendor_id.name}"
            else:
                rec.name = 'New'

    # -----------------------------------------------------
    # SEND RFQ (Create PO per Vendor with multiple lines)
    # -----------------------------------------------------
    # def action_send_rfq(self):
    #     if not self.vendor_line_ids:
    #         raise UserError('Please select at least one vendor.')

    #     if not self.rfq_line_ids:
    #         raise UserError('Please add at least one product.')

    #     PurchaseOrder = self.env['purchase.order'].sudo()

    #     for vendor_line in self.vendor_line_ids:
    #         vendor = vendor_line.vendor_id
    #         order_lines = []

    #         for line in self.rfq_line_ids:
    #             order_lines.append((0, 0, {
    #                 'product_id': line.product_id.id,
    #                 'name': line.product_id.display_name,
    #                 'product_qty': line.quantity,
    #                 'product_uom': line.uom_id.id,
    #                 'price_unit': 0.0,
    #                 'date_planned': self.deadline or fields.Date.today(),
    #             }))

    #         po = PurchaseOrder.create({
    #             'partner_id': vendor.id,
    #             'rfq_request_id': self.id,
    #             'origin': self.name,
    #             'order_line': order_lines,
    #         })

    #         self.env['rfq.vendor.quote'].create({
    #             'rfq_id': self.id,
    #             'vendor_id': vendor.id,
    #             'purchase_order_id': po.id,
    #             'state': 'sent',
    #         })

    #     self.state = 'sent'

    @api.depends('quote_line_ids.total_price')
    def _compute_total_amount(self):
        for quote in self:
            quote.total_amount = sum(
                quote.quote_line_ids.mapped('total_price')
            )

            


    # @api.depends('rfq_id.name', 'vendor_id.name')
    # def _compute_name(self):
    #     for rec in self:
    #         if rec.rfq_id and rec.rfq_id.name != 'New' and rec.vendor_id:
    #             rec.name = f"{rec.rfq_id.name}/{rec.vendor_id.name}"
    #         else:
    #             rec.name = 'New'
    

    def action_receive_quote(self):
        self.ensure_one()
        self.state = 'received'

    # def action_confirm_quote(self):
    #     self.ensure_one()
    #     self.state = 'confirmed'
    #     self.rfq_id.state = 'confirmed'
    #     self.rfq_id.confirmed_quote_id = self.id

    #     other_quotes = self.rfq_id.vendor_quote_ids.filtered(
    #         lambda q: q.id != self.id
    #     )
    #     other_quotes.write({'state': 'rejected'})



    # def action_confirm_quote(self):
    #     """Confirm this vendor quote and update Purchase Order"""
    #     self.ensure_one()
        
    #     if not self.unit_price:
    #         raise UserError('Please enter unit price before confirming.')
        
    #     if self.state != 'received':
    #         raise UserError('Only received quotes can be confirmed.')
            
    #     self.state = 'confirmed'
    #     self.rfq_id.confirmed_quote_id = self.id
    #     self.rfq_id.state = 'confirmed'
        
    #     # Update Purchase Order with quote details
    #     if self.purchase_order_id:
    #         for line in self.purchase_order_id.order_line:
    #             if line.product_id == self.product_id:
    #                 line.write({'price_unit': self.unit_price})
            
    #         # Add note to PO
    #         note_msg = "<p><strong>Vendor Quote Confirmed</strong></p><ul>"
    #         if self.payment_terms:
    #             note_msg += f"<li>Payment Terms: {self.payment_terms}</li>"
    #         if self.delivery_time:
    #             note_msg += f"<li>Delivery Time: {self.delivery_time} days</li>"
    #         if self.notes:
    #             note_msg += f"<li>Notes: {self.notes}</li>"
    #         note_msg += "</ul>"
            
    #         self.purchase_order_id.message_post(
    #             body=note_msg,
    #             subject="Vendor Quote Confirmed"
    #         )
        
    #     # Reject other quotes
    #     other_quotes = self.rfq_id.vendor_quote_ids.filtered(
    #         lambda q: q.id != self.id and q.state in ['sent', 'received']
    #     )
    #     if other_quotes:
    #         other_quotes.write({'state': 'rejected'})
        
    #     # Cancel other purchase orders
    #     if self.rfq_id.purchase_order_ids:
    #         other_pos = self.rfq_id.purchase_order_ids.filtered(
    #             lambda po: po.id != self.purchase_order_id.id and po.state == 'draft'
    #         )
    #         for po in other_pos:
    #             try:
    #                 po.button_cancel()
    #             except Exception as e:
    #                 po.message_post(
    #                     body=f"Could not cancel automatically: {str(e)}",
    #                     subject="Cancellation Note"
    #                 )
        
    #     return True  

    # def action_confirm_quote(self):
    #     self.ensure_one()

    #     if self.state != 'received':
    #         raise UserError('Only received quotes can be confirmed.')

    #     self.state = 'confirmed'
    #     self.rfq_id.state = 'confirmed'

    #     for qline in self.quote_line_ids:
    #         po_line = self.purchase_order_id.order_line.filtered(
    #             lambda l: l.product_id == qline.product_id
    #         )
    #         if po_line:
    #             po_line.write({'price_unit': qline.unit_price})

    #     # Reject other quotes
    #     (self.rfq_id.vendor_quote_ids - self).write({'state': 'rejected'})

    def action_confirm_quote(self):
        self.ensure_one()

        if self.state != 'received':
            raise UserError("Only received quotes can be confirmed.")

        # Confirm this quote
        self.state = 'confirmed'
        self.rfq_id.state = 'confirmed'
        self.rfq_id.confirmed_quote_id = self.id

        # Update the purchase order with the quoted prices
        if self.purchase_order_id:
            for line in self.purchase_order_id.order_line:
                # Find matching quote line for the product
                qline = self.quote_line_ids.filtered(lambda q: q.product_id == line.product_id)
                if qline:
                    line.write({'price_unit': qline.unit_price})
            # You can optionally confirm the PO automatically
            # self.purchase_order_id.button_confirm()

        # Reject other quotes for this RFQ
        other_quotes = self.rfq_id.vendor_quote_ids.filtered(lambda q: q.id != self.id)
        other_quotes.write({'state': 'rejected'})

        # Cancel associated POs of rejected quotes if they exist and are in draft
        for quote in other_quotes:
            if quote.purchase_order_id and quote.purchase_order_id.state == 'draft':
                try:
                    quote.purchase_order_id.button_cancel()
                except Exception as e:
                    quote.purchase_order_id.message_post(
                        body=f"Could not cancel automatically: {str(e)}",
                        subject="Cancellation Note"
                    )

        # Optional: Update L1/L2 rankings after confirmation
        self.update_l_rankings()

        return True


    # def _update_l_rankings(self):
    #     quotes = self.rfq_id.vendor_quote_ids.sorted(
    #         key=lambda q: q.total_price
    #     )

    #     quotes.write({
    #         'is_l1': False,
    #         'is_l2': False,
    #         'is_l3': False
    #     })

    #     if len(quotes) > 0:
    #         quotes[0].is_l1 = True
    #     if len(quotes) > 1:
    #         quotes[1].is_l2 = True
    #     if len(quotes) > 2:
    #         quotes[2].is_l3 = True


    def update_l_rankings(self):
        for rfq in self.mapped('rfq_id'):
            # Filter quotes with a positive total_amount and sort ascending
            quotes = rfq.vendor_quote_ids.filtered(lambda q: q.total_amount > 0).sorted('total_amount')

            # Reset all flags first
            rfq.vendor_quote_ids.write({
                'is_l1': False,
                'is_l2': False,
                'is_l3': False,
                'is_l4': False,
            })

            # Set L1, L2, L3, L4 based on ranking
            for index, quote in enumerate(quotes):
                vals = {}
                if index == 0:
                    vals['is_l1'] = True
                elif index == 1:
                    vals['is_l2'] = True
                elif index == 2:
                    vals['is_l3'] = True
                elif index == 3:
                    vals['is_l4'] = True

                if vals:
                    quote.write(vals) 



    # def action_reject_quote(self):
    #     """Reject this vendor quote"""
    #     self.ensure_one()
        
    #     if self.state not in ['sent', 'received']:
    #         raise UserError('Only sent or received quotes can be rejected.')
        
    #     self.state = 'rejected'
        
    #     # Cancel associated purchase order
    #     if self.purchase_order_id and self.purchase_order_id.state == 'draft':
    #         try:
    #             self.purchase_order_id.button_cancel()
    #         except Exception as e:
    #             self.purchase_order_id.message_post(
    #                 body=f"Could not cancel automatically: {str(e)}",
    #                 subject="Cancellation Note"
    #             )
        
    #     return True
    

    def action_reject_quote(self):
        """Reject this vendor quote"""
        self.ensure_one()

        if self.state not in ['sent', 'received']:
            raise UserError('Only sent or received quotes can be rejected.')

        # Reject this quote
        self.write({
            'state': 'rejected',
            'is_l1': False,
            'is_l2': False,
            'is_l3': False,
            'is_l4': False,
        })

        # Cancel associated purchase order (if not confirmed)
        po = self.purchase_order_id
        if po and po.state not in ('purchase', 'done', 'cancel'):
            try:
                po.button_cancel()
            except Exception as e:
                po.message_post(
                    body=f"Could not cancel automatically: {str(e)}",
                    subject="Cancellation Note"
                )

        # If all quotes are rejected, update RFQ state
        rfq = self.rfq_id
        if rfq and not rfq.vendor_quote_ids.filtered(lambda q: q.state != 'rejected'):
            rfq.state = 'cancelled'

        return True


# =========================================================
# PURCHASE ORDER EXTENSION
# =========================================================
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    rfq_request_id = fields.Many2one(
        'rfq.request',
        ondelete='set null'
    )



class RFQVendorQuoteLine(models.Model):
    _name = 'rfq.vendor.quote.line'
    _description = 'Vendor Quote Line'

    quote_id = fields.Many2one(
        'rfq.vendor.quote',
        ondelete='cascade',
        required=True
    )

    rfq_id = fields.Many2one(
        related='quote_id.rfq_id',
        store=True
    )

    vendor_id = fields.Many2one(
        related='quote_id.vendor_id',
        store=True
    )
    delivery_time = fields.Integer(string="Delivery (Days)")
    product_id = fields.Many2one(
        'product.product',
        required=True
    )

    quantity = fields.Float(required=True)

    unit_price = fields.Float(default=0.0)

    total_price = fields.Float(
        compute='_compute_total',
        store=True
    )


    is_l1 = fields.Boolean(readonly=True)
    is_l2 = fields.Boolean(readonly=True)
    is_l3 = fields.Boolean(readonly=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price
