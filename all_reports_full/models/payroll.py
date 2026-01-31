# -*- coding: utf-8 -*-
from odoo import api, fields, models
from math import floor



# ---------------------------
# 1) Salary Sheet
# ---------------------------
# class SalarySheetWizard(models.TransientModel):
#     _name = "salary.sheet.wizard"
#     _description = "Salary Sheet Report Wizard"

#     date_from = fields.Date(required=True)
#     date_to = fields.Date(required=True)
#     employee_ids = fields.Many2many('hr.employee', string="Employees")

#     def action_view_report(self):
#         self.ensure_one()
#         self.preview_ids.unlink()

#         domain = [
#             ('date_from', '>=', self.date_from),
#             ('date_to', '<=', self.date_to),
#             ('state', '=', 'done'),
#         ]
#         if self.employee_ids:
#             domain.append(('employee_id', 'in', self.employee_ids.ids))

#         slips = self.env['hr.payslip'].search(domain)

#         lines = []
#         for slip in slips:
#             basic = get_amount(slip, {'BASIC'})
#             hra = get_amount(slip, {'HRA'})
#             da = get_amount(slip, {'DA'})
#             gross = basic + hra + da
#             pf = abs(get_amount(slip, {'PF'}))
#             esi = abs(get_amount(slip, {'ESI'}))
#             pt = abs(get_amount(slip, {'PT'}))
#             tds = abs(get_amount(slip, {'TDS'}))
#             net = gross - (pf + esi + pt + tds)

#             lines.append((0, 0, {
#                 'employee': slip.employee_id.name,
#                 'department': slip.employee_id.department_id.name or '',
#                 'basic': basic,
#                 'hra': hra,
#                 'da': da,
#                 'gross': gross,
#                 'pf': pf,
#                 'esi': esi,
#                 'pt': pt,
#                 'tds': tds,
#                 'net': net,
#             }))

#         self.preview_ids = lines
#         return {'type': 'ir.actions.do_nothing'}

  


#     def action_print_salary_sheet(self):
#         data = {
#             'date_from': self.date_from,
#             'date_to': self.date_to,
#             'employee_ids': self.employee_ids.ids,
#         }
#         return self.env.ref('all_reports_full.salary_sheet_report_action').report_action(self, data=data)



class SalarySheetWizard(models.TransientModel):
    _name = "salary.sheet.wizard"
    _description = "Salary Sheet Wizard"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    employee_ids = fields.Many2many('hr.employee')

    preview_ids = fields.One2many(
        'salary.sheet.preview', 'wizard_id'
    )

    def action_view_report(self):
        self.ensure_one()
        self.preview_ids.unlink()

        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        slips = self.env['hr.payslip'].search(domain)

        lines = []
        for slip in slips:
            basic = get_amount(slip, {'BASIC'})
            hra = get_amount(slip, {'HRA'})
            da = get_amount(slip, {'DA'})
            gross = basic + hra + da
            pf = abs(get_amount(slip, {'PF'}))
            esi = abs(get_amount(slip, {'ESI'}))
            pt = abs(get_amount(slip, {'PT'}))
            tds = abs(get_amount(slip, {'TDS'}))
            net = gross - (pf + esi + pt + tds)

            lines.append((0, 0, {
                'employee': slip.employee_id.name,
                'department': slip.employee_id.department_id.name or '',
                'basic': basic,
                'hra': hra,
                'da': da,
                'gross': gross,
                'pf': pf,
                'esi': esi,
                'pt': pt,
                'tds': tds,
                'net': net,
            }))

        self.preview_ids = lines
        return {
        'type': 'ir.actions.act_window',
        'name': 'Salary Sheet',
        'res_model': self._name,
        'res_id': self.id,
        'view_mode': 'form',
        'target': 'new',
    }

    def action_print_salary_sheet(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': self.employee_ids.ids,
        }
        return self.env.ref(
            'all_reports_full.salary_sheet_report_action'
        ).report_action(self, data=data)


