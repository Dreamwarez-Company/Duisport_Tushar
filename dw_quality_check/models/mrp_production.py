from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

# ✅ Define logger for this file
_logger = logging.getLogger(__name__)

class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    quality_check_ids = fields.One2many('dw.quality.check', 'mrp_id', string="Quality Checks")
    show_qc_button = fields.Boolean(string="Show QC Button", default=True)

    qc_state = fields.Selection([
        ('not_required', 'Not Required'),
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='QC State', default='not_required', compute='_compute_qc_state', store=True)

    show_qc_button = fields.Boolean(
        string="Show QC Button",
        compute="_compute_show_qc_button",
        store=True
    )

    @api.depends('state', 'qc_state')
    def _compute_show_qc_button(self):
        """Show QC button only when MO is completed and QC not yet initiated."""
        for rec in self:
            rec.show_qc_button = (
                rec.state == 'done' and
                rec.qc_state == 'not_required'
            )

    def action_send_for_qc(self):
        """Triggered when MO is completed and sent for QC."""
        for mo in self:
            _logger.info("========== QC TRIGGERED FOR MO ==========")
            _logger.info(f"MO ID: {mo.id}, Name: {mo.name}, State: {mo.state}")

            if mo.state != 'done':
                raise UserError('You can only send completed Manufacturing Orders for Quality Check.')

            # -------------------------------------------
            # 1️⃣ CREATE QC RECORD (no picking required)
            # -------------------------------------------
            qc_vals = {
                'mrp_id': mo.id,
                'product_id': mo.product_id.id,
                'quantity': mo.product_qty,
                'remarks': f'QC initiated for Manufacturing Order {mo.name}',
            }

            qc = self.env['dw.quality.check'].create(qc_vals)
            _logger.info(f"Created QC Record: {qc.id}")

            mo.message_post(
                body=f"Quality Check {qc.name} created for Manufacturing Order {mo.name}.",
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )

            mo.qc_state = 'pending'
            mo.show_qc_button = False

            # -------------------------------------------
            # 2️⃣ DEPARTMENT TIME TRACKING (MO → QC Initiated)
            # -------------------------------------------
            _logger.info("---- TIME TRACKING (MO QC Initiated) ----")

            # Close previous MO stage (in progress)
            last_track = self.env['department.time.tracking'].search(
                [
                    ('target_model', '=', f'mrp.production,{mo.id}'),
                    ('status', '=', 'in_progress')
                ],
                limit=1,
                order='start_time desc'
            )

            if last_track:
                last_track.write({
                    'end_time': fields.Datetime.now(),
                    'status': 'done'
                })
                _logger.info(f"Closed previous stage: {last_track.stage_name}")

            # Create QC Initiated stage
            self.env['department.time.tracking'].create({
                'target_model': f'mrp.production,{mo.id}',
                'stage_name': 'QC Initiated',
                'user_id': self.env.user.id,
                'employee_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                'start_time': fields.Datetime.now(),
                'status': 'in_progress',
                'lead_id': mo.sale_order_id.opportunity_id.id 
                    if hasattr(mo, 'sale_order_id') and mo.sale_order_id.opportunity_id 
                    else False,
            })

            _logger.info("Created stage: QC Initiated")

        # -------------------------------------------
        # 3️⃣ Return view for QC team
        # -------------------------------------------
        if self.env.user.has_group('dw_quality_check.group_quality_check'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quality Checks',
                'res_model': 'dw.quality.check',
                'view_mode': 'tree,form',
                'domain': [('mrp_id', '=', self.id)],
                'target': 'current',
            }
        else:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Quality Check has been sent to QC team.',
                    'type': 'rainbow_man',
                }
            }

    def action_send_for_qc(self):
        """Triggered when MO is completed and sent for QC."""
        for mo in self:
            _logger.info("========== QC TRIGGERED FOR MO ==========")
            _logger.info(f"MO ID: {mo.id}, Name: {mo.name}, State: {mo.state}")

            if mo.state != 'done':
                raise UserError('You can only send completed Manufacturing Orders for Quality Check.')

            # -------------------------------------------------------
            # 1️⃣ CREATE QC RECORD (directly linked to MO)
            # -------------------------------------------------------
            qc_vals = {
                'mrp_id': mo.id,
                'product_id': mo.product_id.id,
                'quantity': mo.product_qty,
                'remarks': f'QC initiated for Manufacturing Order {mo.name}',
            }

            qc = self.env['dw.quality.check'].create(qc_vals)
            _logger.info(f"Created QC Record: {qc.id}")

            mo.message_post(
                body=f"Quality Check {qc.name} created for Manufacturing Order {mo.name}.",
                message_type="comment",
                subtype_xmlid="mail.mt_comment"
            )

            mo.qc_state = 'pending'
            mo.show_qc_button = False

            # -------------------------------------------------------
            # 2️⃣ DEPARTMENT TIME TRACKING — QC INITIATED FOR MO
            # -------------------------------------------------------
            _logger.info("---- TIME TRACKING (MO QC Initiated) ----")

            # Correct Sale Order detection
            sale_order = self.env["sale.order"].search([
                ("name", "=", mo.origin)
            ], limit=1)

            # 2.1 Close last MO stage which is still in progress
            last_track = self.env["department.time.tracking"].search(
                [
                    ("target_model", "=", f"mrp.production,{mo.id}"),
                    ("status", "=", "in_progress"),
                ],
                limit=1,
                order="start_time desc"
            )

            if last_track:
                last_track.write({
                    "end_time": fields.Datetime.now(),
                    "status": "done"
                })
                _logger.info(f"Closed previous stage: {last_track.stage_name}")
            else:
                _logger.warning("No previous MO stage found to close!")

            # 2.2 Create QC Initiated stage for MO
            new_track = self.env["department.time.tracking"].create({
                "target_model": f"mrp.production,{mo.id}",
                "stage_name": "QC Initiated",
                "user_id": self.env.user.id,
                "employee_id": self.env.user.employee_id.id if self.env.user.employee_id else False,
                "start_time": fields.Datetime.now(),
                "status": "in_progress",
                "lead_id": sale_order.opportunity_id.id if sale_order and sale_order.opportunity_id else False,
            })

            _logger.info(f"Created stage: QC Initiated for MO {mo.name} (Track ID: {new_track.id})")

        # -------------------------------------------------------
        # 3️⃣ Return view for QC team
        # -------------------------------------------------------
        if self.env.user.has_group('dw_quality_check.group_quality_check'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Quality Checks',
                'res_model': 'dw.quality.check',
                'view_mode': 'tree,form',
                'domain': [('mrp_id', '=', self.id)],
                'target': 'current',
            }
        else:
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': 'Quality Check has been sent to QC team.',
                    'type': 'rainbow_man',
                }
            }
