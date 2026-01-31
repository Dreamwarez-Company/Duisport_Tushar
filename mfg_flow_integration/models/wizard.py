from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ManufactureOrPurchaseWizard(models.TransientModel):
    _name = 'manufacture.or.purchase.wizard'
    _description = 'Manufacture or Purchase Selection Wizard'

    production_request_id = fields.Many2one('production.request', string='Production Request')
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    warning_message = fields.Text(string="Stock Message", readonly=True)
    action_type = fields.Selection([
        ('manufacture', 'Create Manufacturing Order'),
        ('purchase', 'Create Purchase Order'),
    ], string="Action", required=False)

    def action_proceed(self):
        self.ensure_one()
        order = self.sale_order_id
        request = self.production_request_id

        if not self.action_type:
            raise UserError("Please select an action (Manufacture or Purchase).")

        if self.action_type == 'manufacture':
            mo_orders = self._create_manufacturing_orders(order, request)
            if request:
                request.write({'manufacturing_order_ids': [(6, 0, mo_orders.ids)]})
                request.message_post(
                    body=_('Manufacturing Orders created: %s') % ', '.join(mo_orders.mapped('name'))
                )
        elif self.action_type == 'purchase':
            return self._open_purchase_order_form(order, request)
        
        # Mark request as completed
        if request:
            request.action_mark_done()
        
        return {'type': 'ir.actions.act_window_close'}

    def _create_manufacturing_orders(self, order, request):
        """Create Manufacturing Orders for products without sufficient stock"""
        StockQuant = self.env['stock.quant']
        mo_orders = self.env['mrp.production']
        
        lines_to_process = request.line_ids if request else order.order_line.filtered(lambda l: l.product_id.type == 'product')
        
        for line in lines_to_process:
            if request:
                product = line.product_id
                qty_needed = line.quantity_needed
            else:
                product = line.product_id
                qty_available = StockQuant._get_available_quantity(
                    product, order.warehouse_id.lot_stock_id)
                qty_needed = line.product_uom_qty - qty_available
            
            if qty_needed > 0:
                bom = product.bom_ids[:1]
                if not bom:
                    raise UserError(f"No Bill of Materials found for product {product.display_name}.")
                
                mo = self.env['mrp.production'].create({
                    'product_id': product.id,
                    'product_qty': qty_needed,
                    'product_uom_id': product.uom_id.id,
                    'bom_id': bom.id,
                    'origin': order.name,
                })
                mo_orders |= mo
        
        return mo_orders

    def _open_purchase_order_form(self, order, request):
        """Open Purchase Order form with products that need purchasing"""
        StockQuant = self.env['stock.quant']
        po_lines = []
        
        lines_to_process = request.line_ids if request else order.order_line.filtered(lambda l: l.product_id.type == 'product')
        
        for line in lines_to_process:
            if request:
                product = line.product_id
                qty_needed = line.quantity_needed
            else:
                product = line.product_id
                qty_available = StockQuant._get_available_quantity(
                    product, order.warehouse_id.lot_stock_id)
                qty_needed = line.product_uom_qty - qty_available
            
            if qty_needed > 0:
                supplierinfo = product.seller_ids[:1]
                price = supplierinfo.price if supplierinfo else product.standard_price
                
                po_lines.append({
                    'product_id': product.id,
                    'name': product.display_name,
                    'product_qty': qty_needed,
                    'product_uom': product.uom_id.id,
                    'price_unit': price,
                    'date_planned': fields.Datetime.now(),
                })
        
        # Mark request as completed
        if request:
            request.action_mark_done()
            request.message_post(body=_('Purchase Order form opened for completion'))
        
        # Open new Purchase Order form
        return {
            'name': 'Create Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'current',
            'context': {
                'default_origin': order.name,
                'default_order_line': [(0, 0, line) for line in po_lines],
            }
        }


# working - 30/10
# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     warning_message = fields.Text(string="Stock Message", readonly=True)
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=False)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         if not self.action_type:
#             raise UserError("Please select an action (Manufacture or Purchase).")

