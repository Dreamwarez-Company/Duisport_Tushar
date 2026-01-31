from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    is_requisition = fields.Boolean(string='Is Requisition')
    # requisition_number = fields.Char(string='Requisition Number', copy=False)
    manufacturing_order_id = fields.Many2one('mrp.production', string='Manufacturing Order')
    requisition_date = fields.Datetime(string='Requisition Date', default=fields.Datetime.now)
    created_by = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user)
    store_department_id = fields.Many2one('hr.department', string='Store Department')
    requisition_state = fields.Selection([
        ('draft', 'Draft Requisition'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('in_progress', 'In Progress'),
        ('done', 'Fulfilled'),
        ('cancelled', 'Cancelled')
    ], string='Requisition Status', default='draft')
    requisition_number = fields.Char(
        string="Requisition Number",
        readonly=True,
        copy=False,
        index=True
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string="Purchase Order",
        help="The Purchase Order against which this requisition is created."
    )
    @api.model
    def create(self, vals):
        if not vals.get('requisition_number'):
            vals['requisition_number'] = self.env['ir.sequence'].next_by_code('stock.picking.requisition') or 'REQ0001'
        return super(StockPicking, self).create(vals)

    
    responsible_person_id = fields.Many2one(
        'res.users', 
        string='Responsible Person',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    @api.model
    def create(self, vals):
        if vals.get('is_requisition') and not vals.get('requisition_number'):
            vals['requisition_number'] = self.env['ir.sequence'].next_by_code('stock.requisition') or 'New'
        return super(StockPicking, self).create(vals)
    
    def action_convert_to_requisition(self):
        """Convert regular transfer to requisition"""
        for picking in self:
            picking.write({
                'is_requisition': True,
                'requisition_state': 'draft'
            })
        return True
    
    def action_request_requisition(self):
        for picking in self:
            if picking.is_requisition and picking.requisition_state == 'draft':
                picking.requisition_state = 'requested'
    
    def action_approve_requisition(self):
        for picking in self:
            if picking.is_requisition and picking.requisition_state == 'requested':
                picking.requisition_state = 'approved'