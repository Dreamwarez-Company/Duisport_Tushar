# -*- coding: utf-8 -*-
from odoo import models, fields, api
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)

class SlowMovingWizard(models.TransientModel):
    _name = 'slow.moving.wizard'
    _description = 'Slow / Non-Moving Inventory Report'

    slow_days = fields.Integer(string="Slow Moving After (Days)", default=30, required=True)
    non_moving_days = fields.Integer(string="Non-Moving After (Days)", default=90, required=True)

    # NEW FIELDS ADDED
    location_id = fields.Many2one('stock.location', string="Location", 
                                  domain="[('usage', '=', 'internal')]")
    product_category_id = fields.Many2one('product.category', string="Product Category")
    product_id = fields.Many2one('product.product', string="Specific Product")
    
    show_age_buckets = fields.Boolean(string="Show Age Buckets", default=True)
    
    # Action plan thresholds
    threshold_15_days = fields.Integer(string="15 Days Threshold", default=15)
    threshold_30_days = fields.Integer(string="30 Days Threshold", default=30)
    threshold_60_days = fields.Integer(string="60 Days Threshold", default=60)
    threshold_120_days = fields.Integer(string="120 Days Threshold", default=120)
    threshold_180_days = fields.Integer(string="180 Days Threshold", default=180)

    def action_print_report(self):
        return self.env.ref('dw_customer_credit.action_report_slow_nonmoving').report_action(self)

# # -*- coding: utf-8 -*-
# from odoo import models, fields, api
# from datetime import datetime
# import logging

# _logger = logging.getLogger(__name__)

# class SlowMovingWizard(models.TransientModel):
#     _name = 'slow.moving.wizard'
#     _description = 'Slow / Non-Moving Inventory Report'

#     slow_days = fields.Integer(string="Slow Moving After (Days)", default=30, required=True)
#     non_moving_days = fields.Integer(string="Non-Moving After (Days)", default=90, required=True)

#     def action_print_report(self):
#         return self.env.ref('dw_customer_credit.action_report_slow_nonmoving').report_action(self)