# from odoo import api, models

# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     def action_confirm(self):
#         res = super().action_confirm()
#         for order in self:
#             for line in order.order_line:
#                 if line.product_id.type == 'product' and line.product_id.bom_ids:
#                     bom = line.product_id.bom_ids and line.product_id.bom_ids[0] or False
#                     if bom:
#                         self.env['mrp.production'].create({
#                             'product_id': line.product_id.id,
#                             'product_qty': line.product_uom_qty,
#                             'product_uom_id': line.product_uom.id,
#                             'bom_id': bom.id,
#                             'origin': order.name,
#                         })
#         return res


# from odoo import api, models

# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     def action_confirm(self):
#         res = super().action_confirm()

#         # Open wizard for user choice
#         return {
#             'name': 'Select Action',
#             'type': 'ir.actions.act_window',
#             'res_model': 'manufacture.or.purchase.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {'default_sale_order_id': self.id},
#         }


# from odoo import api, models, _
# from odoo.exceptions import UserError

# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     def action_confirm(self):
#         self.ensure_one()
#         StockQuant = self.env['stock.quant']

#         unavailable_products = []
#         for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             qty_available = StockQuant._get_available_quantity(
#                 line.product_id, self.warehouse_id.lot_stock_id)
#             if qty_available < line.product_uom_qty:
#                 unavailable_products.append(line.product_id.display_name)

#         # 🟥 If stock not available → Open wizard
#         if unavailable_products:
#             message = _("The following products are not available in stock:\n- %s") % "\n- ".join(unavailable_products)
#             return {
#                 'name': _('Product Not Available'),
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'manufacture.or.purchase.wizard',
#                 'view_mode': 'form',
#                 'target': 'new',
#                 'context': {
#                     'default_sale_order_id': self.id,
#                     'default_warning_message': message,
#                 },
#             }

#         # ✅ If stock available → Confirm the sale order and create delivery
#         res = super(SaleOrder, self).action_confirm()

#         # Ensure sale order state changes to 'sale'
#         self.state = 'sale'

#         # ✅ Show success notification
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'title': _('Stock Available'),
#                 'message': _('All products are available in stock. The order has been confirmed and delivery order created.'),
#                 'sticky': False,
#                 'type': 'success',
#             }
#         }



# from odoo import api, models, _
# from odoo.exceptions import UserError

# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     def action_confirm(self):
#         self.ensure_one()
#         StockQuant = self.env['stock.quant']

#         unavailable_products = []
#         for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             qty_available = StockQuant._get_available_quantity(
#                 line.product_id, self.warehouse_id.lot_stock_id)
#             if qty_available < line.product_uom_qty:
#                 unavailable_products.append(line.product_id.display_name)

#         # 🟥 If stock not available → Open wizard
#         if unavailable_products:
#             message = _("The following products are not available in stock:\n- %s") % "\n- ".join(unavailable_products)
#             return {
#                 'name': _('Product Not Available'),
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'manufacture.or.purchase.wizard',
#                 'view_mode': 'form',
#                 'target': 'new',
#                 'context': {
#                     'default_sale_order_id': self.id,
#                     'default_warning_message': message,
#                 },
#             }

#         # ✅ If stock available → Confirm the sale order normally
#         res = super(SaleOrder, self).action_confirm()

#         # Show success notification
#         self.env['bus.bus']._sendone(
#             self.env.user.partner_id,
#             'simple_notification',
#             {
#                 'title': _('Stock Available'),
#                 'message': _('All products are available in stock. The order has been confirmed and delivery order created.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         )

#         return res

#     def confirm_after_manufacture_purchase(self):
#         """
#         Called from wizard after creating MO/PO
#         Confirms the sale order and creates delivery order
#         """
#         self.ensure_one()
        
#         # Confirm the sale order (this will change state to 'sale' and create delivery)
#         res = super(SaleOrder, self).action_confirm()
        
