# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


# --------------------------------------------------
# CRM Lead Product Line
# --------------------------------------------------
class CrmLeadProductLine(models.Model):
    _name = 'crm.lead.product.line'
    _description = 'CRM Lead Product Line'

    lead_id = fields.Many2one('crm.lead', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        store=True
    )
    quantity = fields.Float(default=1.0)
    unit_price = fields.Float(compute='_compute_unit_price', store=True)

    @api.depends('product_id')
    def _compute_unit_price(self):
        for rec in self:
            rec.unit_price = rec.product_id.lst_price or 0.0


# --------------------------------------------------
# Engineering Product Line
# --------------------------------------------------
class EngineeringProductLine(models.Model):
    _name = 'engineering.team.product'
    _description = 'Engineering Team Product Line'

    engineering_id = fields.Many2one(
        'engineering.team',
        ondelete='cascade',
        required=True
    )
    product_id = fields.Many2one('product.product', required=True)
    product_tmpl_id = fields.Many2one(
        'product.template',
        related='product_id.product_tmpl_id',
        store=True
    )
    quantity = fields.Float(default=1.0)
    cost_price = fields.Float(string="Unit Price")
    cost_price_m = fields.Float(string="Unit Price Mgnt")

    total_price = fields.Float(
        compute='_compute_total_price',
        store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id_set_price(self):
        for rec in self:
            if rec.product_id and not rec.cost_price:
                rec.cost_price = rec.product_id.lst_price or 0.0

    @api.depends('quantity', 'cost_price')
    def _compute_total_price(self):
        for rec in self:
            rec.total_price = rec.quantity * rec.cost_price

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.engineering_id:
                line.engineering_id._recompute_bom_exploded_lines()
        return res

    def name_get(self):
        result = []
        for rec in self:
            name = rec.product_id.display_name if rec.product_id else ''
            result.append((rec.id, name))
        return result
    
# --------------------------------------------------
# Engineering Team
# --------------------------------------------------
class EngineeringTeam(models.Model):
    _name = 'engineering.team'
    _description = 'Engineering Team Analysis'
    _rec_name = 'lead_id'

    # --------------------------------------------------
    # BASIC
    # --------------------------------------------------
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        readonly=True
    )

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    partner_id = fields.Many2one(
        'res.partner',
        related='lead_id.partner_id',
        store=True,
        readonly=True
    )

    # --------------------------------------------------
    # ENGINEERING DETAILS
    # --------------------------------------------------
    design_ref = fields.Binary("Design Reference")
    design_ref_filename = fields.Char()
    estimation_time = fields.Float("Estimation Time (Days)")
    engineering_notes = fields.Text()

    # --------------------------------------------------
    # PRODUCTS
    # --------------------------------------------------
    product_line_ids = fields.One2many(
        'engineering.team.product',
        'engineering_id'
    )

    # --------------------------------------------------
    # BOM
    # --------------------------------------------------
    bom_ids = fields.Many2many(
        'mrp.bom',
        'engineering_team_bom_rel',
        'engineering_id',
        'bom_id',
        string='Bill of Materials'
    )

    bom_exploded_line_ids = fields.One2many(
        'engineering.team.bom.line',
        'engineering_id'
    )

    # --------------------------------------------------
    #  CREATE FROM CRM METHOD (FIXED)
    # --------------------------------------------------
    @api.model
    def create_from_crm(self, crm_lead):
        """Create Engineering Team record from CRM Lead"""
        # Check if engineering record already exists for this lead
        existing = self.search([('lead_id', '=', crm_lead.id)])
        if existing:
            raise UserError(_("Engineering analysis already exists for this lead!"))
        
        # Create the engineering team record
        eng_record = self.create({
            'lead_id': crm_lead.id,
            'state': 'draft',
            'engineer_id': self.env.user.id,
        })
        
        # Copy product lines from CRM to engineering
        if crm_lead.product_line_ids:
            for line in crm_lead.product_line_ids:
                self.env['engineering.team.product'].create({
                    'engineering_id': eng_record.id,
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'cost_price': line.unit_price or line.product_id.lst_price or 0.0,
                })
        
        # Update CRM lead's engineering team field
        crm_lead.write({
            'engineering_team_id': self.env.user.id
        })
        
        return eng_record

    # --------------------------------------------------
    #  SIMPLIFIED BoM Explosion Logic (More Reliable)
    # --------------------------------------------------
    def _recompute_bom_exploded_lines(self):
        """Recompute exploded BOM lines based on selected BOMs and product quantities"""
        for rec in self:
            # Clear existing lines
            rec.bom_exploded_line_ids.unlink()
            
            if not rec.product_line_ids:
                continue

            # Process each product line
            for prod_line in rec.product_line_ids:
                if not prod_line.product_id:
                    continue
                
                product = prod_line.product_id
                product_qty = prod_line.quantity
                
                # Get BOMs for this product
                boms_to_use = self.env['mrp.bom']
                
                if rec.bom_ids:
                    # Filter BOMs that match this product
                    boms_to_use = rec.bom_ids.filtered(
                        lambda b: (
                            (b.product_id and b.product_id == product) or
                            (not b.product_id and b.product_tmpl_id == product.product_tmpl_id)
                        )
                    )
                else:
                    # Find default BOM for the product
                    bom = self.env['mrp.bom']._bom_find(
                        product=product,
                        company_id=rec.company_id.id
                    )
                    if bom:
                        boms_to_use = bom

                if not boms_to_use:
                    continue

                # Process each BOM (use simple approach for reliability)
                for bom in boms_to_use:
                    for bom_line in bom.bom_line_ids:
                        if bom_line.product_id:
                            self.env['engineering.team.bom.line'].create({
                                'engineering_id': rec.id,
                                'engineering_product_line_id': prod_line.id,
                                'bom_id': bom.id,
                                'component_id': bom_line.product_id.id,
                                'bom_qty': bom_line.product_qty,
                                'engineering_qty': product_qty,
                            })

    # --------------------------------------------------
    # AUTO TRIGGERS
    # --------------------------------------------------
    def write(self, vals):
        res = super().write(vals)
        if 'product_line_ids' in vals or 'bom_ids' in vals:
            self._recompute_bom_exploded_lines()
        return res

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._recompute_bom_exploded_lines()
        return rec

    # --------------------------------------------------
    # WORKFLOW
    # --------------------------------------------------
    state = fields.Selection(
        [('draft', 'New'), ('done', 'Analysis Done')],
        default='draft'
    )
    engineer_id = fields.Many2one(
        'res.users',
        default=lambda self: self.env.user
    )
    date_done = fields.Datetime(readonly=True)

    def action_analysis_done(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError(_("Analysis already done"))

            rec.state = 'done'
            rec.date_done = fields.Datetime.now()

            if rec.lead_id:
                # Update CRM lead stage to "Analysis Done"
                stage = self.env['crm.stage'].search(
                    [('name', '=', 'Analysis Done')], limit=1
                )
                if not stage:
                    stage = self.env['crm.stage'].create({'name': 'Analysis Done'})
                rec.lead_id.stage_id = stage.id

                # Post message to CRM lead
                rec.lead_id.message_post(
                    body=_("Engineering analysis completed by <b>%s</b>") % self.env.user.name,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note"
                )
                
                # Also call CRM's action_analysis_done to ensure consistency
                rec.lead_id.action_analysis_done()