#         if self.action_type == 'manufacture':
#             self._create_manufacturing_orders(order)
#         elif self.action_type == 'purchase':
#             return self._open_purchase_order_form(order)
        
#         # ✅ Mark MO/PO as created
#         order.mark_mo_po_created()
        
#         return {'type': 'ir.actions.act_window_close'}

#     def _create_manufacturing_orders(self, order):
#         """Create Manufacturing Orders for products without sufficient stock"""
#         StockQuant = self.env['stock.quant']
        
#         for line in order.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             product = line.product_id
#             qty_available = StockQuant._get_available_quantity(
#                 product, order.warehouse_id.lot_stock_id)
#             qty_needed = line.product_uom_qty - qty_available
            
#             if qty_needed > 0:
#                 bom = product.bom_ids[:1]
#                 if not bom:
#                     raise UserError(f"No Bill of Materials found for product {product.display_name}.")
                
#                 self.env['mrp.production'].create({
#                     'product_id': product.id,
#                     'product_qty': qty_needed,
#                     'product_uom_id': line.product_uom.id,
#                     'bom_id': bom.id,
#                     'origin': order.name,
#                 })

#     def _open_purchase_order_form(self, order):
#         """Open Purchase Order form with products that need purchasing"""
#         StockQuant = self.env['stock.quant']
#         po_lines = []
        
#         for line in order.order_line.filtered(lambda l: l.product_id.type == 'product'):
#             product = line.product_id
#             qty_available = StockQuant._get_available_quantity(
#                 product, order.warehouse_id.lot_stock_id)
#             qty_needed = line.product_uom_qty - qty_available
            
#             if qty_needed > 0:
#                 # Get supplier info if available
#                 supplierinfo = product.seller_ids[:1]
#                 price = supplierinfo.price if supplierinfo else product.standard_price
                
#                 po_lines.append({
#                     'product_id': product.id,
#                     'name': product.display_name,
#                     'product_qty': qty_needed,
#                     'product_uom': line.product_uom.id,
#                     'price_unit': price,
#                     'date_planned': fields.Datetime.now(),
#                 })
        
#         # Mark as created before opening PO form
#         order.mark_mo_po_created()
        
#         # Open new Purchase Order form
#         return {
#             'name': 'Create Purchase Order',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'view_mode': 'form',
#             'view_type': 'form',
#             'target': 'current',
#             'context': {
#                 'default_origin': order.name,
#                 'default_order_line': [(0, 0, line) for line in po_lines],
#             }
#         }





#workingg - 29/10

# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     warning_message = fields.Text(string="Stock Message", readonly=True)
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=False)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         if not self.action_type:
#             raise UserError("Please select an action (Manufacture or Purchase).")

#         if self.action_type == 'manufacture':
#             self._create_manufacturing_orders(order)
#         elif self.action_type == 'purchase':
#             return self._open_purchase_order_form(order)
        
#         # ✅ CRITICAL: Confirm the sale order after creating MO/PO
#         order.confirm_after_manufacture_purchase()
        
#         return {'type': 'ir.actions.act_window_close'}

#     def _create_manufacturing_orders(self, order):
#         """Create Manufacturing Orders for all order lines"""
#         for line in order.order_line:
#             product = line.product_id
#             bom = product.bom_ids[:1]
#             if not bom:
#                 raise UserError(f"No Bill of Materials found for product {product.display_name}.")
            
#             self.env['mrp.production'].create({
#                 'product_id': product.id,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom_id': line.product_uom.id,
#                 'bom_id': bom.id,
#                 'origin': order.name,
#             })

#     def _open_purchase_order_form(self, order):
#         """Open Purchase Order form with pre-filled order lines in context"""
#         # Prepare order lines data for context
#         po_lines = []
        
#         for line in order.order_line:
#             product = line.product_id
            
#             # Get supplier info if available
#             supplierinfo = product.seller_ids[:1]
#             price = supplierinfo.price if supplierinfo else product.standard_price
            
#             po_lines.append({
#                 'product_id': product.id,
#                 'name': product.display_name,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom': line.product_uom.id,
#                 'price_unit': price,
#                 'date_planned': fields.Datetime.now(),
#             })
        