#         # Show success notification
#         self.env['bus.bus']._sendone(
#             self.env.user.partner_id,
#             'simple_notification',
#             {
#                 'title': _('Order Confirmed'),
#                 'message': _('Manufacturing/Purchase orders created. Sale order confirmed and delivery order created.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         )
        
#         return res





# working - 29/10
# from odoo import api, models, _
# from odoo.exceptions import UserError

# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     def action_confirm(self):
#         self.ensure_one()
        
#         # Skip stock check if called from wizard
#         if self.env.context.get('skip_stock_check'):
#             res = super(SaleOrder, self).action_confirm()
#             return res
        
#         StockQuant = self.env['stock.quant']

#         unavailable_products = []
#         for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             qty_available = StockQuant._get_available_quantity(
#                 line.product_id, self.warehouse_id.lot_stock_id)
#             if qty_available < line.product_uom_qty:
#                 unavailable_products.append(line.product_id.display_name)

#         # 🟥 If stock not available → Open wizard
#         if unavailable_products:
#             message = _("The following products are not available in stock:\n- %s") % "\n- ".join(unavailable_products)
#             return {
#                 'name': _('Product Not Available'),
#                 'type': 'ir.actions.act_window',
#                 'res_model': 'manufacture.or.purchase.wizard',
#                 'view_mode': 'form',
#                 'target': 'new',
#                 'context': {
#                     'default_sale_order_id': self.id,
#                     'default_warning_message': message,
#                 },
#             }

#         # ✅ If stock available → Confirm the sale order normally
#         res = super(SaleOrder, self).action_confirm()

#         # Show success notification
#         self.env['bus.bus']._sendone(
#             self.env.user.partner_id,
#             'simple_notification',
#             {
#                 'title': _('Stock Available'),
#                 'message': _('All products are available in stock. The order has been confirmed and delivery order created.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         )

#         return res

#     def confirm_after_manufacture_purchase(self):
#         """
#         Called from wizard after creating MO/PO
#         Confirms the sale order and creates delivery order
#         """
#         self.ensure_one()
        
#         # Call action_confirm with context to skip stock check
#         res = self.with_context(skip_stock_check=True).action_confirm()
        
#         # Show success notification
#         self.env['bus.bus']._sendone(
#             self.env.user.partner_id,
#             'simple_notification',
#             {
#                 'title': _('Order Confirmed'),
#                 'message': _('Manufacturing/Purchase orders created. Sale order confirmed and delivery order created.'),
#                 'type': 'success',
#                 'sticky': False,
#             }
#         )
        
#         return res





# working , button for production team - 06/11

# from odoo import api, fields, models, _
# from odoo.exceptions import UserError
# import logging

# _logger = logging.getLogger(__name__)

# class SaleOrder(models.Model):
#     _inherit = "sale.order"
    
#     needs_manufacturing_purchase = fields.Boolean(
#         string="Needs MO/PO",
#         compute="_compute_needs_manufacturing_purchase",
#         store=True,
#         help="Indicates if this order needs Manufacturing or Purchase Orders"
#     )
#     mo_po_created = fields.Boolean(
#         string="MO/PO Created",
#         default=False,
#         help="Indicates if Manufacturing/Purchase orders have been created"
#     )

#     @api.depends('order_line.product_id', 'state')
#     def _compute_needs_manufacturing_purchase(self):
#         """Check if any product lacks sufficient stock"""
#         StockQuant = self.env['stock.quant']
        
#         for order in self:
#             needs_mo_po = False
            
#             if order.state == 'sale':
#                 for line in order.order_line.filtered(lambda l: l.product_id.type == 'product'):
#                     qty_available = StockQuant._get_available_quantity(
#                         line.product_id, order.warehouse_id.lot_stock_id)
#                     if qty_available < line.product_uom_qty:
#                         needs_mo_po = True
#                         break
            
#             order.needs_manufacturing_purchase = needs_mo_po

#     def action_confirm(self):
#         """Confirm quotation - just change state, no stock check"""
#         self.ensure_one()
        
#         # Directly confirm the sale order without stock check
#         res = super(SaleOrder, self).action_confirm()
        
