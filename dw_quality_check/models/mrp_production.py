from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

# ✅ Define logger for this file
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    quality_check_ids = fields.One2many('dw.quality.check', 'mrp_id', string="Quality Checks")

    qc_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='QC State', default='not_required', compute='_compute_qc_state', store=True)

    show_qc_button = fields.Boolean(
        string="Show QC Button",
        compute="_compute_show_qc_button",
        store=False
    )

    @api.depends('state')
    def _compute_show_qc_button(self):
        """Show button only when MO is done (completed)."""
        for rec in self:
            rec.show_qc_button = rec.state == 'done'

    @api.depends('quality_check_ids.status')
    def _compute_qc_state(self):
        """Compute QC state based on related QC records."""
        for rec in self:
            qcs = rec.quality_check_ids
            if not qcs:
                rec.qc_state = 'not_required'
            elif any(q.status == 'failed' for q in qcs):
                rec.qc_state = 'failed'
            elif any(q.status == 'pending' for q in qcs):
                rec.qc_state = 'pending'
            else:
                rec.qc_state = 'passed'

    quality_check_ids = fields.One2many(
        'dw.quality.check', 'mrp_id', string="Quality Checks"
    )

    def action_send_for_qc(self):
        """Triggered when MO is completed and sent for QC."""
        for mo in self:
            _logger.info("========== QC TRIGGERED FOR MO ==========")
            _logger.info(f"MO ID: {mo.id}, Name: {mo.name}, State: {mo.state}")
            _logger.info(f"Product: {mo.product_id.display_name}, Qty: {mo.product_qty}")

            if mo.state != 'done':
                raise UserError('You can only send completed Manufacturing Orders for Quality Check.')

            if not mo.product_id:
                raise UserError("No product found on this Manufacturing Order to perform Quality Check.")

            # ✅ Step 1: Try to find related stock picking
            finished_picking = False

            # First, check for pickings via finished move lines
            finished_picking = mo.move_finished_ids.move_line_ids.picking_id
            if finished_picking:
                finished_picking = finished_picking[0]
                _logger.info(f"Found picking via finished moves: {finished_picking.name}")
            else:
                _logger.warning(f"No picking found in finished moves for MO {mo.name}")

            # Fallback → check any pickings via raw move lines (consumed materials)
            if not finished_picking:
                raw_picking = mo.move_raw_ids.move_line_ids.picking_id
                if raw_picking:
                    finished_picking = raw_picking[0]
                    _logger.info(f"Found picking via raw moves: {finished_picking.name}")
                else:
                    _logger.warning(f"No raw move picking found for MO {mo.name}")

            # Last fallback → pick from linked picking_ids if any
            if not finished_picking and mo.picking_ids:
                finished_picking = mo.picking_ids.filtered(
                    lambda p: p.picking_type_id.code in ['outgoing', 'internal', 'mrp_operation']
                )[:1]
                if finished_picking:
                    finished_picking = finished_picking[0]
                    _logger.info(f"Found picking via mo.picking_ids: {finished_picking.name}")
                else:
                    _logger.warning(f"No picking found in mo.picking_ids for MO {mo.name}")

            # ✅ Step 2: Create QC record
            qc_vals = {
                'mrp_id': mo.id,
                'picking_id': finished_picking.id if finished_picking else False,
                'product_id': mo.product_id.id,
                'quantity': mo.product_qty,
                'remarks': f'QC initiated for Manufacturing Order {mo.name}',
            }

            _logger.info(f"Creating QC with values: {qc_vals}")
            qc = self.env['dw.quality.check'].create(qc_vals)
            _logger.info(f"Created QC Record: {qc.name}, ID: {qc.id}")

            # ✅ Step 3: Post chatter message
            mo.message_post(
                body=f"Quality Check {qc.name} created for Manufacturing Order {mo.name}.",
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )

            mo.qc_state = 'pending'
            _logger.info(f"QC State set to 'pending' for MO {mo.name}")

        # ✅ Step 4: Return proper view
        if self.env.user.has_group('dw_quality_check.group_quality_check'):
            _logger.info("Current user is QC Team → opening QC tree/form view.")
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quality Checks',
                'res_model': 'dw.quality.check',
                'view_mode': 'tree,form',
                'domain': [('mrp_id', '=', self.id)],
                'target': 'current',
            }
        else:
            _logger.info("Current user is NOT QC Team → showing rainbow animation.")
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Quality Check has been sent to QC team.',
                    'type': 'rainbow_man',
                }
            }
