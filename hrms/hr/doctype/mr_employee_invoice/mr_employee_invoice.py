# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from erpnext.custom_utils import check_future_date
from frappe.utils import (
    cint,
    flt,
    get_last_day,
    getdate,
)
from erpnext.accounts.general_ledger import (
    make_gl_entries,
    merge_similar_entries,
)
from frappe import _
from erpnext.controllers.accounts_controller import AccountsController
from hrms.hr.hr_custom_functions import get_month_details, get_payroll_settings, get_salary_tax


class MREmployeeInvoice(AccountsController):
    def validate(self):
        check_future_date(self.posting_date)
        self.set_status()
        self.calculate_amount()

    def before_save(self):
        self.calculate_amount()

    def calculate_amount(self):
        other_deductions = total_ot_amount = total_daily_wage_amount = total_arrears_and_allowance = total_advances = total_deductions = total_tds_amount = 0
        
        # Calculate daily wages from attendance
        for a in self.attendance:
            if a.status == "Present":
                total_daily_wage_amount += flt(a.daily_wage, 2)
            elif a.status == "Half Day":
                total_daily_wage_amount += flt(flt(a.daily_wage, 2)/2, 2)
                a.daily_wage = flt(flt(a.daily_wage, 2)/2, 2)
            else:
                total_daily_wage_amount += flt(a.daily_wage, 2)
        
        # Calculate overtime
        for a in self.ot:
            total_ot_amount += flt(a.amount, 2)
        
        # Calculate advances
        for adv in self.advances:
            total_advances += flt(adv.amount, 2)
        
        # Calculate other deductions
        for d in self.deductions:
            other_deductions += flt(d.amount, 2)
        
        # Calculate arrears and allowances
        for arr in self.arrears_and_allowance:
            total_arrears_and_allowance += flt(arr.amount, 2)

        # Set calculated amounts
        self.other_deduction = flt(other_deductions, 2)
        self.total_ot_amount = flt(total_ot_amount, 2)
        self.total_daily_wage_amount = flt(total_daily_wage_amount, 2)
        self.total_arrears_and_allowance = flt(total_arrears_and_allowance, 0)
        self.total_advance = flt(total_advances, 0)

        # Calculate TDS if applicable
        has_tds_deduction = frappe.db.get_value("Muster Roll Employee", self.mr_employee, "has_tds_deduction")
        self.total_tds_amount = 0.0
        if has_tds_deduction:
            tds_percent, tds_account = frappe.db.get_value("Muster Roll Employee", self.mr_employee, ["tds_percent", "tds_account"])
            if not tds_percent:
                frappe.throw("Set TDS percent in Muster Roll Employee {}".format(self.mr_employee))
            
            # Calculate grand total before TDS
            self.grand_total = flt(
                flt(total_daily_wage_amount) + 
                flt(total_ot_amount) + 
                flt(total_arrears_and_allowance), 0
            )
            
            # Calculate TDS on grand_total
            total_tds_amount = flt(flt(tds_percent)/100 * flt(self.grand_total), 0)
            self.total_tds_amount = self.tds_amount = flt(total_tds_amount, 0)
            self.tds_percent = flt(tds_percent)
            self.tds_account = tds_account
        else:
            # Calculate grand total
            self.grand_total = flt(
                flt(total_daily_wage_amount) + 
                flt(total_ot_amount) + 
                flt(total_arrears_and_allowance), 0
            )

        # Calculate salary tax (15% of grand_total)
        grand_total=self.grand_total = flt(flt(total_daily_wage_amount) + flt(total_ot_amount) + flt(total_arrears_and_allowance), 0)
        self.salary_tax = round(get_salary_tax(flt(grand_total) - (flt(grand_total) * 0.15)),)


        
        
        # Calculate total deductions
        total_deductions = flt(
            flt(self.other_deduction) + 
            flt(self.total_advance) + 
            flt(self.total_tds_amount) +
            flt(self.salary_tax)
        )

        # Calculate net payable amount
        self.net_payable_amount = flt(
            flt(self.grand_total) - flt(total_deductions), 0
        )
        
        # Set outstanding amount
        self.outstanding_amount = self.net_payable_amount
    
    def on_submit(self):
        self.update_advance_balance()
        self.make_gl_entries()
        self.set_status(update=True)

    def on_cancel(self):
        self.ignore_linked_doctypes = ("GL Entry", "Stock Ledger Entry", "Payment Ledger Entry")
        self.update_advance_balance(cancel=True)
        self.make_gl_entries()
        self.set_status(update=True, status="Cancelled")

    def update_advance_balance(self, cancel=False):
        muster_roll_group = frappe.db.get_value("Muster Roll Employee", self.mr_employee, "muster_roll_group")
        for advance in self.advances:
            if muster_roll_group == "National":
                amount = 0.0
                if flt(advance.amount) > 0:
                    balance_amount = frappe.db.get_value("Muster Roll Advance", advance.reference_name, "balance_amount")
                    if flt(balance_amount) < flt(advance.amount) and self.docstatus < 2:
                        frappe.throw(_("Advance#{0} : Allocated amount Nu. {1}/- cannot be more than Advance Balance Nu. {2}/-").format(
                            advance.reference_name, 
                            "{:,.2f}".format(flt(advance.amount)),
                            "{:,.2f}".format(flt(balance_amount))))
                    else:
                        adv_doc = frappe.get_doc("Muster Roll Advance", advance.reference_name)
                        if cancel:
                            adv_doc.adjusted_amount = flt(adv_doc.adjusted_amount) - flt(advance.amount)
                            adv_doc.balance_amount = flt(adv_doc.balance_amount) + flt(advance.amount)
                        else:
                            adv_doc.adjusted_amount = flt(adv_doc.adjusted_amount) + flt(advance.amount)
                            adv_doc.balance_amount = flt(adv_doc.balance_amount) - flt(advance.amount)
                        adv_doc.save(ignore_permissions = True)
            else:
                if flt(advance.amount) > 0:
                    query = frappe.db.sql("""select balance_amount, adjusted_amount from `tabMuster Roll Advance Item` where parent='{}' and mr_employee='{}'""".format(
                        advance.reference_name, self.mr_employee), as_dict=True)
                    if cancel:
                        adjusted_amount = flt(query[0].adjusted_amount) - flt(advance.amount)
                        balance_amount = flt(query[0].balance_amount) + flt(advance.amount)
                    else:
                        adjusted_amount = flt(query[0].adjusted_amount) + flt(advance.amount)
                        balance_amount = flt(query[0].balance_amount) - flt(advance.amount)
                    frappe.db.sql("""update `tabMuster Roll Advance Item` 
                                   set adjusted_amount='{}', balance_amount='{}' 
                                   where parent='{}' and mr_employee='{}'""".format(
                        adjusted_amount, balance_amount, advance.reference_name, self.mr_employee))

    def make_gl_entries(self):
        gl_entries = []
        self.make_party_gl_entry(gl_entries)
        self.make_advance_gl_entries(gl_entries)
        self.make_deduction_gl_entries(gl_entries)
        self.make_expense_gl_entries(gl_entries)
        self.make_arrear_allowance_gl_entries(gl_entries)
        self.make_tds_gl_entries(gl_entries)
        self.make_salary_tax_gl_entries(gl_entries)  # New: Add salary tax GL entry
        
        gl_entries = merge_similar_entries(gl_entries)
        make_gl_entries(gl_entries, update_outstanding="No", cancel=self.docstatus == 2)

    def make_party_gl_entry(self, gl_entries):
        if flt(self.net_payable_amount) > 0:
            gl_entries.append(
                self.get_gl_dict({
                    "account": self.credit_account,
                    "credit": flt(self.net_payable_amount, 2),
                    "credit_in_account_currency": flt(self.net_payable_amount, 2),
                    "against_voucher": self.name,
                    "party_type": "Muster Roll Employee",
                    "party": self.mr_employee,
                    "against_voucher_type": self.doctype,
                    "cost_center": self.cost_center,
                    "voucher_type": self.doctype,
                    "voucher_no": self.name
                }, self.currency)
            )

    def make_advance_gl_entries(self, gl_entries):
        for d in self.advances:
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": d.account,
                        "credit": flt(d.amount, 2),
                        "credit_in_account_currency": flt(d.amount, 2),
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                        "party_type": "Muster Roll Employee",
                        "party": self.mr_employee,
                        "cost_center": self.cost_center,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                    },
                    self.currency,
                )
            )

    def make_deduction_gl_entries(self, gl_entries):
        for d in self.deductions:
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": d.account,
                        "credit": flt(d.amount, 2),
                        "credit_in_account_currency": flt(d.amount, 2),
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                        "party_type": "Muster Roll Employee",
                        "party": self.mr_employee,
                        "cost_center": self.cost_center,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                    },
                    self.currency,
                )
            )

    def make_expense_gl_entries(self, gl_entries):
        ot_account = frappe.db.get_value("Company", self.company, "overtime_allowance_account")
        muster_roll_group = frappe.db.get_value("Muster Roll Employee", self.mr_employee, "muster_roll_group")
        acc = "national_wage" if muster_roll_group == "National" else "foreign_wage"
        wages_payable_account = frappe.db.get_single_value("Projects Settings", acc)
        
        if not ot_account:
            frappe.throw("Overtime Allowance Account is missing in company")
        if not wages_payable_account:
            frappe.throw("Wage Account is missing in Projects Settings")
        
        # Wage expense entry
        gl_entries.append(
            self.get_gl_dict({
                "account": wages_payable_account,
                "debit": flt(self.total_daily_wage_amount, 2),
                "debit_in_account_currency": flt(self.total_daily_wage_amount, 2),
                "against_voucher": self.name,
                "against_voucher_type": self.doctype,
                "party_type": "Muster Roll Employee",
                "party": self.mr_employee,
                "cost_center": self.cost_center,
                "voucher_type": self.doctype,
                "voucher_no": self.name
            }, self.currency)
        )
        
        # Overtime expense entry
        gl_entries.append(
            self.get_gl_dict({
                "account": ot_account,
                "debit": flt(self.total_ot_amount, 2),
                "debit_in_account_currency": flt(self.total_ot_amount, 2),
                "against_voucher": self.name,
                "against_voucher_type": self.doctype,
                "party_type": "Muster Roll Employee",
                "party": self.mr_employee,
                "cost_center": self.cost_center,
                "voucher_type": self.doctype,
                "voucher_no": self.name
            }, self.currency)
        )

    def make_arrear_allowance_gl_entries(self, gl_entries):
        for d in self.arrears_and_allowance:
            gl_entries.append(
                self.get_gl_dict(
                    {
                        "account": d.account,
                        "debit": flt(d.amount, 2),
                        "debit_in_account_currency": flt(d.amount, 2),
                        "against_voucher": self.name,
                        "against_voucher_type": self.doctype,
                        "party_type": "Muster Roll Employee",
                        "party": self.mr_employee,
                        "cost_center": self.cost_center,
                        "voucher_type": self.doctype,
                        "voucher_no": self.name,
                    },
                    self.currency,
                )
            )

    def make_tds_gl_entries(self, gl_entries):
        if not self.tds_percent or flt(self.total_tds_amount) <= 0:
            return
        
        account = self.tds_account or frappe.db.get_value("Muster Roll Employee", self.mr_employee, "tds_account")
        if not account:
            frappe.throw("Please set TDS account in {}".format(
                frappe.get_desk_link("Muster Roll Employee", self.mr_employee)))

        gl_entries.append(
            self.get_gl_dict({
                "account": account,
                "credit": flt(self.total_tds_amount, 2),
                "credit_in_account_currency": flt(self.total_tds_amount, 2),
                "against_voucher": self.name,
                "party_type": "Muster Roll Employee",
                "party": self.mr_employee,
                "against_voucher_type": self.doctype,
                "cost_center": self.cost_center,
                "voucher_type": self.doctype,
                "voucher_no": self.name
            }, self.currency)
        )

    def make_salary_tax_gl_entries(self, gl_entries):
        """Make GL entry for salary tax (15% deduction)"""
        if flt(self.salary_tax) > 0:
            # Get salary tax account from company settings
            salary_tax_account = frappe.db.get_value("Company", self.company, "salary_tax_account")
            if not salary_tax_account:
                frappe.throw("Salary Tax Account is not set in Company {}".format(self.company))
            
            gl_entries.append(
                self.get_gl_dict({
                    "account": salary_tax_account,
                    "credit": flt(self.salary_tax, 2),
                    "credit_in_account_currency": flt(self.salary_tax, 2),
                    "against_voucher": self.name,
                    "party_type": "Muster Roll Employee",
                    "party": self.mr_employee,
                    "against_voucher_type": self.doctype,
                    "cost_center": self.cost_center,
                    "voucher_type": self.doctype,
                    "voucher_no": self.name
                }, self.currency)
            )

    def set_status(self, update=False, status=None, update_modified=True):
        if self.is_new():
            self.payment_status = "Draft"
            return

        if status:
            self.payment_status = status
        elif self.docstatus == 2:
            self.payment_status = "Cancelled"
        elif self.docstatus == 1:
            outstanding_amount = flt(self.outstanding_amount, 2)
            if outstanding_amount > 0:
                self.payment_status = "Unpaid"
            elif outstanding_amount <= 0:
                self.payment_status = "Paid"
            else:
                self.payment_status = "Submitted"
        else:
            self.payment_status = "Draft"

        if update:
            self.db_set(
                "payment_status", self.payment_status, update_modified=update_modified
            )

    @frappe.whitelist()
    def get_attendance(self):
        if not self.mr_employee or not self.fiscal_year or not self.month:
            frappe.msgprint("MR Employee or Fiscal Year or Month is missing", raise_exception=True)
        
        month = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"].index(self.month) + 1
        month = str(month) if cint(month) > 9 else "0" + str(month)
        start_date = getdate(str(self.fiscal_year) + "-" + str(month) + "-01")
        end_date = get_last_day(start_date)
        
        self.total_days_worked = 0
        self.set("attendance", [])
        
        for d in frappe.db.sql('''
            select 
                a.name as mr_attendance, 
                a.status,
                a.date, 
                b.rate_per_day as daily_wage
            from `tabMuster Roll Attendance` a 
            join `tabMuster Roll Employee` b on a.mr_employee = b.name
            where a.date between %s and %s 
            and a.status in ('Present', 'Half Day') 
            and a.docstatus = 1 
            and a.mr_employee = %s
            and not exists (
                select 1 
                from `tabMR Employee Invoice` e 
                inner join `tabMR Attendance Item` f on e.name = f.parent 
                where e.name != %s 
                and f.mr_attendance = a.name 
                and e.docstatus != 2
            )
            order by a.date
        ''', (start_date, end_date, self.mr_employee, self.name), as_dict=1):
            
            if d.status == "Present":
                self.total_days_worked += 1
            else:
                self.total_days_worked += 0.5
            
            self.append("attendance", d)
        
        if len(self.attendance) <= 0:
            frappe.msgprint(
                "No attendance found for year {} of month {}".format(
                    frappe.bold(self.fiscal_year), frappe.bold(self.month)
                ), 
                raise_exception=True
            )

    @frappe.whitelist()
    def get_ot(self):
        if not self.mr_employee or not self.fiscal_year or not self.month:
            frappe.throw("MR Employee or Fiscal Year or Month is missing")
        
        month = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ].index(self.month) + 1
        month = str(month) if cint(month) > 9 else "0" + str(month)
        start_date = getdate(str(self.fiscal_year) + "-" + str(month) + "-01")
        end_date = get_last_day(start_date)
        
        self.total_ot_hrs = 0
        self.set("ot", [])
        
        for d in frappe.db.sql('''
            select 
                a.name as overtime_entries, 
                a.number_of_hours,
                a.date, 
                b.rate_per_hour as ot_rate
            from `tabMuster Roll Overtime Entry` a 
            join `tabMuster Roll Employee` b on a.mr_employee = b.name
            where a.date between %s and %s 
            and a.docstatus = 1 
            and a.mr_employee = %s
            and not exists(
                select 1 
                from `tabMR Employee Invoice` c 
                inner join `tabOvertime Invoice Item` d on c.name = d.parent 
                where c.docstatus != 2 
                and c.name != %s 
                and d.overtime_entries = a.name
            )
            order by a.date
        ''', (start_date, end_date, self.mr_employee, self.name), as_dict=1):
            
            self.total_ot_hrs += flt(d.number_of_hours)
            amount = flt(flt(d.ot_rate) * flt(d.number_of_hours), 2)
            d.update({"amount": amount})
            self.append("ot", d)
        
        if len(self.ot) <= 0:
            frappe.msgprint(
                "No OT found for year {} of month {}".format(
                    frappe.bold(self.fiscal_year), frappe.bold(self.month)
                ),
                raise_exception=False,
            )