#         # Check if MO/PO will be needed
#         StockQuant = self.env['stock.quant']
#         unavailable_products = []
        
#         for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             qty_available = StockQuant._get_available_quantity(
#                 line.product_id, self.warehouse_id.lot_stock_id)
#             if qty_available < line.product_uom_qty:
#                 unavailable_products.append(line.product_id.display_name)
        
#         # Show appropriate notification
#         if unavailable_products:
#             self.env['bus.bus']._sendone(
#                 self.env.user.partner_id,
#                 'simple_notification',
#                 {
#                     'title': _('Order Confirmed - Stock Required'),
#                     'message': _('Order confirmed successfully. Some products need manufacturing/purchase. Production team can now create MO/PO.'),
#                     'type': 'warning',
#                     'sticky': True,
#                 }
#             )
#         else:
#             self.env['bus.bus']._sendone(
#                 self.env.user.partner_id,
#                 'simple_notification',
#                 {
#                     'title': _('Stock Available'),
#                     'message': _('All products are available in stock. The order has been confirmed and delivery order created.'),
#                     'type': 'success',
#                     'sticky': False,
#                 }
#             )

#         return res

#     def action_open_mo_po_wizard(self):
#         """Open wizard for production team to create MO/PO"""
#         self.ensure_one()
        
#         if self.state != 'sale':
#             raise UserError(_('This order must be confirmed first by the sales team.'))
        
#         if self.mo_po_created:
#             raise UserError(_('Manufacturing/Purchase orders have already been created for this order.'))
        
#         # Check which products need MO/PO
#         StockQuant = self.env['stock.quant']
#         unavailable_products = []
        
#         for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             qty_available = StockQuant._get_available_quantity(
#                 line.product_id, self.warehouse_id.lot_stock_id)
#             if qty_available < line.product_uom_qty:
#                 unavailable_products.append(line.product_id.display_name)
        
#         if not unavailable_products:
#             raise UserError(_('All products are already available in stock. No manufacturing or purchase needed.'))
        
#         message = _("The following products need to be manufactured or purchased:\n- %s") % "\n- ".join(unavailable_products)
        
#         return {
#             'name': _('Create Manufacturing/Purchase Orders'),
#             'type': 'ir.actions.act_window',
#             'res_model': 'manufacture.or.purchase.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {
#                 'default_sale_order_id': self.id,
#                 'default_warning_message': message,
#             },
#         }

#     def mark_mo_po_created(self):
#         """Mark that MO/PO have been created for this order"""
#         self.ensure_one()
#         self.write({'mo_po_created': True})
        
#         # Send notification to salesperson
#         self._send_mo_po_notification()

#     def _send_mo_po_notification(self):
#         """Send email/notification to salesperson"""
#         self.ensure_one()
        
#         if self.user_id and self.user_id.email:
#             # Send internal message
#             self.message_post(
#                 body=_('Manufacturing/Purchase orders have been created by the production team for order %s.') % self.name,
#                 subject=_('MO/PO Created - %s') % self.name,
#                 partner_ids=[self.user_id.partner_id.id],
#                 message_type='notification',
#                 subtype_xmlid='mail.mt_note',
#             )




