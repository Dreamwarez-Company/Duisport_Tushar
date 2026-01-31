# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import date

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class TrialBalanceReport(models.TransientModel):
    _name = 'trial.balance.report'
    _description = 'Trial Balance Report'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    line_ids = fields.One2many('trial.balance.line', 'report_id', string='Lines')

    def action_view_report(self):
        """Fetch and display report data"""
        self.line_ids.unlink()
        
        accounts = self.env['account.account'].search([], order='code')
        lines_to_create = []
        
        for acc in accounts:
            # Opening balance
            ob_domain = [
                ('account_id', '=', acc.id),
                ('date', '<', self.start_date),
                ('parent_state', '=', 'posted')
            ]
            ob_lines = self.env['account.move.line'].search(ob_domain)
            opening = sum([l.debit - l.credit for l in ob_lines])
            
            # Period movements
            period_domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
                ('parent_state', '=', 'posted')
            ]
            period_lines = self.env['account.move.line'].search(period_domain)
            debit = sum([l.debit for l in period_lines])
            credit = sum([l.credit for l in period_lines])
            closing = opening + debit - credit
            
            lines_to_create.append({
                'report_id': self.id,
                'account_code': acc.code or '',
                'account_name': acc.name,
                'opening_balance': opening,
                'debit': debit,
                'credit': credit,
                'closing_balance': closing,
            })
        
        self.env['trial.balance.line'].create(lines_to_create)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'trial.balance.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_download_xlsx(self):
        """Download Excel report"""
        if xlsxwriter is None:
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))
        
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Trial Balance')
        
        # Headers
        headers = ['Account Code', 'Account Name', 'Opening Balance', 'Debit', 'Credit', 'Closing Balance']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)

        # Data
        accounts = self.env['account.account'].search([], order='code')
        row = 1
        for acc in accounts:
            ob_domain = [
                ('account_id', '=', acc.id),
                ('date', '<', self.start_date),
                ('parent_state', '=', 'posted')
            ]
            ob_lines = self.env['account.move.line'].search(ob_domain)
            opening = sum([l.debit - l.credit for l in ob_lines])
            
            period_domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
                ('parent_state', '=', 'posted')
            ]
            period_lines = self.env['account.move.line'].search(period_domain)
            debit = sum([l.debit for l in period_lines])
            credit = sum([l.credit for l in period_lines])
            closing = opening + debit - credit
            
            sheet.write(row, 0, acc.code or '')
            sheet.write(row, 1, acc.name)
            sheet.write(row, 2, float(opening))
            sheet.write(row, 3, float(debit))
            sheet.write(row, 4, float(credit))
            sheet.write(row, 5, float(closing))
            row += 1

        workbook.close()
        
        attachment = self.env['ir.attachment'].create({
            'name': f'trial_balance_{self.start_date}_{self.end_date}.xlsx',
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_pdf(self):
        """Download PDF report"""
        return self.env.ref('all_reports_full.report_trial_balance_pdf').report_action(self)

    def get_report_data(self):
        """Get data for PDF report"""
        accounts = self.env['account.account'].search([], order='code')
        data = []
        for acc in accounts:
            ob_domain = [
                ('account_id', '=', acc.id),
                ('date', '<', self.start_date),
                ('parent_state', '=', 'posted')
            ]
            ob_lines = self.env['account.move.line'].search(ob_domain)
            opening = sum([l.debit - l.credit for l in ob_lines])
            
            period_domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', self.start_date),
                ('date', '<=', self.end_date),
                ('parent_state', '=', 'posted')
            ]
            period_lines = self.env['account.move.line'].search(period_domain)
            debit = sum([l.debit for l in period_lines])
            credit = sum([l.credit for l in period_lines])
            closing = opening + debit - credit
            
            data.append({
                'account': acc,
                'opening': opening,
                'debit': debit,
                'credit': credit,
                'closing': closing
            })
        return data


class TrialBalanceLine(models.TransientModel):
    _name = 'trial.balance.line'
    _description = 'Trial Balance Line'

    report_id = fields.Many2one('trial.balance.report', string='Report', ondelete='cascade')
    account_code = fields.Char(string='Account Code')
    account_name = fields.Char(string='Account Name')
    opening_balance = fields.Float(string='Opening Balance')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    closing_balance = fields.Float(string='Closing Balance')