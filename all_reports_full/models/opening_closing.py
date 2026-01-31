# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
import io, base64

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None


class OpeningClosingWizard(models.TransientModel):
    _name = "opening.closing.report.wizard"
    _description = "Opening & Closing Balance Report Wizard"

    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    report_format = fields.Selection([
        ('xlsx', 'Excel'),
        ('pdf', 'PDF')
    ], default='xlsx', required=True)

    # -----------------------------
    #  EXPORT ACTION
    # -----------------------------
    def action_export(self):
        if self.report_format == "xlsx":
            return self._export_xlsx()

        if self.report_format == "pdf":
            return self.env.ref("all_reports_full.opening_closing_pdf").report_action(self)

    # -----------------------------
    #  CALCULATE BALANCES
    # -----------------------------
    def _get_balance_data(self):
        start = self.start_date
        end = self.end_date

        accounts = self.env['account.account'].search([], order='code')
        result = []

        for acc in accounts:
            # Opening
            ob_domain = [
                ('account_id', '=', acc.id),
                ('date', '<', start),
                ('parent_state', '=', 'posted')
            ]
            opening = sum(self.env['account.move.line'].search(ob_domain).mapped(lambda l: l.debit - l.credit))

            # Period Movement
            pr_domain = [
                ('account_id', '=', acc.id),
                ('date', '>=', start),
                ('date', '<=', end),
                ('parent_state', '=', 'posted')
            ]
            lines = self.env['account.move.line'].search(pr_domain)
            debit = sum(lines.mapped('debit'))
            credit = sum(lines.mapped('credit'))

            closing = opening + debit - credit

            result.append({
                'account': acc,
                'opening': opening,
                'debit': debit,
                'credit': credit,
                'closing': closing
            })

        return result

    # -----------------------------
    #  EXCEL EXPORT
    # -----------------------------
    def _export_xlsx(self):
        if xlsxwriter is None:
            raise UserError("xlsxwriter missing!")

        stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Opening-Closing')

        headers = ["Account Code", "Account Name", "Opening", "Debit", "Credit", "Closing"]
        for col, h in enumerate(headers):
            sheet.write(0, col, h)

        row = 1
        data = self._get_balance_data()

        for item in data:
            sheet.write(row, 0, item['account'].code or '')
            sheet.write(row, 1, item['account'].name)
            sheet.write(row, 2, item['opening'])
            sheet.write(row, 3, item['debit'])
            sheet.write(row, 4, item['credit'])
            sheet.write(row, 5, item['closing'])
            row += 1

        workbook.close()

        attachment = self.env['ir.attachment'].create({
            'name': f"opening_closing_{self.start_date}_{self.end_date}.xlsx",
            'type': 'binary',
            'datas': base64.b64encode(stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': f"/web/content/{attachment.id}?download=true"
        }
