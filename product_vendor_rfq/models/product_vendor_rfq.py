from odoo import models, fields, api
from odoo.exceptions import UserError


class RFQ(models.Model):
    _name = 'rfq.request'
    _description = 'Request for Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='RFQ Number', required=True, copy=False, 
                       readonly=True, default='New')
    date = fields.Date(string='RFQ Date', default=fields.Date.today, 
                       required=True, tracking=True)
    deadline = fields.Date(string='Deadline', tracking=True)
    product_id = fields.Many2one('product.product', string='Product', 
                                 required=True, tracking=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', 
                             related='product_id.uom_id')
    description = fields.Text(string='Description')
    
    vendor_line_ids = fields.One2many('rfq.vendor.line', 'rfq_id', 
                                      string='Vendors')
    vendor_quote_ids = fields.One2many('rfq.vendor.quote', 'rfq_id', 
                                       string='Vendor Quotes')
    purchase_order_ids = fields.One2many('purchase.order', 'rfq_request_id',
                                         string='Purchase Orders')
    purchase_count = fields.Integer(string='Purchase Orders', 
                                    compute='_compute_purchase_count')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'RFQ Sent'),
        ('received', 'Quotes Received'),
        ('confirmed', 'Confirmed'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    confirmed_quote_id = fields.Many2one('rfq.vendor.quote', 
                                         string='Confirmed Quote')




    is_l1 = fields.Boolean(string='L1', readonly=True)
    is_l2 = fields.Boolean(string='L2', readonly=True)
    is_l3 = fields.Boolean(string='L3', readonly=True)

    
    @api.depends('purchase_order_ids')
    def _compute_purchase_count(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_order_ids)
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('rfq.request') or 'New'
        return super(RFQ, self).create(vals)
    
    def action_send_rfq(self):
        """Send RFQ emails to all selected vendors and create Purchase Orders"""
        if not self.vendor_line_ids:
            raise UserError('Please select at least one vendor.')
        
        # Check if email template exists
        try:
            template = self.env.ref('product_vendor_rfq.email_template_rfq')
        except:
            template = None
        
        PurchaseOrder = self.env['purchase.order'].sudo()
        
        for vendor_line in self.vendor_line_ids:
            # Get vendor partner
            vendor = vendor_line.vendor_id
            
            if not vendor:
                continue
            
            # Prepare order line values with all required fields
            order_line_vals = {
                'product_id': self.product_id.id,
                'product_qty': self.quantity,
                'product_uom': self.uom_id.id,
                'price_unit': 0.0,
                'name': self.product_id.name or self.product_id.display_name or 'Product',
                'date_planned': self.deadline or fields.Date.context_today(self),
            }
            
            # Create Purchase Order with proper context to avoid conflicts
            po_vals = {
                'partner_id': vendor.id,
                'rfq_request_id': self.id,
                'origin': self.name,
                'date_order': fields.Datetime.now(),
                'order_line': [(0, 0, order_line_vals)],
                'company_id': self.env.company.id,
            }
            
            try:
                # Create PO with context to skip custom validations if needed
                purchase_order = PurchaseOrder.with_context(
                    skip_custom_validation=True,
                    from_rfq_module=True
                ).create(po_vals)
                
                # Create vendor quote record
                quote = self.env['rfq.vendor.quote'].create({
                    'rfq_id': self.id,
                    'vendor_id': vendor.id,
                    'product_id': self.product_id.id,
                    'quantity': self.quantity,
                    'purchase_order_id': purchase_order.id,
                    'state': 'sent',
                })
                
                # Log PO creation in chatter
                self.message_post(
                    body=f"Purchase Order <a href='/web#id={purchase_order.id}&model=purchase.order'>{purchase_order.name}</a> created for vendor {vendor.name}",
                    subject="Purchase Order Created"
                )
                
                # Send email to vendor if template exists and vendor has email
                if template and vendor.email:
                    try:
                        template.send_mail(quote.id, force_send=True)
                    except Exception as e:
                        # Log error but don't stop the process
                        quote.message_post(
                            body=f"Failed to send email: {str(e)}",
                            subject="Email Error"
                        )
                        
            except Exception as e:
                # Log the error and continue with other vendors
                self.message_post(
                    body=f"Failed to create Purchase Order for vendor {vendor.name}: {str(e)}",
                    subject="PO Creation Error"
                )
                continue
        
        self.state = 'sent'
        
        # Final summary message
        po_count = len(self.purchase_order_ids)
        if po_count > 0:
            self.message_post(
                body=f"RFQ sent to {len(self.vendor_line_ids)} vendor(s). {po_count} Purchase Order(s) created successfully.",
                subject="RFQ Sent"
            )
        else:
            raise UserError('Failed to create any Purchase Orders. Please check the logs.')
    
    def action_view_purchase_orders(self):
        """View all purchase orders related to this RFQ"""
        try:
            action = self.env.ref('purchase.purchase_rfq').read()[0]

        
        except:
            action = {
                'name': 'Purchase Orders',
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'view_mode': 'tree,form',
            }

        
        # Filter to show only POs related to this RFQ
        action['domain'] = [('rfq_request_id', '=', self.id)]
        action['context'] = {
            'default_rfq_request_id': self.id,
        }
        
        return action
    

    # horizontal display
    def action_view_comparison(self):
        """Open comparison view for quotes"""

        for rec in self:
            rec.vendor_quote_ids._update_l_rankings()
        return {
            'name': 'Vendor Quote Comparison',
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.vendor.quote',
            'view_mode': 'tree,form',
            'domain': [('rfq_id', '=', self.id)],
            'context': {'default_rfq_id': self.id},
        }



# vertical display
    # def action_view_comparison(self):
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'target': 'new',
    #         'url': f"/rfq/comparison/{self.id}",
    #     }




class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    rfq_request_id = fields.Many2one('rfq.request', string='RFQ Request',
                                     ondelete='set null', index=True,
                                     help="Link to RFQ Management request")
    
    @api.model
    def create(self, vals):
        """Override to handle RFQ module context"""
        # If called from RFQ module, ensure partner_id is properly set
        if self.env.context.get('from_rfq_module') and 'partner_id' in vals:
            # Partner ID should already be correct, just ensure it's an integer
            if isinstance(vals.get('partner_id'), int):
                vals['partner_id'] = vals['partner_id']
        
        return super(PurchaseOrder, self).create(vals)


class RFQVendorLine(models.Model):
    _name = 'rfq.vendor.line'
    _description = 'RFQ Vendor Line'
    
    rfq_id = fields.Many2one('rfq.request', string='RFQ', ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', string='Vendor', 
                                domain=[('supplier_rank', '>', 0)], 
                                required=True)
    email = fields.Char(related='vendor_id.email', string='Email', readonly=True)
    phone = fields.Char(related='vendor_id.phone', string='Phone', readonly=True)


class RFQVendorQuote(models.Model):
    _name = 'rfq.vendor.quote'
    _description = 'Vendor Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Quote Reference', compute='_compute_name', 
                       store=True)
    rfq_id = fields.Many2one('rfq.request', string='RFQ', required=True, 
                             ondelete='cascade')
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
    product_id = fields.Many2one('product.product', string='Product', 
                                 required=True)
    quantity = fields.Float(string='Quantity', required=True)
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
                                        ondelete='cascade')
    
    unit_price = fields.Float(string='Unit Price', tracking=True)
    total_price = fields.Float(string='Total Price', compute='_compute_total', 
                               store=True)
    delivery_time = fields.Integer(string='Delivery Time (Days)')
    payment_terms = fields.Char(string='Payment Terms')
    notes = fields.Text(string='Notes')

    is_l1 = fields.Boolean(string='L1', readonly=True)
    is_l2 = fields.Boolean(string='L2', readonly=True)
    is_l3 = fields.Boolean(string='L3', readonly=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('received', 'Received'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    
    @api.depends('rfq_id', 'vendor_id')
    def _compute_name(self):
        for rec in self:
            if rec.rfq_id and rec.vendor_id:
                rec.name = f"{rec.rfq_id.name}/{rec.vendor_id.name}"
            else:
                rec.name = 'New'
    
    @api.depends('quantity', 'unit_price')
    def _compute_total(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.unit_price
    
    def action_confirm_quote(self):
        """Confirm this vendor quote and update Purchase Order"""
        self.ensure_one()
        
        if not self.unit_price:
            raise UserError('Please enter unit price before confirming.')
        
        if self.state != 'received':
            raise UserError('Only received quotes can be confirmed.')
            
        self.state = 'confirmed'
        self.rfq_id.confirmed_quote_id = self.id
        self.rfq_id.state = 'confirmed'
        
        # Update Purchase Order with quote details
        if self.purchase_order_id:
            for line in self.purchase_order_id.order_line:
                if line.product_id == self.product_id:
                    line.write({'price_unit': self.unit_price})
            
            # Add note to PO
            note_msg = "<p><strong>Vendor Quote Confirmed</strong></p><ul>"
            if self.payment_terms:
                note_msg += f"<li>Payment Terms: {self.payment_terms}</li>"
            if self.delivery_time:
                note_msg += f"<li>Delivery Time: {self.delivery_time} days</li>"
            if self.notes:
                note_msg += f"<li>Notes: {self.notes}</li>"
            note_msg += "</ul>"
            
            self.purchase_order_id.message_post(
                body=note_msg,
                subject="Vendor Quote Confirmed"
            )
        
        # Reject other quotes
        other_quotes = self.rfq_id.vendor_quote_ids.filtered(
            lambda q: q.id != self.id and q.state in ['sent', 'received']
        )
        if other_quotes:
            other_quotes.write({'state': 'rejected'})
        
        # Cancel other purchase orders
        if self.rfq_id.purchase_order_ids:
            other_pos = self.rfq_id.purchase_order_ids.filtered(
                lambda po: po.id != self.purchase_order_id.id and po.state == 'draft'
            )
            for po in other_pos:
                try:
                    po.button_cancel()
                except Exception as e:
                    po.message_post(
                        body=f"Could not cancel automatically: {str(e)}",
                        subject="Cancellation Note"
                    )
        
        return True
        
    def action_receive_quote(self):
        """Mark quote as received"""
        self.ensure_one()
        
        if self.state != 'sent':
            raise UserError('Only sent quotes can be marked as received.')
        
        self.state = 'received'
        
        # Check if all quotes received
        if all(q.state in ['received', 'rejected', 'confirmed'] 
               for q in self.rfq_id.vendor_quote_ids):
            self.rfq_id.state = 'received'
        
        return True
    
    def action_reject_quote(self):
        """Reject this vendor quote"""
        self.ensure_one()
        
        if self.state not in ['sent', 'received']:
            raise UserError('Only sent or received quotes can be rejected.')
        
        self.state = 'rejected'
        
        # Cancel associated purchase order
        if self.purchase_order_id and self.purchase_order_id.state == 'draft':
            try:
                self.purchase_order_id.button_cancel()
            except Exception as e:
                self.purchase_order_id.message_post(
                    body=f"Could not cancel automatically: {str(e)}",
                    subject="Cancellation Note"
                )
        
        return True
    

    def _update_l_rankings(self):
        """Assign L1, L2, L3 rankings based on total price (ascending)."""
        if not self.rfq_id:
            return

        # Get all vendor quotes for this RFQ that have total_price
        quotes = self.rfq_id.vendor_quote_ids.filtered(lambda q: q.total_price > 0)
        if not quotes:
            return

        # Sort by total_price ascending
        quotes = quotes.sorted(key=lambda q: q.total_price)

        # Reset all first
        quotes.write({'is_l1': False, 'is_l2': False, 'is_l3': False})

        # Assign ranks (write ensures DB update)
        if len(quotes) >= 1:
            quotes[0].write({'is_l1': True})
        if len(quotes) >= 2:
            quotes[1].write({'is_l2': True})
        if len(quotes) >= 3:
            quotes[2].write({'is_l3': True})


































# from odoo import models, fields, api
# from odoo.exceptions import UserError


# class RFQ(models.Model):
#     _name = 'rfq.request'
#     _description = 'Request for Quotation'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
#     _rec_name = 'name'

#     name = fields.Char(string='RFQ Number', required=True, copy=False, 
#                        readonly=True, default='New')
#     date = fields.Date(string='RFQ Date', default=fields.Date.today, 
#                        required=True, tracking=True)
#     deadline = fields.Date(string='Deadline', tracking=True)
#     product_id = fields.Many2one('product.product', string='Product', 
#                                  required=True, tracking=True)
#     quantity = fields.Float(string='Quantity', default=1.0, required=True)
#     uom_id = fields.Many2one('uom.uom', string='Unit of Measure', 
#                              related='product_id.uom_id')
#     description = fields.Text(string='Description')
    
#     vendor_line_ids = fields.One2many('rfq.vendor.line', 'rfq_id', 
#                                       string='Vendors')
#     vendor_quote_ids = fields.One2many('rfq.vendor.quote', 'rfq_id', 
#                                        string='Vendor Quotes')
    
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('sent', 'RFQ Sent'),
#         ('received', 'Quotes Received'),
#         ('confirmed', 'Confirmed'),
#         ('cancel', 'Cancelled')
#     ], string='Status', default='draft', tracking=True)
    
#     confirmed_quote_id = fields.Many2one('rfq.vendor.quote', 
#                                          string='Confirmed Quote')
    
#     @api.model
#     def create(self, vals):
#         if vals.get('name', 'New') == 'New':
#             vals['name'] = self.env['ir.sequence'].next_by_code('rfq.request') or 'New'
#         return super(RFQ, self).create(vals)
    
#     def action_send_rfq(self):
#         """Send RFQ emails to all selected vendors"""
#         if not self.vendor_line_ids:
#             raise UserError('Please select at least one vendor.')
        
#         template = self.env.ref('product_vendor_rfq.email_template_rfq')
        
#         for vendor_line in self.vendor_line_ids:
#             # Create vendor quote record
#             quote = self.env['rfq.vendor.quote'].create({
#                 'rfq_id': self.id,
#                 'vendor_id': vendor_line.vendor_id.id,
#                 'product_id': self.product_id.id,
#                 'quantity': self.quantity,
#                 'state': 'sent',
#             })
            
#             # Send email
#             if vendor_line.vendor_id.email:
#                 template.send_mail(quote.id, force_send=True)
        
#         self.state = 'sent'
        
#     def action_view_comparison(self):
#         """Open comparison view for quotes"""
#         return {
#             'name': 'Vendor Quote Comparison',
#             'type': 'ir.actions.act_window',
#             'res_model': 'rfq.vendor.quote',
#             'view_mode': 'tree,form',
#             'domain': [('rfq_id', '=', self.id)],
#             'context': {'default_rfq_id': self.id},
#         }


# class PurchaseOrder(models.Model):
#     _inherit = 'purchase.order'
    
#     rfq_request_id = fields.Many2one('rfq.request', string='RFQ Request',
#                                      ondelete='set null')


# class RFQVendorLine(models.Model):
#     _name = 'rfq.vendor.line'
#     _description = 'RFQ Vendor Line'
    
#     rfq_id = fields.Many2one('rfq.request', string='RFQ', ondelete='cascade')
#     vendor_id = fields.Many2one('res.partner', string='Vendor', 
#                                 domain=[('supplier_rank', '>', 0)], 
#                                 required=True)
#     email = fields.Char(related='vendor_id.email', string='Email')
#     phone = fields.Char(related='vendor_id.phone', string='Phone')


# class RFQVendorQuote(models.Model):
#     _name = 'rfq.vendor.quote'
#     _description = 'Vendor Quotation'
#     _inherit = ['mail.thread', 'mail.activity.mixin']
    
#     name = fields.Char(string='Quote Reference', compute='_compute_name', 
#                        store=True)
#     rfq_id = fields.Many2one('rfq.request', string='RFQ', required=True, 
#                              ondelete='cascade')
#     vendor_id = fields.Many2one('res.partner', string='Vendor', required=True)
#     product_id = fields.Many2one('product.product', string='Product', 
#                                  required=True)
#     quantity = fields.Float(string='Quantity', required=True)
#     purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',
#                                         ondelete='cascade')
    
#     unit_price = fields.Float(string='Unit Price', tracking=True)
#     total_price = fields.Float(string='Total Price', compute='_compute_total', 
#                                store=True)
#     delivery_time = fields.Integer(string='Delivery Time (Days)')
#     payment_terms = fields.Char(string='Payment Terms')
#     notes = fields.Text(string='Notes')
    
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('sent', 'Sent'),
#         ('received', 'Received'),
#         ('confirmed', 'Confirmed'),
#         ('rejected', 'Rejected')
#     ], string='Status', default='draft', tracking=True)
    
#     @api.depends('rfq_id', 'vendor_id')
#     def _compute_name(self):
#         for rec in self:
#             rec.name = f"{rec.rfq_id.name}/{rec.vendor_id.name}"
    
#     @api.depends('quantity', 'unit_price')
#     def _compute_total(self):
#         for rec in self:
#             rec.total_price = rec.quantity * rec.unit_price
    
#     def action_confirm_quote(self):
#         """Confirm this vendor quote and update Purchase Order"""
#         if not self.unit_price:
#             raise UserError('Please enter unit price before confirming.')
            
#         self.state = 'confirmed'
#         self.rfq_id.confirmed_quote_id = self.id
#         self.rfq_id.state = 'confirmed'
        
#         # Update Purchase Order with quote details
#         if self.purchase_order_id:
#             for line in self.purchase_order_id.order_line:
#                 if line.product_id == self.product_id:
#                     line.price_unit = self.unit_price
            
#             # Add note to PO
#             if self.notes or self.payment_terms:
#                 note_msg = ""
#                 if self.payment_terms:
#                     note_msg += f"Payment Terms: {self.payment_terms}\n"
#                 if self.delivery_time:
#                     note_msg += f"Delivery Time: {self.delivery_time} days\n"
#                 if self.notes:
#                     note_msg += f"Notes: {self.notes}"
                
#                 self.purchase_order_id.message_post(
#                     body=note_msg,
#                     subject="Vendor Quote Confirmed"
#                 )
        
#         # Reject other quotes
#         other_quotes = self.rfq_id.vendor_quote_ids.filtered(
#             lambda q: q.id != self.id and q.state in ['sent', 'received']
#         )
#         other_quotes.write({'state': 'rejected'})
        
#         # Cancel other purchase orders
#         other_pos = self.rfq_id.purchase_order_ids.filtered(
#             lambda po: po.id != self.purchase_order_id.id and po.state == 'draft'
#         )
#         other_pos.button_cancel()
        
#     def action_receive_quote(self):
#         """Mark quote as received"""
#         self.state = 'received'
        
#         # Check if all quotes received
#         if all(q.state in ['received', 'rejected'] 
#                for q in self.rfq_id.vendor_quote_ids):
#             self.rfq_id.state = 'received'
    
#     def action_reject_quote(self):
#         """Reject this vendor quote"""
#         self.state = 'rejected'
        
#         # Cancel associated purchase order
#         if self.purchase_order_id and self.purchase_order_id.state == 'draft':
#             self.purchase_order_id.button_cancel()