# "SEND TO PRODUCTION" button for sales team and "Create MO/PO" button only visible to production team
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    needs_manufacturing_purchase = fields.Boolean(
        string="Needs MO/PO",
        compute="_compute_needs_manufacturing_purchase",
        store=True,
        help="Indicates if this order needs Manufacturing or Purchase Orders"
    )
    mo_po_created = fields.Boolean(
        string="MO/PO Created",
        default=False,
        help="Indicates if Manufacturing/Purchase orders have been created"
    )
    sent_to_production = fields.Boolean(
        string="Sent to Production",
        default=False,
        help="Indicates if order has been sent to production team"
    )
    production_request_id = fields.Many2one(
        'production.request',
        string='Production Request',
        readonly=True,
        help="Related production request"
    )

    @api.depends('order_line.product_id', 'state')
    def _compute_needs_manufacturing_purchase(self):
        """Check if any product lacks sufficient stock"""
        StockQuant = self.env['stock.quant']
        
        for order in self:
            needs_mo_po = False
            
            if order.state == 'sale':
                for line in order.order_line.filtered(lambda l: l.product_id.type == 'product'):
                    qty_available = StockQuant._get_available_quantity(
                        line.product_id, order.warehouse_id.lot_stock_id)
                    if qty_available < line.product_uom_qty:
                        needs_mo_po = True
                        break
            
            order.needs_manufacturing_purchase = needs_mo_po

    def action_confirm(self):
        """Confirm quotation - just change state, no stock check"""
        self.ensure_one()
        
        # Directly confirm the sale order without stock check
        res = super(SaleOrder, self).action_confirm()
        
        # Check if MO/PO will be needed
        StockQuant = self.env['stock.quant']
        unavailable_products = []
        
        for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
            qty_available = StockQuant._get_available_quantity(
                line.product_id, self.warehouse_id.lot_stock_id)
            if qty_available < line.product_uom_qty:
                unavailable_products.append(line.product_id.display_name)
        
        # Show appropriate notification
        if unavailable_products:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Order Confirmed - Stock Required'),
                    'message': _('Order confirmed successfully. Click "Send to Production" to forward this order to production team.'),
                    'type': 'warning',
                    'sticky': True,
                }
            )
        else:
            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'simple_notification',
                {
                    'title': _('Stock Available'),
                    'message': _('All products are available in stock. The order has been confirmed and delivery order created.'),
                    'type': 'success',
                    'sticky': False,
                }
            )

        return res

    def action_send_to_production(self):
        """Send order to production team - creates production request"""
        self.ensure_one()
        
        if self.state != 'sale':
            raise UserError(_('This order must be confirmed first.'))
        
        if self.sent_to_production:
            raise UserError(_('This order has already been sent to production team.'))
        
        if not self.needs_manufacturing_purchase:
            raise UserError(_('All products are available in stock. No need to send to production.'))
        
        # Create production request
        production_request = self._create_production_request()
        
        # Mark as sent to production
        self.write({
            'sent_to_production': True,
            'production_request_id': production_request.id,
        })
        
        # Log in sale order
        self.message_post(
            body=_('Order sent to production team. Production Request: <a href="#" data-oe-model="production.request" data-oe-id="%s">%s</a>') % (production_request.id, production_request.name),
            subject=_('Sent to Production'),
        )
        
        # Show success message
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'simple_notification',
            {
                'title': _('Sent to Production'),
                'message': _('Production Request %s has been created and sent to production team.') % production_request.name,
                'type': 'success',
                'sticky': False,
            }
        )
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Request'),
            'res_model': 'production.request',
            'res_id': production_request.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_production_request(self):
        """Create production request with lines for products needing MO/PO"""
        self.ensure_one()
        
        StockQuant = self.env['stock.quant']
        request_lines = []
        
        for line in self.order_line.filtered(lambda l: l.product_id.type == 'product'):
            qty_available = StockQuant._get_available_quantity(
                line.product_id, self.warehouse_id.lot_stock_id)
            qty_needed = line.product_uom_qty - qty_available
            
            if qty_needed > 0:
                request_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity_needed': qty_needed,
                    'quantity_available': qty_available,
                }))
        
        production_request = self.env['production.request'].create({
            'sale_order_id': self.id,
            'line_ids': request_lines,
            'notes': _('Production request created from sale order %s') % self.name,
        })
        
        return production_request

    def _send_mo_po_notification(self):
        """Send notification to salesperson"""
        self.ensure_one()
        
        if self.user_id and self.user_id.partner_id:
            self.message_post(
                body=_('Manufacturing/Purchase orders have been created by the production team. The order is now ready for processing.'),
                subject=_('MO/PO Created - %s') % self.name,
                partner_ids=[self.user_id.partner_id.id],
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

    def action_view_production_request(self):
        """View related production request"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Production Request'),
            'res_model': 'production.request',
            'res_id': self.production_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }