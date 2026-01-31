# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import io, base64
from datetime import datetime, date, timedelta

try:
    import xlsxwriter
except Exception:
    xlsxwriter = None

class ReportCenter(models.Model):
    _name = 'report.center'
    _description = 'Report Center Link Model'

    name = fields.Char(string='Report Name', required=True)
    code = fields.Char(string='Code', help='Internal code to identify report')
    report_type = fields.Selection([('standard','Standard'),('custom','Custom')], default='standard')

class ReportExportWizard(models.TransientModel):
    _name = 'report.export.wizard'
    _description = 'Export report wizard'

    report_code = fields.Selection(selection=[
        ('general_ledger','General Ledger'),
        ('trial_balance','Trial Balance'),
        ('chart_of_accounts','Chart of Accounts'),
        ('customer_aging','Customer Outstanding Aging'),
        ('vendor_aging','Vendor Outstanding Aging'),
        ('inventory_valuation','Inventory Valuation'),
        ('stock_register','Stock Register'),
        ('gr_ir','GR/IR Report'),
    ], string='Report', required=True)
    start_date = fields.Date(string='Start Date')
    end_date = fields.Date(string='End Date')
    report_format = fields.Selection([
        ('xlsx', 'Excel'),
        ('pdf', 'PDF')
    ], string='Format', default='xlsx', required=True)

    def _get_date_range(self):
        start = self.start_date or (date.today().replace(day=1))
        end = self.end_date or date.today()
        return (start, end)

    def action_export(self):
        if xlsxwriter is None and self.report_format == 'xlsx':
            raise UserError(_('Python library xlsxwriter is required for Excel export.'))

        report_code = self.report_code
        start_date, end_date = self._get_date_range()

        # PDF Reports Mapping
        pdf_report_mapping = {
            'general_ledger': 'all_reports_full.report_general_ledger_pdf',
            'trial_balance': 'all_reports_full.report_trial_balance_pdf',
            'chart_of_accounts': 'all_reports_full.report_chart_of_accounts_pdf',
            'customer_aging': 'all_reports_full.report_customer_aging_pdf',
            'vendor_aging': 'all_reports_full.report_vendor_aging_pdf',
            'inventory_valuation': 'all_reports_full.report_inventory_valuation_pdf',
            'stock_register': 'all_reports_full.report_stock_register_pdf',
            'gr_ir': 'all_reports_full.report_gr_ir_pdf',
        }

        if self.report_format == 'pdf':
            report_action = pdf_report_mapping.get(report_code)
            if not report_action:
                raise UserError(_('PDF report not implemented for %s') % report_code.replace('_', ' ').title())
            
            # Store data in context for the report to access
            return self.env.ref(report_action).report_action(self)

        # Excel exports
        if report_code == 'general_ledger':
            return self._export_general_ledger(start_date, end_date)
        if report_code == 'trial_balance':
            return self._export_trial_balance(start_date, end_date)
        if report_code == 'chart_of_accounts':
            return self._export_chart_of_accounts()
        if report_code == 'customer_aging':
            return self._export_partner_aging(start_date, end_date, partner_type='customer')
        if report_code == 'vendor_aging':
            return self._export_partner_aging(start_date, end_date, partner_type='vendor')
        if report_code == 'inventory_valuation':
            return self._export_inventory_valuation(start_date, end_date)
        if report_code == 'stock_register':
            return self._export_stock_register(start_date, end_date)
        if report_code == 'gr_ir':
            return self._export_gr_ir(start_date, end_date)

        raise UserError(_('Unknown report'))

    def _make_xlsx_attachment_action(self, workbook_stream, filename):
        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': base64.b64encode(workbook_stream.getvalue()),
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        url = '/web/content/%s?download=true' % (attachment.id)
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def _export_general_ledger(self, start_date, end_date):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('General Ledger')

        headers = ['Date','Journal','Account Code','Account Name','Partner','Label','Debit','Credit','Balance']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)

        domain = [('date','>=',str(start_date)),('date','<=',str(end_date)),('parent_state','=','posted')]
        amls = self.env['account.move.line'].search(domain, order='date,account_id,partner_id')
        balance_map = {}
        row = 1
        for line in amls:
            acc = line.account_id
            key = acc.id
            bal = balance_map.get(key, 0.0) + (line.debit - line.credit)
            balance_map[key] = bal
            sheet.write(row, 0, str(line.date))
            sheet.write(row, 1, line.move_id.journal_id.name or '')
            sheet.write(row, 2, acc.code or '')
            sheet.write(row, 3, acc.name)
            sheet.write(row, 4, line.partner_id.name or '')
            sheet.write(row, 5, line.name or '')
            sheet.write(row, 6, float(line.debit))
            sheet.write(row, 7, float(line.credit))
            sheet.write(row, 8, float(bal))
            row += 1

        workbook.close()
        filename = 'general_ledger_%s_%s.xlsx' % (start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_trial_balance(self, start_date, end_date):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Trial Balance')
        headers = ['Account Code','Account Name','Opening Balance','Debit','Credit','Closing Balance']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)

        accounts = self.env['account.account'].search([], order='code')
        row = 1
        for acc in accounts:
            ob_domain = [('account_id','=',acc.id),('date','<',str(start_date)),('parent_state','=','posted')]
            ob_lines = self.env['account.move.line'].search(ob_domain)
            opening = sum([l.debit - l.credit for l in ob_lines])
            period_domain = [('account_id','=',acc.id),('date','>=',str(start_date)),('date','<=',str(end_date)),('parent_state','=','posted')]
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
        filename = 'trial_balance_%s_%s.xlsx' % (start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_chart_of_accounts(self):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Chart of Accounts')
        headers = ['Account Code','Account Name','Type','Reconciliable']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        accounts = self.env['account.account'].search([], order='code')
        row = 1
        for acc in accounts:
            sheet.write(row, 0, acc.code or '')
            sheet.write(row, 1, acc.name)
            # In Odoo 17, account_type is a selection field
            acc_type = ''
            if hasattr(acc, 'account_type'):
                acc_type = dict(acc._fields['account_type'].selection).get(acc.account_type, acc.account_type or '')
            sheet.write(row, 2, acc_type)
            sheet.write(row, 3, 'Yes' if acc.reconcile else 'No')
            row += 1
        workbook.close()
        filename = 'chart_of_accounts.xlsx'
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_partner_aging(self, start_date, end_date, partner_type='customer'):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Aged %s' % partner_type.title())
        headers = ['Partner','Total Due','0-30','31-60','61-90','90+']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        # Build proper domain for aging
        domain = [
            ('date','<=',str(end_date)),
            ('reconciled','=',False),
            ('parent_state','=','posted'),
            ('account_id.account_type', 'in', ['asset_receivable'] if partner_type == 'customer' else ['liability_payable'])
        ]
        
        lines = self.env['account.move.line'].search(domain)
        partners = {}
        for l in lines:
            partner = l.partner_id
            if not partner:
                continue
            partners.setdefault(partner.id, []).append(l)
        
        row = 1
        for pid, lns in partners.items():
            partner = self.env['res.partner'].browse(pid)
            buckets = [0, 0, 0, 0]  # 0-30, 31-60, 61-90, 90+
            total_due = 0.0
            
            for l in lns:
                days = (end_date - l.date).days if l.date else 0
                # Use amount_residual for proper outstanding amount
                amount = float(l.amount_residual or 0.0)
                total_due += amount
                
                if days <= 30:
                    buckets[0] += amount
                elif days <= 60:
                    buckets[1] += amount
                elif days <= 90:
                    buckets[2] += amount
                else:
                    buckets[3] += amount
            
            sheet.write(row, 0, partner.name)
            sheet.write(row, 1, float(total_due))
            sheet.write(row, 2, float(buckets[0]))
            sheet.write(row, 3, float(buckets[1]))
            sheet.write(row, 4, float(buckets[2]))
            sheet.write(row, 5, float(buckets[3]))
            row += 1
        
        workbook.close()
        filename = '%s_aging_%s_%s.xlsx' % (partner_type, start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_inventory_valuation(self, start_date, end_date):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Inventory Valuation')
        headers = ['Product','SKU','Quantity On Hand','Unit Cost','Total Value']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        products = self.env['product.product'].search([('type', '=', 'product')])
        row = 1
        for p in products:
            quants = self.env['stock.quant'].search([('product_id','=',p.id),('location_id.usage','=','internal')])
            qty_sum = sum(quants.mapped('quantity'))
            unit_cost = float(p.standard_price or 0.0)
            value = unit_cost * float(qty_sum)
            
            sheet.write(row, 0, p.name)
            sheet.write(row, 1, p.default_code or '')
            sheet.write(row, 2, float(qty_sum))
            sheet.write(row, 3, float(unit_cost))
            sheet.write(row, 4, float(value))
            row += 1
        
        workbook.close()
        filename = 'inventory_valuation_%s_%s.xlsx' % (start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_stock_register(self, start_date, end_date):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('Stock Register')
        headers = ['Date','Reference','Product','SKU','Qty','UOM','Source','Dest','Status']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        domain = [('date','>=',str(start_date)),('date','<=',str(end_date)),('state','=','done')]
        moves = self.env['stock.move'].search(domain, order='date')
        row = 1
        for m in moves:
            sheet.write(row, 0, str(m.date))
            sheet.write(row, 1, m.reference or m.picking_id.name or '')
            sheet.write(row, 2, m.product_id.name or '')
            sheet.write(row, 3, m.product_id.default_code or '')
            sheet.write(row, 4, float(m.product_uom_qty or 0.0))
            sheet.write(row, 5, m.product_uom.name or '')
            sheet.write(row, 6, m.location_id.complete_name or '')
            sheet.write(row, 7, m.location_dest_id.complete_name or '')
            sheet.write(row, 8, m.state or '')
            row += 1
        
        workbook.close()
        filename = 'stock_register_%s_%s.xlsx' % (start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    def _export_gr_ir(self, start_date, end_date):
        workbook_stream = io.BytesIO()
        workbook = xlsxwriter.Workbook(workbook_stream, {'in_memory': True})
        sheet = workbook.add_worksheet('GR-IR Report')
        headers = ['PO','Vendor','Product','Ordered Qty','Received Qty','Invoiced Qty','Difference (GR-IR)']
        for col, h in enumerate(headers):
            sheet.write(0, col, h)
        
        pos = self.env['purchase.order'].search([
            ('date_order','>=',str(start_date)),
            ('date_order','<=',str(end_date)),
            ('state','in',['purchase','done'])
        ])
        
        row = 1
        for po in pos:
            for line in po.order_line:
                ordered = float(line.product_qty or 0.0)
                received = float(line.qty_received or 0.0)
                invoiced = float(line.qty_invoiced or 0.0)
                diff = received - invoiced
                
                sheet.write(row, 0, po.name)
                sheet.write(row, 1, po.partner_id.name or '')
                sheet.write(row, 2, line.product_id.name or '')
                sheet.write(row, 3, ordered)
                sheet.write(row, 4, received)
                sheet.write(row, 5, invoiced)
                sheet.write(row, 6, diff)
                row += 1
        
        workbook.close()
        filename = 'gr_ir_%s_%s.xlsx' % (start_date, end_date)
        return self._make_xlsx_attachment_action(workbook_stream, filename)

    # Methods for PDF report data preparation
    def _get_general_ledger_data(self):
        start_date, end_date = self._get_date_range()
        domain = [('date','>=',str(start_date)),('date','<=',str(end_date)),('parent_state','=','posted')]
        lines = self.env['account.move.line'].search(domain, order='date,account_id')
        return lines

    def _get_trial_balance_data(self):
        start_date, end_date = self._get_date_range()
        accounts = self.env['account.account'].search([], order='code')
        data = []
        for acc in accounts:
            ob_domain = [('account_id','=',acc.id),('date','<',str(start_date)),('parent_state','=','posted')]
            ob_lines = self.env['account.move.line'].search(ob_domain)
            opening = sum([l.debit - l.credit for l in ob_lines])
            
            period_domain = [('account_id','=',acc.id),('date','>=',str(start_date)),('date','<=',str(end_date)),('parent_state','=','posted')]
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

    def _get_aging_data(self, partner_type):
        start_date, end_date = self._get_date_range()
        domain = [
            ('date','<=',str(end_date)),
            ('reconciled','=',False),
            ('parent_state','=','posted'),
            ('account_id.account_type', 'in', ['asset_receivable'] if partner_type == 'customer' else ['liability_payable'])
        ]
        lines = self.env['account.move.line'].search(domain)
        partners_data = {}
        
        for l in lines:
            if not l.partner_id:
                continue
            pid = l.partner_id.id
            if pid not in partners_data:
                partners_data[pid] = {'partner': l.partner_id, 'lines': [], 'buckets': [0,0,0,0], 'total': 0}
            
            days = (end_date - l.date).days if l.date else 0
            amount = float(l.amount_residual or 0.0)
            partners_data[pid]['total'] += amount
            partners_data[pid]['lines'].append(l)
            
            if days <= 30:
                partners_data[pid]['buckets'][0] += amount
            elif days <= 60:
                partners_data[pid]['buckets'][1] += amount
            elif days <= 90:
                partners_data[pid]['buckets'][2] += amount
            else:
                partners_data[pid]['buckets'][3] += amount
        
        return list(partners_data.values())