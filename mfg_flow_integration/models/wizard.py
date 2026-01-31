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

    # def action_proceed(self):
    #     self.ensure_one()
    #     order = self.sale_order_id
    #     request = self.production_request_id

    #     if not self.action_type:
    #         raise UserError("Please select an action (Manufacture or Purchase).")

    #     if self.action_type == 'manufacture':
    #         mo_orders = self._create_manufacturing_orders(order, request)
    #         if request:
    #             request.write({'manufacturing_order_ids': [(6, 0, mo_orders.ids)]})
    #             request.message_post(
    #                 body=_('Manufacturing Orders created: %s') % ', '.join(mo_orders.mapped('name'))
    #             )
    #     elif self.action_type == 'purchase':
    #         return self._open_purchase_order_form(order, request)
        
    #     # Mark request as completed
    #     if request:
    #         request.action_mark_done()
        
    #     return {'type': 'ir.actions.act_window_close'}

    
    # def action_proceed(self):
    #     self.ensure_one()
    #     order = self.sale_order_id
    #     request = self.production_request_id

    #     # ------------------------------------------------------------
    #     # CLOSE PREVIOUS STAGE (Production Started)
    #     # ------------------------------------------------------------
    #     last_track = self.env['department.time.tracking'].search([
    #         ('target_model', '=', f'production.request,{request.id}'),
    #         ('status', '=', 'in_progress')
    #     ], limit=1, order='start_time desc')

    #     if last_track:
    #         last_track.write({
    #             'end_time': fields.Datetime.now(),
    #             'status': 'done'
    #         })

    #     # ------------------------------------------------------------
    #     # CREATE NEW STAGE → MO/PO Created
    #     # ------------------------------------------------------------
    #     self.env['department.time.tracking'].create({
    #         'target_model': f'production.request,{request.id}',
    #         'stage_name': 'MO/PO Created',
    #         'user_id': self.env.user.id,
    #         'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
    #         'start_time': fields.Datetime.now(),
    #         'end_time': fields.Datetime.now(),
    #         'status': 'done',
    #         'lead_id': order.opportunity_id.id if order.opportunity_id else False,
    #     })

    #     # ------------------------------------------------------------
    #     # VALIDATION
    #     # ------------------------------------------------------------
    #     if not self.action_type:
    #         raise UserError("Please select an action (Manufacture or Purchase).")

    #     # ------------------------------------------------------------
    #     # MANUFACTURE FLOW
    #     # ------------------------------------------------------------
    #     if self.action_type == 'manufacture':
    #         mo_orders = self._create_manufacturing_orders(order, request)

    #         if request:
    #             request.write({'manufacturing_order_ids': [(6, 0, mo_orders.ids)]})
    #             request.message_post(
    #                 body=_('Manufacturing Orders created: %s') % ', '.join(mo_orders.mapped('name'))
    #             )

    #         request.action_mark_done()
    #         return {'type': 'ir.actions.act_window_close'}

    #     # ------------------------------------------------------------
    #     # PURCHASE FLOW
    #     # (Inside the function we will CLOSE this stage and create PO Created)
    #     # ------------------------------------------------------------
    #     elif self.action_type == 'purchase':
    #         return self._open_purchase_order_form(order, request)

    def action_proceed(self):
        self.ensure_one()
        order = self.sale_order_id
        request = self.production_request_id

        # 1️⃣ CLOSE PREVIOUS STAGE
        last_track = self.env['department.time.tracking'].search([
            ('target_model', '=', f'production.request,{request.id}'),
            ('status', '=', 'in_progress')
        ], limit=1, order='start_time desc')

        if last_track:
            last_track.write({
                'end_time': fields.Datetime.now(),
                'status': 'done'
            })

        # 2️⃣ CREATE NEW STAGE → MO/PO Created
        self.env['department.time.tracking'].create({
            'target_model': f'production.request,{request.id}',
            'stage_name': 'MO/PO Created',
            'user_id': self.env.user.id,
            'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
            'start_time': fields.Datetime.now(),
            'status': 'in_progress',
            'lead_id': order.opportunity_id.id if order.opportunity_id else False,
        })

        # VALIDATION
        if not self.action_type:
            raise UserError("Please select an action (Manufacture or Purchase).")

        if self.action_type == 'manufacture':
            mo_orders = self._create_manufacturing_orders(order, request)
            request.write({'manufacturing_order_ids': [(6, 0, mo_orders.ids)]})
            request.message_post(body=_('Manufacturing Orders created: %s') % ', '.join(mo_orders.mapped('name')))
            request.action_mark_done()
            return {'type': 'ir.actions.act_window_close'}

        elif self.action_type == 'purchase':
            return self._open_purchase_order_form(order, request)



    def _create_manufacturing_orders(self, order, request):
        """Create Manufacturing Orders and create MO Created stage"""
        StockQuant = self.env['stock.quant']
        mo_orders = self.env['mrp.production']
        
        lines_to_process = request.line_ids if request else order.order_line.filtered(
            lambda l: l.product_id.type == 'product'
        )
        
        for line in lines_to_process:

            if request:
                product = line.product_id
                qty_needed = line.quantity_needed
            else:
                product = line.product_id
                qty_available = StockQuant._get_available_quantity(
                    product, order.warehouse_id.lot_stock_id)
                qty_needed = line.product_uom_qty - qty_available

            if qty_needed <= 0:
                continue

            bom = product.bom_ids[:1]
            if not bom:
                raise UserError(f"No Bill of Materials found for product {product.display_name}.")

            # 1️⃣ CREATE MO
            mo = self.env['mrp.production'].create({
                'product_id': product.id,
                'product_qty': qty_needed,
                'product_uom_id': product.uom_id.id,
                'bom_id': bom.id,
                'origin': order.name,
            })
            mo_orders |= mo

            # 2️⃣ CLOSE MO/PO Created (under production.request)
            if request:
                last_track = self.env['department.time.tracking'].search([
                    ('target_model', '=', f'production.request,{request.id}'),
                    ('stage_name', '=', 'MO/PO Created'),
                    ('status', '=', 'in_progress'),
                ], limit=1, order="start_time desc")

                if last_track:
                    last_track.write({
                        'end_time': fields.Datetime.now(),
                        'status': 'done'
                    })

            # 3️⃣ CREATE MO Created (under mrp.production)
            self.env['department.time.tracking'].create({
                'target_model': f'mrp.production,{mo.id}',
                'stage_name': 'MO Created',
                'user_id': self.env.user.id,
                'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'start_time': fields.Datetime.now(),
                'status': 'in_progress',
                'lead_id': order.opportunity_id.id if order.opportunity_id else False,
            })

        return mo_orders



    # def _open_purchase_order_form(self, order, request):
    #     StockQuant = self.env['stock.quant']
    #     po_lines = []

    #     # Build PO lines
    #     lines_to_process = request.line_ids if request else order.order_line.filtered(
    #         lambda l: l.product_id.type == 'product'
    #     )

    #     for line in lines_to_process:
    #         product = line.product_id
    #         qty_needed = line.quantity_needed if request else (
    #             line.product_uom_qty - StockQuant._get_available_quantity(
    #                 product, order.warehouse_id.lot_stock_id
    #             )
    #         )

    #         if qty_needed > 0:
    #             supplierinfo = product.seller_ids[:1]
    #             price = supplierinfo.price if supplierinfo else product.standard_price

    #             po_lines.append({
    #                 'product_id': product.id,
    #                 'name': product.display_name,
    #                 'product_qty': qty_needed,
    #                 'product_uom': product.uom_id.id,
    #                 'price_unit': price,
    #                 'date_planned': fields.Datetime.now(),
    #             })

    #     # Create PO
    #     vendor = False
    #     if po_lines:
    #         prod = self.env['product.product'].browse(po_lines[0]['product_id'])
    #         vendor = prod.seller_ids[:1].partner_id.id if prod.seller_ids else False

    #     po = self.env['purchase.order'].create({
    #         'partner_id': vendor,
    #         'origin': order.name,
    #         'order_line': [(0, 0, line) for line in po_lines],
    #     })

    #     # Link PO to request
    #     if request:
    #         request.write({'purchase_order_ids': [(4, po.id)]})
    #         request.message_post(body=_('Draft Purchase Order %s created') % po.name)

    #     # ----------------------------------------------------
    #     # TIME TRACKING FIX:
    #     # CLOSE "MO/PO Created" BEFORE creating "PO Created"
    #     # ----------------------------------------------------
    #     last_track = self.env['department.time.tracking'].search([
    #         ('target_model', '=', f'production.request,{request.id}'),
    #         ('status', '=', 'in_progress'),
    #         ('stage_name', '=', 'MO/PO Created')
    #     ], limit=1, order='start_time desc')

    #     if last_track:
    #         last_track.write({
    #             'end_time': fields.Datetime.now(),
    #             'status': 'done'
    #         })

    #     # NOW create new stage → PO Created
    #     self.env['department.time.tracking'].create({
    #         'target_model': f'production.request,{request.id}',
    #         'stage_name': 'PO Created',
    #         'user_id': self.env.user.id,
    #         'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
    #         'start_time': fields.Datetime.now(),
    #         'status': 'in_progress',
    #         'lead_id': order.opportunity_id.id if order.opportunity_id else False,
    #     })

    #     # Open PO screen
    #     return {
    #         'name': 'Purchase Order',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'purchase.order',
    #         'res_id': po.id,
    #         'view_mode': 'form',
    #         'target': 'current',
    #     }



    def _open_purchase_order_form(self, order, request):
        RFQ = self.env['rfq.request']

        rfq_lines = []

        # Build RFQ product lines
        for line in request.line_ids:
            if line.quantity_needed > 0:
                rfq_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity_needed,
                    'description': line.product_id.display_name,
                }))

        if not rfq_lines:
            raise UserError(_("No products available to create RFQ."))

        # Create RFQ
        rfq = RFQ.sudo().create({
            'description': f'RFQ created from Production Request {request.name}',
            'rfq_line_ids': rfq_lines,
        })

        # Optional chatter log
        request.sudo().message_post(
            body=_("RFQ %s created.") % rfq.name,
            subtype_xmlid='mail.mt_note'
        )

        # Optional time tracking close/open
        last_track = self.env['department.time.tracking'].search([
            ('target_model', '=', f'production.request,{request.id}'),
            ('status', '=', 'in_progress')
        ], limit=1, order='start_time desc')

        if last_track:
            last_track.write({
                'end_time': fields.Datetime.now(),
                'status': 'done'
            })

        self.env['department.time.tracking'].create({
            'target_model': f'production.request,{request.id}',
            'stage_name': 'RFQ Created',
            'user_id': self.env.user.id,
            'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
            'start_time': fields.Datetime.now(),
            'status': 'in_progress',
        })

        # 🔥 OPEN YOUR RFQ FORM (NOT PURCHASE ORDER)
        return {
            'name': _('Request for Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'rfq.request',
            'res_id': rfq.id,
            'view_mode': 'form',
            'target': 'current',
        }



























    # def _open_purchase_order_form(self, order, request):
    #     """Open Purchase Order form with products that need purchasing"""
    #     StockQuant = self.env['stock.quant']
    #     po_lines = []
        
    #     lines_to_process = request.line_ids if request else order.order_line.filtered(lambda l: l.product_id.type == 'product')
        
    #     for line in lines_to_process:
    #         if request:
    #             product = line.product_id
    #             qty_needed = line.quantity_needed
    #         else:
    #             product = line.product_id
    #             qty_available = StockQuant._get_available_quantity(
    #                 product, order.warehouse_id.lot_stock_id)
    #             qty_needed = line.product_uom_qty - qty_available
            
    #         if qty_needed > 0:
    #             supplierinfo = product.seller_ids[:1]
    #             price = supplierinfo.price if supplierinfo else product.standard_price
                
    #             po_lines.append({
    #                 'product_id': product.id,
    #                 'name': product.display_name,
    #                 'product_qty': qty_needed,
    #                 'product_uom': product.uom_id.id,
    #                 'price_unit': price,
    #                 'date_planned': fields.Datetime.now(),
    #             })
        
    #     # Mark request as completed
    #     if request:
    #         request.action_mark_done()
    #         request.message_post(body=_('Purchase Order form opened for completion'))
        
    #     # Open new Purchase Order form
    #     return {
    #         'name': 'Create Purchase Order',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'purchase.order',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'target': 'current',
    #         'context': {
    #             'default_origin': order.name,
    #             'default_order_line': [(0, 0, line) for line in po_lines],
    #         }
    #     }


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