#         # ✅ First confirm the sale order
#         order.confirm_after_manufacture_purchase()
        
#         # Then open new Purchase Order form with lines in context
#         return {
#             'name': 'Create Purchase Order',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'view_mode': 'form',
#             'view_type': 'form',
#             'target': 'current',
#             'context': {
#                 'default_origin': order.name,
#                 'default_order_line': [(0, 0, line) for line in po_lines],
#             }
#         }





# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     warning_message = fields.Text(string="Stock Message", readonly=True)
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=False)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         if not self.action_type:
#             raise UserError("Please select an action (Manufacture or Purchase).")

#         if self.action_type == 'manufacture':
#             return self._create_manufacturing_orders(order)
#         elif self.action_type == 'purchase':
#             return self._open_purchase_order_form(order)

#     def _create_manufacturing_orders(self, order):
#         """Create Manufacturing Orders for all order lines"""
#         for line in order.order_line:
#             product = line.product_id
#             bom = product.bom_ids[:1]
#             if not bom:
#                 raise UserError(f"No Bill of Materials found for product {product.display_name}.")
            
#             self.env['mrp.production'].create({
#                 'product_id': product.id,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom_id': line.product_uom.id,
#                 'bom_id': bom.id,
#                 'origin': order.name,
#             })
        
#         return {'type': 'ir.actions.act_window_close'}

#     def _open_purchase_order_form(self, order):
#         """Open Purchase Order form with pre-filled order lines in context"""
#         # Prepare order lines data for context
#         po_lines = []
        
#         for line in order.order_line:
#             product = line.product_id
            
#             # Get supplier info if available
#             supplierinfo = product.seller_ids[:1]
#             price = supplierinfo.price if supplierinfo else product.standard_price
            
#             po_lines.append({
#                 'product_id': product.id,
#                 'name': product.display_name,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom': line.product_uom.id,
#                 'price_unit': price,
#                 'date_planned': fields.Datetime.now(),
#             })
        
#         # Open new Purchase Order form with lines in context
#         return {
#             'name': 'Create Purchase Order',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'view_mode': 'form',
#             'view_type': 'form',
#             'target': 'current',
#             'context': {
#                 'default_origin': order.name,
#                 'default_order_line': [(0, 0, line) for line in po_lines],
#             }
#         }







# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     warning_message = fields.Text(string="Stock Message", readonly=True)
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=False)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         if not self.action_type:
#             raise UserError("Please select an action (Manufacture or Purchase).")

#         if self.action_type == 'manufacture':
#             return self._create_manufacturing_orders(order)
#         elif self.action_type == 'purchase':
#             return self._create_purchase_order(order)

#     def _create_manufacturing_orders(self, order):
#         """Create Manufacturing Orders for all order lines"""
#         for line in order.order_line:
#             product = line.product_id
#             bom = product.bom_ids[:1]
#             if not bom:
#                 raise UserError(f"No Bill of Materials found for product {product.display_name}.")
            
#             self.env['mrp.production'].create({
#                 'product_id': product.id,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom_id': line.product_uom.id,
#                 'bom_id': bom.id,
#                 'origin': order.name,
#             })
        
#         return {'type': 'ir.actions.act_window_close'}

#     def _create_purchase_order(self, order):
#         """Create Purchase Order and open form view for vendor selection"""
#         # Collect all products that need to be purchased
#         po_lines = []
        
#         for line in order.order_line:
#             product = line.product_id
            
#             # Get supplier info if available (optional)
#             supplierinfo = product.seller_ids[:1]
#             price = supplierinfo.price if supplierinfo else product.standard_price
            
#             po_lines.append((0, 0, {
#                 'product_id': product.id,
#                 'name': product.display_name,
#                 'product_qty': line.product_uom_qty,
#                 'product_uom': line.product_uom.id,
#                 'price_unit': price,
#                 'date_planned': fields.Datetime.now(),
#             }))
        
