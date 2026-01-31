from odoo import models, fields, api

class CrmLeadTime(models.Model):
    _name = 'crm.lead.time'
    _description = 'Time spent by Department on Lead'

    lead_id = fields.Many2one('crm.lead', string='Lead', required=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    employee_id = fields.Many2one('hr.employee', string='Employee')
    start_time = fields.Datetime(string='Start Time', default=fields.Datetime.now)
    end_time = fields.Datetime(string='End Time')
    duration = fields.Float(string='Duration (hours)', compute='_compute_duration', store=True)
    status = fields.Selection([
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], string='Status', default='pending')

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for rec in self:
            if rec.start_time and rec.end_time:
                delta = rec.end_time - rec.start_time
                rec.duration = delta.total_seconds() / 3600
            else:
                rec.duration = 0
