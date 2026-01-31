# -*- coding: utf-8 -*-
from odoo import models, fields, api


class EngineeringTeamBomLine(models.Model):
    _name = 'engineering.team.bom.line'
    _description = 'Engineering BoM Explosion Line'
    _order = 'component_id'
    # _order = 'engineering_product_line_id, component_id'

    engineering_id = fields.Many2one(
        'engineering.team',
        string='Engineering',
        ondelete='cascade',
        required=True
    )

    engineering_product_line_id = fields.Many2one(
        'engineering.team.product',
        string='',  # EMPTY STRING - This removes the field label
        ondelete='cascade'
    )
    
    # Computed field to show only product name
    main_product_display = fields.Char(
        string='Engineering Product',
        compute='_compute_main_product_display',
        store=True,
        readonly=True
    )

    bom_id = fields.Many2one(
        'mrp.bom',
        string='BoM',
        readonly=True
    )

    component_id = fields.Many2one(
        'product.product',
        string='Component',
        readonly=True,
        required=True
    )

    bom_qty = fields.Float(
        string='BoM Qty',
        readonly=True
    )

    engineering_qty = fields.Float(
        string='Engineering Qty',
        readonly=True
    )

    total_required_qty = fields.Float(
        string='Total Required Qty',
        compute='_compute_total_required_qty',
        store=True,
        readonly=True
    )

    component_unit_price = fields.Float(
        string='Unit Price',
        compute='_compute_component_price',
        store=True,
        readonly=True
    )

    component_total_price = fields.Float(
        string='Total Price',
        compute='_compute_component_price',
        store=True,
        readonly=True
    )

    @api.depends('engineering_product_line_id')
    def _compute_main_product_display(self):
        for rec in self:
            if rec.engineering_product_line_id and rec.engineering_product_line_id.product_id:
                product = rec.engineering_product_line_id.product_id
                # Set the display name of the main product
                rec.main_product_display = product.display_name
            else:
                rec.main_product_display = False

    @api.depends('bom_qty', 'engineering_qty')
    def _compute_total_required_qty(self):
        for rec in self:
            rec.total_required_qty = (rec.bom_qty or 0.0) * (rec.engineering_qty or 0.0)

    @api.depends('component_id', 'total_required_qty')
    def _compute_component_price(self):
        for rec in self:
            unit_price = rec.component_id.standard_price or 0.0
            rec.component_unit_price = unit_price
            rec.component_total_price = unit_price * (rec.total_required_qty or 0.0)