class ReportSalarySheet(models.AbstractModel):
    _name = "report.all_reports_full.salary_sheet_template"
    _description = "Salary Sheet QWeb Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        employee_ids = data.get('employee_ids') or []

        # find payslips in period
        domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', '=', 'done'),
        ]
        if employee_ids:
            domain.append(('employee_id', 'in', employee_ids))

        payslips = self.env['hr.payslip'].search(domain, order='employee_id, date_from')

        # helper to safely get totals for a given salary rule code
        def get_line_total(slip, code):
            if not slip:
                return 0.0
            lines = slip.line_ids.filtered(lambda l: (l.code or '').strip().upper() == (code or '').strip().upper())
            # if multiple lines with same code, sum totals
            return float(sum(l.total or 0.0 for l in lines))

        # fallback: classify a line as earning/deduction depending on sign if code unknown
        def classify_lines(slip):
            earnings = {}
            deductions = {}
            for l in slip.line_ids:
                code = (l.code or '').strip().upper() or ('UNKNOWN_%s' % l.id)
                amt = float(l.total or 0.0)
                if amt >= 0:
                    earnings[code] = earnings.get(code, 0.0) + amt
                else:
                    deductions[code] = deductions.get(code, 0.0) + abs(amt)
            return earnings, deductions

        rows = []
        totals = {
            'basic': 0.0, 'hra': 0.0, 'da': 0.0, 'conveyance': 0.0,
            'medical': 0.0, 'special': 0.0, 'overtime': 0.0, 'other_earn': 0.0,
            'pf': 0.0, 'esi': 0.0, 'pt': 0.0, 'tds': 0.0, 'other_ded': 0.0,
            'gross': 0.0, 'net': 0.0
        }

        for slip in payslips:
            emp = slip.employee_id

            # Prefer explicit salary-rule codes; fallback to classification if needed
            basic = get_line_total(slip, 'BASIC')
            hra = get_line_total(slip, 'HRA')
            da = get_line_total(slip, 'DA')
            conv = get_line_total(slip, 'CONV') or get_line_total(slip, 'CONVEY') or get_line_total(slip, 'CONVEYANCE')
            med = get_line_total(slip, 'MED') or get_line_total(slip, 'MEDICAL')
            special = get_line_total(slip, 'SPALLOW') or get_line_total(slip, 'SPECIAL') or get_line_total(slip, 'SPECALLOW')
            ot = get_line_total(slip, 'OT') or get_line_total(slip, 'OVERTIME')
            gross = (
    get_line_total(slip, 'BASIC')
    + get_line_total(slip, 'HRA')
    + get_line_total(slip, 'DA')
    + get_line_total(slip, 'CONV')
    + get_line_total(slip, 'MED')
    + get_line_total(slip, 'SPALLOW')
    + get_line_total(slip, 'OT')
)  # many setups have explicit GROSS line
            net = get_line_total(slip, 'NET')

            # Deductions
            pf = get_line_total(slip, 'PF') or get_line_total(slip, 'EPF') or get_line_total(slip, 'PFEE')
            esi = get_line_total(slip, 'ESI')
            pt = get_line_total(slip, 'PT') or get_line_total(slip, 'PROFTAX') or get_line_total(slip, 'PROF_TAX')
            tds = get_line_total(slip, 'TDS')

            # If many values are zero, try to intelligently classify lines
            if not any([basic, hra, da, conv, med, special, ot, gross, net, pf, esi, pt, tds]):
                earnings_map, deductions_map = classify_lines(slip)
                # attempt reasonable picks
                basic = basic or earnings_map.get('BASIC', 0.0)
                hra = hra or earnings_map.get('HRA', 0.0)
                da = da or earnings_map.get('DA', 0.0)
                gross = gross or sum(earnings_map.values())
                pf = pf or deductions_map.get('PF', 0.0)
                esi = esi or deductions_map.get('ESI', 0.0)
                pt = pt or deductions_map.get('PT', 0.0)
                tds = tds or deductions_map.get('TDS', 0.0)
                # any earnings not classified go to other_earn
                other_earn = sum(v for k, v in earnings_map.items() if k not in {'BASIC', 'HRA', 'DA', 'CONV', 'CONVEY', 'MED', 'SPALLOW', 'OT', 'OVERTIME', 'GROSS', 'NET'})
                other_ded = sum(v for k, v in deductions_map.items() if k not in {'PF', 'ESI', 'PT', 'TDS'})
            else:
                # compute any remaining 'other' amounts from lines not matched above
                matched_codes = {'BASIC', 'HRA', 'DA', 'CONV', 'CONVEY', 'CONVEYANCE', 'MED', 'MEDICAL', 'SPALLOW', 'SPECIAL', 'SPECALLOW', 'OT', 'OVERTIME', 'GROSS', 'NET', 'PF', 'EPF', 'PFEE', 'ESI', 'PT', 'PROFTAX', 'PROF_TAX', 'TDS'}
                other_earn = 0.0
                other_ded = 0.0
                for l in slip.line_ids:
                    code = (l.code or '').strip().upper()
                    amt = float(l.total or 0.0)
                    if code not in matched_codes:
                        if amt >= 0:
                            other_earn += amt
                        else:
                            other_ded += abs(amt)

            # If gross still zero, compute as sum of earnings (basic + hra + da + conv + med + special + ot + other_earn)
            if not gross:
                gross = basic + hra + da + conv + med + special + ot + other_earn

            # If net still zero, compute net as gross - (pf + esi + pt + tds + other_ded)
            if not net:
                net = gross - (pf + esi + pt + tds + other_ded)

            # accumulate totals
            totals['basic'] += basic
            totals['hra'] += hra
            totals['da'] += da
            totals['conveyance'] += conv
            totals['medical'] += med
            totals['special'] += special
            totals['overtime'] += ot
            totals['other_earn'] += other_earn
            totals['pf'] += pf
            totals['esi'] += esi
            totals['pt'] += pt
            totals['tds'] += tds
            totals['other_ded'] += other_ded
            totals['gross'] += gross
            totals['net'] += net

            rows.append({
                'employee_name': emp.name,
                'employee_code': getattr(emp, 'employee_id', False) or getattr(emp, 'identification_id', False) or emp.id,
                'department': emp.department_id.name if emp.department_id else '',
                'job_title': emp.job_id.name if emp.job_id else '',
                'work_days': getattr(slip, 'worked_days_count', 0),
                'lop': getattr(slip, 'unpaid_leaves', 0) or 0,
                'basic': basic,
                'hra': hra,
                'da': da,
                'conveyance': conv,
                'medical': med,
                'special': special,
                'overtime': ot,
                'other_earn': other_earn,
                'gross': gross,
                'pf': pf,
                'esi': esi,
                'pt': pt,
                'tds': tds,
                'other_ded': other_ded,
                'net': net,
                'bank_acc': getattr(getattr(emp, 'bank_account_id', False), 'acc_number', '') or getattr(emp, 'bank_account_no', '') or '',
                'slip': slip,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'salary.sheet.wizard',
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'rows': rows,
            'totals': totals,
        }


# ---------------------------
# 2) PF / ESI / PT Summary
# ---------------------------
class PFESIPTSummaryWizard(models.TransientModel):
    _name = "pf.esi.pt.summary.wizard"
    _description = "PF / ESI / PT Summary Wizard"

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    employee_ids = fields.Many2many('hr.employee', string="Employees")

    preview_ids = fields.One2many(
        'pf.esi.pt.preview',
        'wizard_id',
        string="Preview Lines"
    )
    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


    def action_view_report(self):
        self.ensure_one()
        self.preview_ids.unlink()

        domain = [
            ('date_from', '>=', self.date_from),
            ('date_to', '<=', self.date_to),
            ('state', '=', 'done'),
        ]
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))

        slips = self.env['hr.payslip'].search(domain)

        data = {}
        for slip in slips:
            emp = slip.employee_id.name
            data.setdefault(emp, {'pf': 0, 'esi': 0, 'pt': 0})
            data[emp]['pf'] += abs(get_amount(slip, {'PF'}))
            data[emp]['esi'] += abs(get_amount(slip, {'ESI'}))
            data[emp]['pt'] += abs(get_amount(slip, {'PT'}))

        self.preview_ids = [(0, 0, {
            'employee': k,
            'pf': v['pf'],
            'esi': v['esi'],
            'pt': v['pt'],
        }) for k, v in data.items()]

        return self._reopen()

 

    def action_print_pf_esi_pt(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'employee_ids': self.employee_ids.ids,
        }
        return self.env.ref('all_reports_full.pf_esi_pt_summary_report_action').report_action(self, data=data)


