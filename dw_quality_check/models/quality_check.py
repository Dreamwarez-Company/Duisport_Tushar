from odoo import models, fields, api
from odoo.exceptions import UserError

class DwQualityCheck(models.Model):
    _name = 'dw.quality.check'
    _description = 'Quality Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='QC Reference', required=True, copy=False, default='New')
    picking_id = fields.Many2one('stock.picking', string='Picking', ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    mrp_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial')  # No required=True    
    quantity = fields.Float(string='Quantity')
    passed = fields.Boolean(string='Passed')
    remarks = fields.Text(string='Remarks')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    inspected_by = fields.Many2one('res.users', string='Inspected By', default=lambda self: self.env.user)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed')
    ], string='QC Status', default='pending', tracking=True)
    qc_status = fields.Selection([
        ('received', 'Received for QC'),
        ('done', 'QC Done')
    ], string="QC Process Status", default='received', tracking=True)

    def action_qc_done(self):
        """Mark the QC as Done"""
        for rec in self:
            rec.qc_status = 'done'
            rec.message_post(body=f"Quality Check marked as Done by {self.env.user.name}")

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            seq = self.env['ir.sequence'].sudo().next_by_code('dw.quality.check') or 'QC/0000'
            vals['name'] = seq

        rec = super().create(vals)
        rec._update_picking_qc_state()

        if rec.picking_id:
            rec.picking_id.message_post(body=f'Quality check {rec.name} created with status {rec.status}')

        if rec.mrp_id:
            rec.mrp_id.message_post(body=f'Quality check {rec.name} created for Manufacturing Order {rec.mrp_id.name}')

        return rec


    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            rec._update_picking_qc_state()
        return res

    def action_set_passed(self):
        for rec in self:
            rec.status = 'passed'
            rec.passed = True
            rec._update_picking_qc_state()
            rec.message_post(body=f'QC {rec.name} marked as Passed by {self.env.user.name}')

    def action_set_failed(self):
        for rec in self:
            rec.status = 'failed'
            rec.passed = False
            rec._update_picking_qc_state()
            rec.message_post(body=f'QC {rec.name} marked as Failed by {self.env.user.name}')

    def _update_picking_qc_state(self):
        for rec in self:
            if rec.picking_id:
                qcs = self.search([('picking_id', '=', rec.picking_id.id)])
                if not qcs:
                    rec.picking_id.qc_state = 'not_required'
                else:
                    # rec.picking_id.qc_count = len(qcs)  # REMOVE THIS
                    if any(q.status == 'failed' for q in qcs):
                        rec.picking_id.qc_state = 'failed'
                    elif any(q.status == 'pending' for q in qcs):
                        rec.picking_id.qc_state = 'pending'
                    else:
                        rec.picking_id.qc_state = 'passed'