#         # Create Purchase Order without vendor (user will select it)
#         purchase_order = self.env['purchase.order'].create({
#             'origin': order.name,
#             'order_line': po_lines,
#         })
        
#         # Open the Purchase Order form view
#         return {
#             'name': 'Purchase Order',
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'res_id': purchase_order.id,
#             'view_mode': 'form',
#             'view_type': 'form',
#             'target': 'current',
#         }















# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     warning_message = fields.Text(string="Stock Message", readonly=True)
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=False)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         if not self.action_type:
#             raise UserError("Please select an action (Manufacture or Purchase).")

#         for line in order.order_line:
#             product = line.product_id

#             # --- Manufacturing Path ---
#             if self.action_type == 'manufacture':
#                 bom = product.bom_ids[:1]
#                 if not bom:
#                     raise UserError(f"No Bill of Materials found for product {product.display_name}.")
#                 self.env['mrp.production'].create({
#                     'product_id': product.id,
#                     'product_qty': line.product_uom_qty,
#                     'product_uom_id': line.product_uom.id,
#                     'bom_id': bom.id,
#                     'origin': order.name,
#                 })

#             # --- Purchase Path ---
#             elif self.action_type == 'purchase':
#                 supplierinfo = product.seller_ids[:1]
#                 if not supplierinfo:
#                     raise UserError(f"No vendor found for product {product.display_name}. Please define at least one vendor.")
                
#                 vendor = supplierinfo.partner_id

#                 purchase_order = self.env['purchase.order'].create({
#                     'partner_id': vendor.id,
#                     'origin': order.name,
#                 })
#                 self.env['purchase.order.line'].create({
#                     'order_id': purchase_order.id,
#                     'product_id': product.id,
#                     'name': product.display_name,
#                     'product_qty': line.product_uom_qty,
#                     'product_uom': line.product_uom.id,
#                     'price_unit': supplierinfo.price or product.standard_price,
#                     'date_planned': fields.Datetime.now(),
#                 })
#         return {'type': 'ir.actions.act_window_close'}





















# from odoo import api, fields, models
# from odoo.exceptions import UserError

# class ManufactureOrPurchaseWizard(models.TransientModel):
#     _name = 'manufacture.or.purchase.wizard'
#     _description = 'Manufacture or Purchase Selection Wizard'

#     sale_order_id = fields.Many2one('sale.order', string="Sale Order")
#     action_type = fields.Selection([
#         ('manufacture', 'Create Manufacturing Order'),
#         ('purchase', 'Create Purchase Order'),
#     ], string="Action", required=True)

#     def action_proceed(self):
#         self.ensure_one()
#         order = self.sale_order_id

#         for line in order.order_line:
#             product = line.product_id

#             # --- Manufacturing Path ---
#             if self.action_type == 'manufacture':
#                 bom = product.bom_ids[:1]
#                 if not bom:
#                     raise UserError(f"No Bill of Materials found for product {product.display_name}.")
#                 self.env['mrp.production'].create({
#                     'product_id': product.id,
#                     'product_qty': line.product_uom_qty,
#                     'product_uom_id': line.product_uom.id,
#                     'bom_id': bom.id,
#                     'origin': order.name,
#                 })

#             # --- Purchase Path ---
#             elif self.action_type == 'purchase':
#                 supplierinfo = product.seller_ids[:1]
#                 if not supplierinfo:
#                     raise UserError(f"No vendor found for product {product.display_name}. Please define at least one vendor.")
                
#                 vendor = supplierinfo.partner_id

#                 purchase_order = self.env['purchase.order'].create({
#                     'partner_id': vendor.id,
#                     'origin': order.name,
#                 })
#                 self.env['purchase.order.line'].create({
#                     'order_id': purchase_order.id,
#                     'product_id': product.id,
#                     'name': product.display_name,
#                     'product_qty': line.product_uom_qty,
#                     'product_uom': line.product_uom.id,
#                     'price_unit': supplierinfo.price or product.standard_price,
#                     'date_planned': fields.Datetime.now(),
#                 })
#         return {'type': 'ir.actions.act_window_close'}