class ReportPFESIPT(models.AbstractModel):
    _name = "report.all_reports_full.pf_esi_pt_summary_template"
    _description = "PF ESI PT Summary QWeb Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        date_from = data.get('date_from')
        date_to = data.get('date_to')
        employee_ids = data.get('employee_ids') or []

        # search payslips
        domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('state', '=', 'done'),
        ]
        if employee_ids:
            domain.append(('employee_id', 'in', employee_ids))
        payslips = self.env['hr.payslip'].search(domain, order='employee_id')

        # aggregation per employee
        summary = {}
        for slip in payslips:
            emp = slip.employee_id
            key = emp.id
            rec = summary.setdefault(key, {
                'employee': emp,
                'pf_emp': 0.0, 'pf_emp_er': 0.0, 'eps': 0.0,
                'esi_emp': 0.0, 'esi_er': 0.0, 'pt': 0.0, 'pf_wages': 0.0, 'esi_wages': 0.0
            })
            # iterate lines
            for l in slip.line_ids:
                code = (l.code or '').upper()
                amt = float(l.total or 0.0)
                # PF employee contribution
                if code in ('PF', 'EPF', 'PFEE', 'PFD') or ('PF' in code and 'EMP' in code):
                    rec['pf_emp'] += abs(amt)
                # Employer PF or ER
                if 'ER' in code and 'PF' in code or code in ('PF_ER', 'ERPF'):
                    rec['pf_emp_er'] += abs(amt)
                # EPS / Pension
                if 'EPS' in code or 'PENSION' in code:
                    rec['eps'] += abs(amt)
                # ESI
                if 'ESI' in code:
                    if 'ER' in code or 'EMPLOYER' in code:
                        rec['esi_er'] += abs(amt)
                    else:
                        rec['esi_emp'] += abs(amt)
                # PT / PROFESSIONAL TAX
                if 'PT' in code or 'PROF_TAX' in code or 'PROFESSIONAL' in code:
                    rec['pt'] += abs(amt)
                # attempt to find pf/esi wages from lines with typical codes:
                if code in ('PFW', 'PF_WAGES', 'PF_WAGE'):
                    rec['pf_wages'] += abs(amt)
                if code in ('ESIW', 'ESI_WAGES', 'ESI_WAGE'):
                    rec['esi_wages'] += abs(amt)
            # if not found wages, try to use basic from slip
            if not rec['pf_wages']:
                basic = sum(l.total for l in slip.line_ids if (l.code or '').upper() in ('BASIC',))
                rec['pf_wages'] += basic
            if not rec['esi_wages']:
                rec['esi_wages'] += rec['pf_wages']  # fallback

        # prepare list
        rows = []
        grand = {'pf_emp':0.0,'pf_emp_er':0.0,'eps':0.0,'esi_emp':0.0,'esi_er':0.0,'pt':0.0}
        for k, v in summary.items():
            rows.append(v)
            grand['pf_emp'] += v['pf_emp']
            grand['pf_emp_er'] += v['pf_emp_er']
            grand['eps'] += v['eps']
            grand['esi_emp'] += v['esi_emp']
            grand['esi_er'] += v['esi_er']
            grand['pt'] += v['pt']

        return {
            'doc_ids': docids,
            'doc_model': 'pf.esi.pt.summary.wizard',
            'data': data,
            'date_from': date_from,
            'date_to': date_to,
            'rows': rows,
            'grand': grand,
        }


