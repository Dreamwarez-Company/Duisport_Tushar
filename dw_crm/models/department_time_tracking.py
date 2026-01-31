from odoo import models, fields, api
from datetime import datetime
from odoo.fields import Datetime as OdooDatetime
import pytz

class DepartmentTimeTracking(models.Model):
    _name = 'department.time.tracking'
    _description = 'Department Time Tracking for CRM'

    # Link to CRM Lead (for now)
    target_model = fields.Reference(selection=[('crm.lead', 'CRM Lead')], string='Target')


    stage_name = fields.Char("Stage / State")

    user_id = fields.Many2one(
        'res.users', string="Responsible User", default=lambda self: self.env.user
    )
    employee_id = fields.Many2one('hr.employee', string="Responsible Employee")

    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    total_duration = fields.Char(string='Total Duration', compute='_compute_total_duration', store=True)
    lead_id = fields.Many2one('crm.lead', string="Lead")


    status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='in_progress')
    
    @api.depends('start_time', 'end_time')
    def _compute_total_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                days = delta.days
                hours = delta.seconds // 3600
                minutes = (delta.seconds % 3600) // 60

                # Format text cleanly depending on the duration
                parts = []
                if days:
                    parts.append(f"{days} day{'s' if days > 1 else ''}")
                if hours:
                    parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
                if minutes:
                    parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")

                rec.total_duration = ", ".join(parts) if parts else "Less than a minute"
            else:
                rec.total_duration = "-"

