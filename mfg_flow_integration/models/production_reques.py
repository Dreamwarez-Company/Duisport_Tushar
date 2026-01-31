from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ProductionRequest(models.Model):
    _name = 'production.request'
    _description = 'Production Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Request Number', required=True, copy=False, readonly=True, default='New')
    sale_order_id = fields.Many2one('sale.order', string='Sale Order', required=True, readonly=True, tracking=True)
    partner_id = fields.Many2one(related='sale_order_id.partner_id', string='Customer', store=True, readonly=True)
    salesperson_id = fields.Many2one(related='sale_order_id.user_id', string='Salesperson', store=True, readonly=True)
    
    state = fields.Selection([
        ('draft', 'New'),
        ('in_progress', 'In Progress'),
        ('done', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    
    request_date = fields.Datetime(string='Request Date', default=fields.Datetime.now, readonly=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)
    completion_date = fields.Datetime(string='Completion Date', readonly=True)
    
    # Product lines that need MO/PO
    line_ids = fields.One2many('production.request.line', 'request_id', string='Product Lines')
    
    # Related Manufacturing and Purchase Orders
    manufacturing_order_ids = fields.Many2many('mrp.production', string='Manufacturing Orders', readonly=True)
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Orders', readonly=True)
    
    notes = fields.Text(string='Notes')
    
    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('production.request') or 'New'
        return super(ProductionRequest, self).create(vals)

    def action_start_production(self):
        """Mark request as in progress"""
        self.ensure_one()
        self.write({
            'state': 'in_progress',
            'assigned_to': self.env.user.id,
        })
        self.message_post(body=_('Production request started by %s') % self.env.user.name)

    def action_open_mo_po_wizard(self):
        """Open wizard to create MO/PO"""
        self.ensure_one()
        
        if self.state == 'done':
            raise UserError(_('This request has already been completed.'))
        
        if self.state == 'cancelled':
            raise UserError(_('This request has been cancelled.'))
        
        # Auto-assign to current user if not assigned
        if not self.assigned_to:
            self.write({'assigned_to': self.env.user.id})
        
        # Change state to in_progress if still draft
        if self.state == 'draft':
            self.write({'state': 'in_progress'})
            self.message_post(body=_('Production request started by %s') % self.env.user.name)
        
        # Prepare message for wizard
        product_list = []
        for line in self.line_ids:
            product_list.append(f"{line.product_id.display_name} - Qty: {line.quantity_needed}")
        
        message = _("The following products need to be manufactured or purchased:\n- %s") % "\n- ".join(product_list)
        
        return {
            'name': _('Create Manufacturing/Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'manufacture.or.purchase.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_production_request_id': self.id,
                'default_sale_order_id': self.sale_order_id.id,
                'default_warning_message': message,
            },
        }

    def action_mark_done(self):
        """Mark request as completed"""
        self.ensure_one()
        self.write({
            'state': 'done',
            'completion_date': fields.Datetime.now(),
        })
        
        # Update sale order
        self.sale_order_id.write({'mo_po_created': True})
        
        # Notify salesperson
        self.sale_order_id._send_mo_po_notification()
        
        self.message_post(body=_('Production request completed by %s') % self.env.user.name)

    def action_cancel(self):
        """Cancel the request"""
        self.ensure_one()
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Production request cancelled by %s') % self.env.user.name)


    def action_view_sale_order(self):
        """View related sale order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sale Order'),
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class ProductionRequestLine(models.Model):
    _name = 'production.request.line'
    _description = 'Production Request Line'

    request_id = fields.Many2one('production.request', string='Production Request', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity_needed = fields.Float(string='Quantity Needed', required=True)
    quantity_available = fields.Float(string='Available Quantity', required=True)
    product_uom_id = fields.Many2one(related='product_id.uom_id', string='Unit of Measure')