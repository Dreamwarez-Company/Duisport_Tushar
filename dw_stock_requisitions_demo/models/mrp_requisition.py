from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

# Add logger
_logger = logging.getLogger(__name__)

class MrpRequisition(models.Model):
    _name = 'dw.mrp.requisition'
    _description = 'Manufacturing Requisition Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date desc, id desc'
    
    name = fields.Char(
        string='Requisition Number',
        required=True,
        readonly=True,
        default=lambda self: _('New')
    )
    date = fields.Date(
        string='Requisition Date',
        default=fields.Date.today
    )
    department = fields.Selection([
        ('manufacturing', 'Manufacturing'),
        ('production', 'Production'),
        ('assembly', 'Assembly'),
        ('finishing', 'Finishing'),
        ('store', 'Store')
    ], string='Department', required=True, default='store')
    
    requested_by = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user
    )
    required_date = fields.Date(
        string='Required Date',
        required=True
    )
    
    manufacturing_order_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        domain="[('state', 'in', ['confirmed', 'progress'])]"
    )
    
    requisition_line_ids = fields.One2many(
        'dw.mrp.requisition.line',
        'requisition_id',
        string='Items'
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted to Store'),
        ('ready_for_transfer', 'Ready for Internal Transfer'),
        ('requested_other_location', 'Requested to Another Location')
        
    ], string='Status', default='draft')
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    notes = fields.Text(string='Internal Notes')
    
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', '=', 'internal')]",
        required=True,
        default=lambda self: self._get_default_source_location()
    )
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location', 
        domain="[('usage', '=', 'internal')]",
        required=True,
        default=lambda self: self._get_default_destination_location()
    )
    
    internal_transfer_id = fields.Many2one(
        'stock.picking',
        string='Internal Transfer',
        readonly=True
    )
    requested_location_id = fields.Many2one(
        'stock.location',
        string='Requested Location',
        domain="[('usage', '=', 'internal')]"
    )
    
    total_items = fields.Integer(
        string='Total Items',
        compute='_compute_total_items'
    )
    total_quantity = fields.Float(
        string='Total Quantity',
        compute='_compute_total_quantity'
    )
    
    @api.depends('requisition_line_ids')
    def _compute_total_items(self):
        for requisition in self:
            requisition.total_items = len(requisition.requisition_line_ids)
    
    @api.depends('requisition_line_ids.quantity')
    def _compute_total_quantity(self):
        for requisition in self:
            requisition.total_quantity = sum(line.quantity for line in requisition.requisition_line_ids)
    
    def _get_default_source_location(self):
        """Get default source location from stock settings"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return picking_type.default_location_src_id if picking_type else False
    
    def _get_default_destination_location(self):
        """Get default destination location from stock settings"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)
        return picking_type.default_location_dest_id if picking_type else False
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('dw.mrp.requisition') or _('New')
        return super().create(vals)
    
    def _check_manufacturing_user_permission(self):
        """Check if current user is a manufacturing user and owns the requisition"""
        is_manufacturing_user = self.env.user.has_group('dw_stock_requisitions_demo.group_manufacturing_team')
        is_admin = self.env.user.has_group('base.group_erp_manager')  # Built-in admin group
        is_requester = self.requested_by == self.env.user
        return (is_manufacturing_user and is_requester) or is_admin
    
    def _check_inventory_user_permission(self):
        """Check if current user is an inventory user or admin"""
        is_inventory_user = self.env.user.has_group('dw_stock_requisitions_demo.group_inventory_team')
        is_admin = self.env.user.has_group('base.group_erp_manager')  # Built-in admin group
        return is_inventory_user or is_admin
    
    def action_submit_to_store(self):
        """Submit requisition to store - Only manufacturing users can submit their own drafts"""
        for requisition in self:
            if requisition.state != 'draft':
                raise UserError(_("Only draft requisitions can be submitted."))
            
            if not requisition._check_manufacturing_user_permission():
                raise UserError(_("You can only submit your own draft requisitions."))
            
            # Admin can submit any requisition, manufacturing users only their own
            if not self.env.user.has_group('base.group_erp_manager') and requisition.requested_by != self.env.user:
                raise UserError(_("You can only submit your own requisitions."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot submit requisition without any items."))
            
            if not requisition.source_location_id or not requisition.destination_location_id:
                raise UserError(_("Please set both source and destination locations."))
            
            requisition.state = 'submitted'
        return True
        
    def action_ready_for_internal_transfer(self):
        """Create Internal Transfer - Only inventory users can process submitted requisitions"""
        for requisition in self:
            if requisition.state != 'submitted':
                raise UserError(_("Only submitted requisitions can be processed for transfer."))
            
            if not requisition._check_inventory_user_permission():
                raise UserError(_("Only inventory users can process requisitions."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot create transfer without any items."))
            
            if not requisition.source_location_id:
                raise UserError(_("Please set source location."))
            if not requisition.destination_location_id:
                raise UserError(_("Please set destination location."))
            
            # Check if all products are available in source location
            for line in requisition.requisition_line_ids:
                available_qty = line.product_id.with_context(
                    location=requisition.source_location_id.id
                ).qty_available
                
                if available_qty < line.quantity:
                    raise UserError(_(
                        "Product %s is not available in sufficient quantity at %s. Available: %s, Required: %s"
                    ) % (line.product_id.name, requisition.source_location_id.name, available_qty, line.quantity))
            
            # IMPROVED: Robust picking type search with multiple fallbacks
            picking_type = self._find_or_create_internal_picking_type(requisition.company_id)
            
            if not picking_type:
                raise UserError(_(
                    "No internal transfer operation type found. Please contact your administrator to set up Inventory operations."
                ))
            
            # Create picking with proper values
            picking_vals = {
                'picking_type_id': picking_type.id,
                'location_id': requisition.source_location_id.id,
                'location_dest_id': requisition.destination_location_id.id,
                'origin': f"Requisition: {requisition.name}",
                'scheduled_date': requisition.required_date,
                'company_id': requisition.company_id.id,
                'move_type': 'direct',
                'priority': '1',
            }
            
            picking = self.env['stock.picking'].create(picking_vals)
            
            # Create move lines
            for line in requisition.requisition_line_ids:
                move_vals = {
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.uom_id.id,
                    'product_uom_qty': line.quantity,
                    'picking_id': picking.id,
                    'location_id': requisition.source_location_id.id,
                    'location_dest_id': requisition.destination_location_id.id,
                    'company_id': requisition.company_id.id,
                }
                self.env['stock.move'].create(move_vals)
            
            requisition.internal_transfer_id = picking.id
            requisition.state = 'ready_for_transfer'
            
            # Confirm and assign the transfer
            picking.action_confirm()
            picking.action_assign()
        
        # Show success message AFTER the loop and state change
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Transfer Created'),
                'message': _('Internal transfer has been created successfully. State updated to Ready for Transfer.'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},  # Optional: close any wizard
            }
        }
    
    # def action_ready_for_internal_transfer(self):
    #     """Create Internal Transfer - Only inventory users can process submitted requisitions"""
    #     for requisition in self:
    #         if requisition.state != 'submitted':
    #             raise UserError(_("Only submitted requisitions can be processed for transfer."))
            
    #         if not requisition._check_inventory_user_permission():
    #             raise UserError(_("Only inventory users can process requisitions."))
            
    #         if not requisition.requisition_line_ids:
    #             raise UserError(_("Cannot create transfer without any items."))
            
    #         if not requisition.source_location_id:
    #             raise UserError(_("Please set source location."))
    #         if not requisition.destination_location_id:
    #             raise UserError(_("Please set destination location."))
            
    #         # Check if all products are available in source location
    #         for line in requisition.requisition_line_ids:
    #             available_qty = line.product_id.with_context(
    #                 location=requisition.source_location_id.id
    #             ).qty_available
                
    #             if available_qty < line.quantity:
    #                 raise UserError(_(
    #                     "Product %s is not available in sufficient quantity at %s. Available: %s, Required: %s"
    #                 ) % (line.product_id.name, requisition.source_location_id.name, available_qty, line.quantity))
            
    #         # IMPROVED: Robust picking type search with multiple fallbacks
    #         picking_type = self._find_or_create_internal_picking_type(requisition.company_id)
            
    #         if not picking_type:
    #             raise UserError(_(
    #                 "No internal transfer operation type found. Please contact your administrator to set up Inventory operations."
    #             ))
            
    #         # Create picking with proper values
    #         picking_vals = {
    #             'picking_type_id': picking_type.id,
    #             'location_id': requisition.source_location_id.id,
    #             'location_dest_id': requisition.destination_location_id.id,
    #             'origin': f"Requisition: {requisition.name}",
    #             'scheduled_date': requisition.required_date,
    #             'company_id': requisition.company_id.id,
    #             'move_type': 'direct',
    #             'priority': '1',
    #         }
            
    #         picking = self.env['stock.picking'].create(picking_vals)
            
    #         # Create move lines
    #         for line in requisition.requisition_line_ids:
    #             move_vals = {
    #                 'name': line.product_id.name,
    #                 'product_id': line.product_id.id,
    #                 'product_uom': line.uom_id.id,
    #                 'product_uom_qty': line.quantity,
    #                 'picking_id': picking.id,
    #                 'location_id': requisition.source_location_id.id,
    #                 'location_dest_id': requisition.destination_location_id.id,
    #                 'company_id': requisition.company_id.id,
    #             }
    #             self.env['stock.move'].create(move_vals)
            
    #         requisition.internal_transfer_id = picking.id
    #         requisition.state = 'ready_for_transfer'
            
    #         # Confirm and assign the transfer
    #         picking.action_confirm()
    #         picking.action_assign()
            
    #         # Show success message
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'title': _('Transfer Created'),
    #                 'message': _('Internal transfer %s has been created successfully.') % picking.name,
    #                 'sticky': False,
    #             }
    #         }
    #     return True

    def _find_or_create_internal_picking_type(self, company):
        """Find or create an internal picking type with multiple fallbacks"""
        # Try multiple search strategies
        search_domains = [
            [('code', '=', 'internal'), ('company_id', '=', company.id)],
            [('code', '=', 'internal'), ('company_id', '=', False)],
            [('code', '=', 'internal')],
            [('name', 'ilike', 'internal'), ('company_id', '=', company.id)],
            [('name', 'ilike', 'internal')],
        ]
        
        for domain in search_domains:
            picking_type = self.env['stock.picking.type'].search(domain, limit=1)
            if picking_type:
                return picking_type
        
        # If no picking type found, try to create one
        return self._create_default_internal_picking_type(company)

    def _create_default_internal_picking_type(self, company):
        """Create a default internal picking type"""
        try:
            # Get default locations
            stock_location = self.env.ref('stock.stock_location_stock')
            if not stock_location:
                # If stock location doesn't exist, search for any internal location
                stock_location = self.env['stock.location'].search([
                    ('usage', '=', 'internal')
                ], limit=1)
            
            if not stock_location:
                raise UserError(_("No internal stock locations found. Please set up inventory locations first."))
            
            # Create the picking type
            picking_type_vals = {
                'name': 'Internal Transfers',
                'code': 'internal',
                'sequence_code': 'INT',
                'default_location_src_id': stock_location.id,
                'default_location_dest_id': stock_location.id,
                'company_id': company.id,
            }
            
            return self.env['stock.picking.type'].create(picking_type_vals)
            
        except Exception as e:
            # Log the error but don't crash
            _logger.warning("Failed to create internal picking type: %s", str(e))
            return False
            
    def action_request_to_another_location(self):
        """Request products from another location - Only inventory users"""
        for requisition in self:
            if requisition.state != 'submitted':
                raise UserError(_("Only submitted requisitions can be requested from other locations."))
            
            if not requisition._check_inventory_user_permission():
                raise UserError(_("Only inventory users can request from other locations."))
            
            if not requisition.requested_location_id:
                raise UserError(_("Please select a location to request from."))
            
            requisition.state = 'requested_other_location'
        return True
    
    def action_set_draft(self):
        """Reset to draft - Only original requester, inventory users, or admin can reset"""
        for requisition in self:
            is_admin = self.env.user.has_group('base.group_erp_manager')
            can_reset = (
                is_admin or
                (requisition.state == 'draft' and requisition.requested_by == self.env.user) or
                (requisition.state == 'submitted' and self.env.user.has_group('dw_stock_requisitions_demo.group_inventory_team'))
            )
            
            if not can_reset:
                raise UserError(_("You don't have permission to reset this requisition."))
            
            requisition.state = 'draft'
            requisition.message_post(
                body=_("Requisition reset to draft."),
                subject=_("Reset to Draft")
            )
    def action_create_purchase_order(self):
        """Create and open Purchase Order from requisition - Only inventory users"""
        for requisition in self:
            if requisition.state != 'requested_other_location':
                raise UserError(_("Only requisitions in 'Requested to Another Location' state can create purchase orders."))
            
            if not requisition._check_inventory_user_permission():
                raise UserError(_("Only inventory users can create purchase orders."))
            
            if not requisition.requisition_line_ids:
                raise UserError(_("Cannot create purchase order without any items."))
            
            # Find a common vendor for all products
            common_partner = False
            vendor_candidates = {}
            
            # Collect all possible vendors from product suppliers
            for line in requisition.requisition_line_ids:
                if line.product_id.seller_ids:
                    for seller in line.product_id.seller_ids:
                        # Use seller.partner_id instead of seller.name
                        vendor_candidates[seller.partner_id.id] = vendor_candidates.get(seller.partner_id.id, 0) + 1
            
            # Find the vendor that supplies the most products
            if vendor_candidates:
                common_partner_id = max(vendor_candidates, key=vendor_candidates.get)
                common_partner = self.env['res.partner'].browse(common_partner_id)
            else:
                # If no vendor found, try to get any vendor from the company
                common_partner = self.env['res.partner'].search([
                    ('supplier_rank', '>', 0),
                    ('company_id', 'in', [False, requisition.company_id.id])
                ], limit=1)
                
                if not common_partner:
                    # If still no vendor, create a temporary one or raise error
                    raise UserError(_("No vendor found. Please set up at least one supplier in the system."))
            
            # Create purchase order with the found vendor
            purchase_vals = {
                'partner_id': common_partner.id,
                'origin': f"Requisition: {requisition.name}",
                'date_order': fields.Datetime.now(),
                'company_id': requisition.company_id.id,
                'currency_id': common_partner.property_purchase_currency_id.id or requisition.company_id.currency_id.id,
            }
            
            purchase_order = self.env['purchase.order'].create(purchase_vals)
            
            # Create purchase order lines
            for line in requisition.requisition_line_ids:
                # Get the supplier info for the product with the selected vendor
                seller = line.product_id._select_seller(
                    partner_id=common_partner,  # Pass the partner recordset, not ID
                    quantity=line.quantity,
                    date=fields.Date.today(),
                    uom_id=line.uom_id
                )
                
                line_vals = {
                    'order_id': purchase_order.id,
                    'product_id': line.product_id.id,
                    'name': line.description or line.product_id.name,
                    'product_qty': line.quantity,
                    'product_uom': line.uom_id.id,
                    'price_unit': seller.price if seller else line.product_id.standard_price,
                    'date_planned': requisition.required_date or fields.Date.today(),
                }
                self.env['purchase.order.line'].create(line_vals)
            
            # Return action to open the created purchase order in proper Purchase Order form view
            return {
                'type': 'ir.actions.act_window',
                'name': _('Purchase Order'),
                'res_model': 'purchase.order',
                'res_id': purchase_order.id,
                'view_mode': 'form',
                'view_id': self.env.ref('purchase.purchase_order_form').id,  # Force specific form view
                'target': 'current',
                'context': {
                    'form_view_initial_mode': 'edit',
                    'create': False,
                }
            }

    # def action_create_purchase_order(self):
    #     """Create and open Purchase Order from requisition - Only inventory users"""
    #     for requisition in self:
    #         if requisition.state != 'requested_other_location':
    #             raise UserError(_("Only requisitions in 'Requested to Another Location' state can create purchase orders."))
            
    #         if not requisition._check_inventory_user_permission():
    #             raise UserError(_("Only inventory users can create purchase orders."))
            
    #         if not requisition.requisition_line_ids:
    #             raise UserError(_("Cannot create purchase order without any items."))
            
    #         # Find a common vendor for all products
    #         common_partner = False
    #         vendor_candidates = {}
            
    #         # Collect all possible vendors from product suppliers
    #         for line in requisition.requisition_line_ids:
    #             if line.product_id.seller_ids:
    #                 for seller in line.product_id.seller_ids:
    #                     vendor_candidates[seller.partner_id.id] = vendor_candidates.get(seller.partner_id.id, 0) + 1
            
    #         # Find the vendor that supplies the most products
    #         if vendor_candidates:
    #             common_partner = max(vendor_candidates, key=vendor_candidates.get)
    #         else:
    #             # If no vendor found, try to get any vendor from the company
    #             default_vendor = self.env['res.partner'].search([
    #                 ('supplier_rank', '>', 0),
    #                 ('company_id', 'in', [False, requisition.company_id.id])
    #             ], limit=1)
                
    #             if not default_vendor:
    #                 # If still no vendor, create a temporary one or raise error
    #                 raise UserError(_("No vendor found. Please set up at least one supplier in the system."))
                
    #             common_partner = default_vendor.id
            
    #         # Create purchase order with the found vendor
    #         purchase_vals = {
    #             'partner_id': common_partner,
    #             'origin': f"Requisition: {requisition.name}",
    #             'date_order': fields.Datetime.now(),
    #             'company_id': requisition.company_id.id,
    #             'currency_id': self.env['res.partner'].browse(common_partner).property_purchase_currency_id.id or requisition.company_id.currency_id.id,
    #         }
            
    #         purchase_order = self.env['purchase.order'].create(purchase_vals)
            
    #         # Create purchase order lines
    #         for line in requisition.requisition_line_ids:
    #             # Get the supplier info for the product with the selected vendor
    #             seller = line.product_id._select_seller(
    #                 partner_id=common_partner,
    #                 quantity=line.quantity,
    #                 date=fields.Date.today(),
    #                 uom_id=line.uom_id
    #             )
                
    #             line_vals = {
    #                 'order_id': purchase_order.id,
    #                 'product_id': line.product_id.id,
    #                 'name': line.description or line.product_id.name,
    #                 'product_qty': line.quantity,
    #                 'product_uom': line.uom_id.id,
    #                 'price_unit': seller.price if seller else line.product_id.standard_price,
    #                 'date_planned': requisition.required_date or fields.Date.today(),
    #             }
    #             self.env['purchase.order.line'].create(line_vals)
            
    #         # Return action to open the created purchase order in proper Purchase Order form view
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'name': _('Purchase Order'),
    #             'res_model': 'purchase.order',
    #             'res_id': purchase_order.id,
    #             'view_mode': 'form',
    #             'view_id': self.env.ref('purchase.purchase_order_form').id,  # Force specific form view
    #             'target': 'current',
    #             'context': {
    #                 'form_view_initial_mode': 'edit',
    #                 'create': False,
    #             }
    #         }

    # def action_create_purchase_order(self):
    #     """Create and open Purchase Order from requisition - Only inventory users"""
    #     for requisition in self:
    #         if requisition.state != 'requested_other_location':
    #             raise UserError(_("Only requisitions in 'Requested to Another Location' state can create purchase orders."))
            
    #         if not requisition._check_inventory_user_permission():
    #             raise UserError(_("Only inventory users can create purchase orders."))
            
    #         if not requisition.requisition_line_ids:
    #             raise UserError(_("Cannot create purchase order without any items."))
            
    #         # Find a common vendor for all products
    #         common_partner = False
    #         vendor_candidates = {}
            
    #         # Collect all possible vendors from product suppliers
    #         for line in requisition.requisition_line_ids:
    #             if line.product_id.seller_ids:
    #                 for seller in line.product_id.seller_ids:
    #                     vendor_candidates[seller.name.id] = vendor_candidates.get(seller.name.id, 0) + 1
            
    #         # Find the vendor that supplies the most products
    #         if vendor_candidates:
    #             common_partner = max(vendor_candidates, key=vendor_candidates.get)
    #         else:
    #             # If no vendor found, try to get any vendor from the company
    #             default_vendor = self.env['res.partner'].search([
    #                 ('supplier_rank', '>', 0),
    #                 ('company_id', 'in', [False, requisition.company_id.id])
    #             ], limit=1)
                
    #             if not default_vendor:
    #                 # If still no vendor, create a temporary one or raise error
    #                 raise UserError(_("No vendor found. Please set up at least one supplier in the system."))
                
    #             common_partner = default_vendor.id
            
    #         # Create purchase order with the found vendor
    #         purchase_vals = {
    #             'partner_id': common_partner,
    #             'origin': f"Requisition: {requisition.name}",
    #             'date_order': fields.Datetime.now(),
    #             'company_id': requisition.company_id.id,
    #             'currency_id': self.env['res.partner'].browse(common_partner).property_purchase_currency_id.id or requisition.company_id.currency_id.id,
    #         }
            
    #         purchase_order = self.env['purchase.order'].create(purchase_vals)
            
    #         # Create purchase order lines
    #         for line in requisition.requisition_line_ids:
    #             # Get the supplier info for the product with the selected vendor
    #             seller = line.product_id._select_seller(
    #                 partner_id=common_partner,
    #                 quantity=line.quantity,
    #                 date=fields.Date.today(),
    #                 uom_id=line.uom_id
    #             )
                
    #             line_vals = {
    #                 'order_id': purchase_order.id,
    #                 'product_id': line.product_id.id,
    #                 'name': line.description or line.product_id.name,
    #                 'product_qty': line.quantity,
    #                 'product_uom': line.uom_id.id,
    #                 'price_unit': seller.price if seller else line.product_id.standard_price,
    #                 'date_planned': requisition.required_date or fields.Date.today(),
    #             }
    #             self.env['purchase.order.line'].create(line_vals)
            
    #         # Return action to open the created purchase order in form view
    #         return {
    #             'type': 'ir.actions.act_window',
    #             'res_model': 'purchase.order',
    #             'res_id': purchase_order.id,
    #             'view_mode': 'form',
    #             'target': 'current',
    #             'context': {'create': False},
    #         }



    # Add this at the bottom of your existing mrp_requisition.py file
# class PurchaseOrderWizard(models.TransientModel):
#     _name = 'purchase.order.wizard'
#     _description = 'Purchase Order Wizard'

#     partner_id = fields.Many2one(
#         'res.partner',
#         string='Vendor',
#         required=True,
#         domain="[('supplier_rank', '>', 0)]"
#     )
#     requisition_id = fields.Many2one(
#         'dw.mrp.requisition',
#         string='Requisition',
#         required=True
#     )

#     def action_create_purchase_order(self):
#         """Create Purchase Order with selected vendor"""
#         self.ensure_one()
        
#         requisition = self.requisition_id
        
#         # Create purchase order
#         purchase_vals = {
#             'partner_id': self.partner_id.id,
#             'origin': f"Requisition: {requisition.name}",
#             'date_order': fields.Datetime.now(),
#             'company_id': requisition.company_id.id,
#             'currency_id': self.partner_id.property_purchase_currency_id.id or requisition.company_id.currency_id.id,
#         }
        
#         purchase_order = self.env['purchase.order'].create(purchase_vals)
        
#         # Create purchase order lines
#         for line in requisition.requisition_line_ids:
#             # Get the supplier info for the product
#             seller = line.product_id._select_seller(
#                 partner_id=self.partner_id.id,
#                 quantity=line.quantity,
#                 date=fields.Date.today(),
#                 uom_id=line.uom_id
#             )
            
#             line_vals = {
#                 'order_id': purchase_order.id,
#                 'product_id': line.product_id.id,
#                 'name': line.description or line.product_id.name,
#                 'product_qty': line.quantity,
#                 'product_uom': line.uom_id.id,
#                 'price_unit': seller.price if seller else line.product_id.standard_price,
#                 'date_planned': requisition.required_date or fields.Date.today(),
#             }
#             self.env['purchase.order.line'].create(line_vals)
        
#         # Return action to open the created purchase order
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'purchase.order',
#             'res_id': purchase_order.id,
#             'view_mode': 'form',
#             'target': 'current',
#             'context': {'create': False},
#         }