# ---------------------------
# 3) Gratuity & Leave Provision
# ---------------------------
class GratuityLeaveProvisionWizard(models.TransientModel):
    _name = "gratuity.leave.provision.wizard"
    _description = "Gratuity and Leave Provision Wizard"

    as_of_date = fields.Date(required=True, string="As of Date")
    employee_ids = fields.Many2many('hr.employee', string="Employees")
    preview_ids = fields.One2many(
        'gratuity.leave.preview', 'wizard_id'
    )


    def _reopen(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


    def action_view_report(self):
        self.ensure_one()
        self.preview_ids.unlink()

        employees = self.employee_ids or self.env['hr.employee'].search([])

        lines = []
        for emp in employees:
            # hire = emp.employee_id.date_start or emp.create_date.date()
            hire = emp.create_date.date()
            years = floor((self.as_of_date - hire).days / 365) if hire else 0

            slip = self.env['hr.payslip'].search(
                [('employee_id', '=', emp.id), ('state', '=', 'done')],
                order='date_from desc', limit=1
            )
            basic = get_amount(slip, {'BASIC'}) if slip else 0
            gratuity = (basic * 15 / 26) * years if years else 0

            lines.append((0, 0, {
                'employee': emp.name,
                'years': years, 
                'basic': basic,
                'gratuity': gratuity,
            }))

        self.preview_ids = lines
        return self._reopen()

   
    def action_print_gratuity_leave(self):
        data = {
            'as_of_date': self.as_of_date,
            'employee_ids': self.employee_ids.ids,
        }
        return self.env.ref('all_reports_full.gratuity_leave_provision_report_action').report_action(self, data=data)


class ReportGratuityLeaveProvision(models.AbstractModel):
    _name = "report.all_reports_full.gratuity_leave_provision_template"
    _description = "Gratuity & Leave Provision QWeb Report"






    @api.model
    def _get_report_values(self, docids, data=None):
        as_of = data.get('as_of_date')
        employee_ids = data.get('employee_ids') or []

        rows = []
        grand = {'gratuity':0.0, 'leave_provision':0.0}
        # find employees
        domain = []
        if employee_ids:
            domain = [('id','in', employee_ids)]
        employees = self.env['hr.employee'].search(domain, order='name')

        for emp in employees:
            # determine hire date
            hire_date = getattr(emp, 'hire_date', False) or getattr(emp, 'employee_id.date_start', False) or False
            # fallback: try contract start
            if not hire_date:
                last_contract = emp.contract_id or (emp.contract_ids and emp.contract_ids[:1])
                if last_contract:
                    hire_date = getattr(last_contract, 'employee_id.date_start', False)
            # parse dates
            years_service = 0
            try:
                if hire_date and as_of:
                    hd = fields.Date.from_string(hire_date) if isinstance(hire_date, str) else hire_date
                    ao = fields.Date.from_string(as_of) if isinstance(as_of, str) else as_of
                    days = (ao - hd).days
                    years_service = floor(days / 365) if days > 0 else 0
            except Exception:
                years_service = 0

            # find last payslip basic (latest payslip before as_of)
            basic = 0.0
            slip_domain = [('state', '=', 'done')]
            if as_of:
                slip_domain += [('date_from', '<=', as_of)]
            slip_domain += [('employee_id', '=', emp.id)]
            last_slip = self.env['hr.payslip'].search(slip_domain, order='date_from desc', limit=1)
            if last_slip:
                basic = sum(l.total for l in last_slip.line_ids if (l.code or '').upper() == 'BASIC') or 0.0

            # gratuity: standard formula (15/26)*basic*years_of_service (common practice)
            gratuity = 0.0
            try:
                gratuity = (basic * 15.0 / 26.0) * years_service if basic and years_service else 0.0
            except Exception:
                gratuity = 0.0

            # leave provision: attempt to approximate leave balance
            leave_balance = 0.0
            # Attempt: sum of remaining allocations (best-effort; custom setups may differ)
            try:
                allocations = self.env['hr.leave.allocation'].search([('employee_id','=',emp.id), ('state','=','validate')])
                for alloc in allocations:
                    # many installs use 'number_of_days' or 'number_of_days_display'
                    nd = getattr(alloc, 'number_of_days_display', None)
                    if nd is None:
                        nd = getattr(alloc, 'number_of_days', 0.0)
                    leave_balance += nd or 0.0
                # subtract taken leaves in period up to as_of (approx)
                leaves = self.env['hr.leave'].search([('holiday_status_id.include_in_calendar','=','True'), ('employee_id','=',emp.id), ('state','=','validate'), ('request_date_from','<=', as_of)])
                used = sum(abs(getattr(l, 'number_of_days_display', 0.0) or getattr(l,'number_of_days', 0.0)) for l in leaves)
                # approximate net balance
                leave_balance = max(0.0, leave_balance - used)
            except Exception:
                leave_balance = 0.0

            # per day salary estimation
            per_day = (basic / 30.0) if basic else 0.0
            leave_provision_value = leave_balance * per_day

            rows.append({
                'employee': emp,
                'hire_date': hire_date,
                'years_service': years_service,
                'basic': basic,
                'gratuity': gratuity,
                'leave_balance': leave_balance,
                'per_day_salary': per_day,
                'leave_provision': leave_provision_value,
            })

            grand['gratuity'] += gratuity
            grand['leave_provision'] += leave_provision_value

        return {
            'doc_ids': docids,
            'doc_model': 'gratuity.leave.provision.wizard',
            'data': data,
            'as_of': as_of,
            'rows': rows,
            'grand': grand,
        }





# =====================================================
# COMMON HELPERS
# =====================================================
def get_amount(slip, codes):
    return sum(
        l.total for l in slip.line_ids
        if (l.code or '').upper() in codes
    )


# =====================================================
# 1️⃣ SALARY SHEET
# =====================================================
class SalarySheetPreview(models.TransientModel):
    _name = "salary.sheet.preview"
    _description = "Salary Sheet Preview"

    wizard_id = fields.Many2one('salary.sheet.wizard', ondelete='cascade')

    employee = fields.Char()
    department = fields.Char()
    basic = fields.Float()
    hra = fields.Float()
    da = fields.Float()
    gross = fields.Float()
    pf = fields.Float()
    esi = fields.Float()
    pt = fields.Float()
    tds = fields.Float()
    net = fields.Float()


# class SalarySheetWizard(models.TransientModel):
#     _name = "salary.sheet.wizard"
#     _description = "Salary Sheet Wizard"

#     date_from = fields.Date(required=True)
#     date_to = fields.Date(required=True)
#     employee_ids = fields.Many2many('hr.employee')

#     preview_ids = fields.One2many(
#         'salary.sheet.preview', 'wizard_id'
#     )

#     def action_view_report(self):
#         self.ensure_one()
#         self.preview_ids.unlink()

#         domain = [
#             ('date_from', '>=', self.date_from),
#             ('date_to', '<=', self.date_to),
#             ('state', '=', 'done'),
#         ]
#         if self.employee_ids:
#             domain.append(('employee_id', 'in', self.employee_ids.ids))

#         slips = self.env['hr.payslip'].search(domain)

#         lines = []
#         for slip in slips:
#             basic = get_amount(slip, {'BASIC'})
#             hra = get_amount(slip, {'HRA'})
#             da = get_amount(slip, {'DA'})
#             gross = basic + hra + da
#             pf = abs(get_amount(slip, {'PF'}))
#             esi = abs(get_amount(slip, {'ESI'}))
#             pt = abs(get_amount(slip, {'PT'}))
#             tds = abs(get_amount(slip, {'TDS'}))
#             net = gross - (pf + esi + pt + tds)

#             lines.append((0, 0, {
#                 'employee': slip.employee_id.name,
#                 'department': slip.employee_id.department_id.name or '',
#                 'basic': basic,
#                 'hra': hra,
#                 'da': da,
#                 'gross': gross,
#                 'pf': pf,
#                 'esi': esi,
#                 'pt': pt,
#                 'tds': tds,
#                 'net': net,
#             }))

#         self.preview_ids = lines
#         return {'type': 'ir.actions.do_nothing'}

#     def action_print_pdf(self):
#         return self.env.ref(
#             'all_reports_full.salary_sheet_report_action'
#         ).report_action(self)


# =====================================================
# 2️⃣ PF / ESI / PT SUMMARY
# =====================================================
class PFESIPTPreview(models.TransientModel):
    _name = "pf.esi.pt.preview"
    _description = "PF ESI PT Preview"

    wizard_id = fields.Many2one('pf.esi.pt.summary.wizard', ondelete='cascade')

    employee = fields.Char()
    pf = fields.Float()
    esi = fields.Float()
    pt = fields.Float()


# class PFESIPTSummaryWizard(models.TransientModel):
#     _name = "pf.esi.pt.summary.wizard"
#     _description = "PF ESI PT Summary Wizard"

#     date_from = fields.Date(required=True)
#     date_to = fields.Date(required=True)
#     employee_ids = fields.Many2many('hr.employee')

#     preview_ids = fields.One2many(
#         'pf.esi.pt.preview', 'wizard_id'
#     )

#     def action_view_report(self):
#         self.ensure_one()
#         self.preview_ids.unlink()

#         domain = [
#             ('date_from', '>=', self.date_from),
#             ('date_to', '<=', self.date_to),
#             ('state', '=', 'done'),
#         ]
#         if self.employee_ids:
#             domain.append(('employee_id', 'in', self.employee_ids.ids))

#         slips = self.env['hr.payslip'].search(domain)

#         data = {}
#         for slip in slips:
#             emp = slip.employee_id.name
#             data.setdefault(emp, {'pf': 0, 'esi': 0, 'pt': 0})
#             data[emp]['pf'] += abs(get_amount(slip, {'PF'}))
#             data[emp]['esi'] += abs(get_amount(slip, {'ESI'}))
#             data[emp]['pt'] += abs(get_amount(slip, {'PT'}))

#         self.preview_ids = [(0, 0, {
#             'employee': k,
#             'pf': v['pf'],
#             'esi': v['esi'],
#             'pt': v['pt'],
#         }) for k, v in data.items()]

#         return {'type': 'ir.actions.do_nothing'}

#     def action_print_pdf(self):
#         return self.env.ref(
#             'all_reports_full.pf_esi_pt_summary_report_action'
#         ).report_action(self)


# =====================================================
# 3️⃣ GRATUITY & LEAVE PROVISION
# =====================================================
class GratuityLeavePreview(models.TransientModel):
    _name = "gratuity.leave.preview"
    _description = "Gratuity Leave Preview"

    wizard_id = fields.Many2one('gratuity.leave.provision.wizard', ondelete='cascade')

    employee = fields.Char()
    years = fields.Integer()
    basic = fields.Float()
    gratuity = fields.Float()


# class GratuityLeaveProvisionWizard(models.TransientModel):
#     _name = "gratuity.leave.provision.wizard"
#     _description = "Gratuity Leave Provision Wizard"

#     as_of_date = fields.Date(required=True)
#     employee_ids = fields.Many2many('hr.employee')

#     preview_ids = fields.One2many(
#         'gratuity.leave.preview', 'wizard_id'
#     )

#     def action_view_report(self):
#         self.ensure_one()
#         self.preview_ids.unlink()

#         employees = self.employee_ids or self.env['hr.employee'].search([])

#         lines = []
#         for emp in employees:
#             hire = emp.employee_id.date_start or emp.create_date.date()
#             years = floor((self.as_of_date - hire).days / 365) if hire else 0

#             slip = self.env['hr.payslip'].search(
#                 [('employee_id', '=', emp.id), ('state', '=', 'done')],
#                 order='date_from desc', limit=1
#             )
#             basic = get_amount(slip, {'BASIC'}) if slip else 0
#             gratuity = (basic * 15 / 26) * years if years else 0

#             lines.append((0, 0, {
#                 'employee': emp.name,
#                 'years': years,
#                 'basic': basic,
#                 'gratuity': gratuity,
#             }))

#         self.preview_ids = lines
#         return {'type': 'ir.actions.do_nothing'}

   
   
   
#     def action_print_pdf(self):
#         return self.env.ref(
#             'all_reports_full.gratuity_leave_provision_report_action'
#         ).report_action(self)

# access_salary_sheet_preview,salary.sheet.preview,model_salary_sheet_preview,base.group_user,1,1,1,1
# access_pf_esi_pt_preview,pf.esi.pt.preview,model_pf_esi_pt_preview,base.group_user,1,1,1,1
# access_gratuity_leave_preview,gratuity.leave.preview,model_gratuity_leave_preview,base.group_user,1,1,1,1