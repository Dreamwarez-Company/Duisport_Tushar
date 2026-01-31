from odoo import models, fields, api
from odoo.exceptions import UserError

class DwQualityCheck(models.Model):
    _name = 'dw.quality.check'
    _description = 'Quality Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ----------------------------------------------------------
    # Basic Info
    # ----------------------------------------------------------
    name = fields.Char(string='QC Reference', required=True, copy=False, default='New')
    picking_id = fields.Many2one('stock.picking', string='Picking', ondelete='cascade', index=True)
    product_id = fields.Many2one('product.product', string='Product')
    mrp_id = fields.Many2one('mrp.production', string="Manufacturing Order")
    lot_id = fields.Many2one('stock.production.lot', string='Lot/Serial')
    quantity = fields.Float(string='Quantity')
    passed = fields.Boolean(string='Passed')
    remarks = fields.Text(string='Remarks')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    inspected_by = fields.Many2one('res.users', string='Inspected By', default=lambda self: self.env.user)

    source_reference = fields.Char(
        string='Source Reference',
        compute='_compute_source_reference',
        store=True,
        readonly=True
    )

    # ----------------------------------------------------------
    # QC Status Fields
    # ----------------------------------------------------------
    status = fields.Selection([
        ('pending', 'Pending'),
        ('passed', 'Passed'),
        ('failed', 'Failed')
    ], string='QC Result', default='pending', tracking=True)

    qc_status = fields.Selection([
        ('received', 'Received for QC'),
        ('returned', 'Returned'),
        ('done', 'QC Done')
    ], string="QC Process Status", default='received', tracking=True)

    # ----------------------------------------------------------
    # Compute
    # ----------------------------------------------------------
    @api.depends('mrp_id', 'picking_id')
    def _compute_source_reference(self):
        """Show source reference from MO or PO."""
        for rec in self:
            if rec.mrp_id:
                rec.source_reference = rec.mrp_id.origin or rec.mrp_id.name
            elif rec.picking_id:
                rec.source_reference = rec.picking_id.origin or rec.picking_id.name
            else:
                rec.source_reference = False

    # ----------------------------------------------------------
    # QC Actions
    # ----------------------------------------------------------
    # def action_qc_done(self):
    #     """Mark QC as Done and update delivery order."""
    #     for rec in self:
    #         rec.qc_status = 'done'
    #         rec.message_post(body=f"✅ Quality Check marked as Done by {self.env.user.name}")
    #         rec._update_picking_qc_state()

    # def action_qc_done(self):
    #     for rec in self:

    #         # ---------------------------
    #         #  CASE 1: QC FOR MRP
    #         # ---------------------------
    #         if rec.mrp_id:
    #             # No picking required for MO QC
    #             rec.qc_status = "done"
    #             rec.status = "passed" if rec.passed else "failed"

    #             rec.message_post(
    #                 body=f"✅ QC Done for Manufacturing Order {rec.mrp_id.name} "
    #                     f"by {self.env.user.name}"
    #             )

    #             # You may want to update MO state or timeline here later
    #             return True

    #         # ---------------------------
    #         #  CASE 2: QC FOR PURCHASE (existing logic)
    #         # ---------------------------
    #         picking = rec.picking_id
    #         if not picking:
    #             raise UserError("No picking linked for QC.")

    #         purchase_orders = picking.move_ids_without_package.mapped(
    #             "purchase_line_id.order_id"
    #         )
    #         purchase_order = purchase_orders[:1]

    #         if not purchase_order:
    #             raise UserError("No Purchase Order found for this QC action.")

    #         sale_order = self.env["sale.order"].search(
    #             [("name", "=", purchase_order.origin)], limit=1
    #         )

    #         lead_id = (
    #             sale_order.opportunity_id.id
    #             if sale_order and sale_order.opportunity_id
    #             else False
    #         )

    #         # --------------------------------------------
    #         # Close QC Initiated
    #         # --------------------------------------------
    #         last_qc_initiated = self.env["department.time.tracking"].search([
    #             ("target_model", "=", f"purchase.order,{purchase_order.id}"),
    #             ("stage_name", "=", "QC Initiated"),
    #             ("status", "=", "in_progress")
    #         ], limit=1, order="start_time desc")

    #         if last_qc_initiated:
    #             last_qc_initiated.write({
    #                 "end_time": fields.Datetime.now(),
    #                 "status": "done"
    #             })

    #         # --------------------------------------------
    #         # Close previous QC Done
    #         # --------------------------------------------
    #         last_qc_done = self.env["department.time.tracking"].search([
    #             ("target_model", "=", f"purchase.order,{purchase_order.id}"),
    #             ("stage_name", "=", "QC Done"),
    #             ("status", "=", "in_progress")
    #         ], limit=1, order="start_time desc")

    #         if last_qc_done:
    #             last_qc_done.write({
    #                 "end_time": fields.Datetime.now(),
    #                 "status": "done"
    #             })

    #         # --------------------------------------------
    #         # Create QC DONE timeline entry
    #         # --------------------------------------------
    #         self.env["department.time.tracking"].create({
    #             "target_model": f"purchase.order,{purchase_order.id}",
    #             "stage_name": "QC Done",
    #             "user_id": self.env.user.id,
    #             "employee_id": (
    #                 self.env.user.employee_id.id
    #                 if self.env.user.employee_id else False
    #             ),
    #             "start_time": fields.Datetime.now(),
    #             "status": "done",
    #             "end_time": fields.Datetime.now(),
    #             "lead_id": lead_id,
    #         })

    #         rec.qc_status = "done"
    #         rec.message_post(body=f"QC Done by {self.env.user.name}")
    #         rec._update_picking_qc_state()

    #     return True

    def action_qc_done(self):
        for rec in self:

            # =====================================================
            # 🔵 CASE 1: QC → MRP (Manufacturing Order QC Flow)
            # =====================================================
            if rec.mrp_id:
                mo = rec.mrp_id

                rec.qc_status = "done"
                rec.status = "passed" if rec.passed else "failed"

                rec.message_post(
                    body=f"✅ QC Done for Manufacturing Order {mo.name} by {self.env.user.name}"
                )

                # ------------------------------------------------
                # 1️⃣ Identify Sale Order linked to MO
                # ------------------------------------------------
                sale_order = self.env["sale.order"].search([
                    ("name", "=", mo.origin)
                ], limit=1)

                lead_id = (
                    sale_order.opportunity_id.id
                    if sale_order and sale_order.opportunity_id
                    else False
                )

                # ------------------------------------------------
                # 2️⃣ CLOSE “QC Initiated” stage for MO
                # ------------------------------------------------
                last_qc_initiated = self.env["department.time.tracking"].search([
                    ("target_model", "=", f"mrp.production,{mo.id}"),
                    ("stage_name", "=", "QC Initiated"),
                    ("status", "=", "in_progress")
                ], limit=1, order="start_time desc")

                if last_qc_initiated:
                    last_qc_initiated.write({
                        "end_time": fields.Datetime.now(),
                        "status": "done"
                    })

                # ------------------------------------------------
                # 3️⃣ Close any previous QC Done (prevent duplicate)
                # ------------------------------------------------
                last_qc_done = self.env["department.time.tracking"].search([
                    ("target_model", "=", f"mrp.production,{mo.id}"),
                    ("stage_name", "=", "QC Done"),
                    ("status", "=", "in_progress")
                ], limit=1, order="start_time desc")

                if last_qc_done:
                    last_qc_done.write({
                        "end_time": fields.Datetime.now(),
                        "status": "done"
                    })

                # ------------------------------------------------
                # 4️⃣ CREATE NEW “QC Done” STAGE FOR MRP
                # ------------------------------------------------
                self.env["department.time.tracking"].create({
                    "target_model": f"mrp.production,{mo.id}",
                    "stage_name": "QC Done",
                    "user_id": self.env.user.id,
                    "employee_id": (
                        self.env.user.employee_id.id
                        if self.env.user.employee_id else False
                    ),
                    "start_time": fields.Datetime.now(),
                    "end_time": fields.Datetime.now(),
                    "status": "done",
                    "lead_id": lead_id,
                })

                return True  # MRP flow ends here

            # =====================================================
            # 🔴 CASE 2: QC → PURCHASE ORDER (Your existing logic)
            # =====================================================
            picking = rec.picking_id
            if not picking:
                raise UserError("No picking linked for QC.")

            purchase_orders = picking.move_ids_without_package.mapped(
                "purchase_line_id.order_id"
            )
            purchase_order = purchase_orders[:1]

            if not purchase_order:
                raise UserError("No Purchase Order found for this QC action.")

            sale_order = self.env["sale.order"].search(
                [("name", "=", purchase_order.origin)], limit=1
            )

            lead_id = (
                sale_order.opportunity_id.id
                if sale_order and sale_order.opportunity_id
                else False
            )

            # --------------------------------------------
            # CLOSE QC Initiated (PO)
            # --------------------------------------------
            last_qc_initiated = self.env["department.time.tracking"].search([
                ("target_model", "=", f"purchase.order,{purchase_order.id}"),
                ("stage_name", "=", "QC Initiated"),
                ("status", "=", "in_progress")
            ], limit=1, order="start_time desc")

            if last_qc_initiated:
                last_qc_initiated.write({
                    "end_time": fields.Datetime.now(),
                    "status": "done"
                })

            # --------------------------------------------
            # CLOSE previous QC Done (PO)
            # --------------------------------------------
            last_qc_done = self.env["department.time.tracking"].search([
                ("target_model", "=", f"purchase.order,{purchase_order.id}"),
                ("stage_name", "=", "QC Done"),
                ("status", "=", "in_progress")
            ], limit=1, order="start_time desc")

            if last_qc_done:
                last_qc_done.write({
                    "end_time": fields.Datetime.now(),
                    "status": "done"
                })

            # --------------------------------------------
            # CREATE QC Done (PO)
            # --------------------------------------------
            self.env["department.time.tracking"].create({
                "target_model": f"purchase.order,{purchase_order.id}",
                "stage_name": "QC Done",
                "user_id": self.env.user.id,
                "employee_id": (
                    self.env.user.employee_id.id
                    if self.env.user.employee_id else False
                ),
                "start_time": fields.Datetime.now(),
                "status": "done",
                "end_time": fields.Datetime.now(),
                "lead_id": lead_id,
            })

            rec.qc_status = "done"
            rec.message_post(body=f"QC Done by {self.env.user.name}")
            rec._update_picking_qc_state()

        return True



    def action_return_file(self):
        """Send item to Return Order QC picking type."""
        for rec in self:
            if not rec.picking_id:
                raise UserError("No related picking found to return.")

            rec.qc_status = 'returned'
            rec.message_post(body=f"QC {rec.name} marked as Returned by {self.env.user.name}")

            picking_type = self.env['stock.picking.type'].search([
                ('name', 'ilike', 'Return Order QC')
            ], limit=1)
            if not picking_type:
                raise UserError(
                    "No 'Return Order QC' operation type found. "
                    "Please create one under Inventory > Configuration > Operations Types."
                )

            return_picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'origin': f"Return for QC {rec.name}",
                'location_id': rec.picking_id.location_dest_id.id,
                'location_dest_id': rec.picking_id.location_id.id,
                'move_ids_without_package': [(0, 0, {
                    'name': f"Return {rec.product_id.display_name}",
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.quantity,
                    'product_uom': rec.product_id.uom_id.id,
                    'location_id': rec.picking_id.location_dest_id.id,
                    'location_dest_id': rec.picking_id.location_id.id,
                })]
            })

            return_picking.action_confirm()
            rec.message_post(body=f"Return Picking <b>{return_picking.name}</b> created under Return Order QC.")
        return True

    def action_set_passed(self):
        """Mark QC record as Passed."""
        for rec in self:
            rec.write({
                'status': 'passed',
                'qc_status': 'done',
            })
            rec._update_picking_qc_state()
            rec.message_post(body=f'✅ QC {rec.name} marked as Passed by {self.env.user.name}')

    def action_set_failed(self):
        """Mark QC record as Failed."""
        for rec in self:
            rec.write({
                'status': 'failed',
                'qc_status': 'done',
            })
            rec._update_picking_qc_state()
            rec.message_post(body=f'❌ QC {rec.name} marked as Failed by {self.env.user.name}')

    # ----------------------------------------------------------
    # ORM Overrides
    # ----------------------------------------------------------
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

    # ----------------------------------------------------------
    # Main Sync Logic
    # ----------------------------------------------------------
    def _update_picking_qc_state(self):
        """Sync Delivery Order QC fields based on QC process status."""
        for rec in self:
            if not rec.picking_id:
                continue

            qcs = self.search([('picking_id', '=', rec.picking_id.id)]) | self
            new_state = 'pending'
            qc_bool = False

            if any(q.status == 'failed' for q in qcs):
                new_state = 'failed'
                qc_bool = False
            elif all(q.qc_status == 'done' for q in qcs):
                new_state = 'passed'
                qc_bool = True

            rec.picking_id.sudo().write({
                'qc_state': new_state,
                'quality_check_passed': qc_bool,
            })
