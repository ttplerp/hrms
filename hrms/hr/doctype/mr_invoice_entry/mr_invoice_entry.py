# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
    flt,
    money_in_words,
    get_last_day,
    getdate
)
from datetime import datetime


class MRInvoiceEntry(Document):
    def validate(self):
        self.validate_posting_date()

    def validate_posting_date(self):
        months = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        month = str(int(months.index(self.month)) + 1).rjust(2, "0")

        month_start_date = "-".join([str(self.fiscal_year), month, "01"])
        month_end_date = get_last_day(month_start_date)
    
        if not (getdate(month_start_date) <= getdate(self.posting_date) <= getdate(month_end_date)):
            frappe.throw('Posting date must be between <strong>{}</strong> and <strong>{}</strong>.'.format(month_start_date, month_end_date), title="Reset Posting Date")

    def on_submit(self):
        self.submit_mr_invoice()

    def on_cancel(self):
        frappe.db.sql(
            """
            UPDATE  
                `tabJournal Entry` 
            SET 
                docstatus = 2 
            WHERE 
                referece_doctype = '{0}'
            """.format(
                self.name
            )
        )

        frappe.db.sql(
            """
            UPDATE  
                `tabMR Employee Invoice` 
            SET 
                docstatus = 2 
            WHERE 
                mr_invoice_entry = '{0}'
            """.format(
                self.name
            )
        )
        # self.post_to_account(cancel=True)


    '''
    # Commented by Dawa Tshering
    @frappe.whitelist()
    def post_to_account(self):
        frappe.throw('Here')
        bank_account = frappe.db.get_value(
            "Branch", self.branch, "expense_bank_account"
        )
        if not bank_account:
            frappe.throw(
                _(
                    "Default bank account is not set in company {}".format(
                        frappe.bold(self.company)
                    )
                )
            )
        # debit account
        credit_account = frappe.db.get_value(
            "Company", self.company, "mr_payable_account"
        )
        if not credit_account:
            frappe.throw(
                _(
                    "Mr Payable account is not set in company {}".format(
                        frappe.bold(self.company)
                    )
                )
            )
        ot_account = frappe.db.get_value("Company", self.company, "mr_ot_account")
        wages_account = frappe.db.get_value(
            "Company", self.company, "mr_daily_wage_account"
        )
        net_payable_amount = 0.00
        total_ot_amount = 0.00
        total_daily_wage_amount = 0.00
        for inv in self.items:
            net_payable_amount += inv.net_payable_amount
            total_daily_wage_amount += inv.total_daily_wage_amount
            if inv.total_ot_amount:
                total_ot_amount += inv.total_ot_amount

        journal = [
            {
                "type": "payable",
                "entry_type": "Journal Entry",
                "series": "Journal Voucher",
                "is_submitable": 1,
            },
            {
                "type": "payment",
                "entry_type": "Bank Entry",
                "series": "Bank Payment Voucher",
                "is_submitable": 0,
            },
        ]
        for j in journal:
            je = frappe.new_doc("Journal Entry")
            je.flags.ignore_permissions = 1
            je.update(
                {
                    "doctype": "Journal Entry",
                    "voucher_type": j["entry_type"],
                    "naming_series": j["series"],
                    "title": "MR Invoice Entry " + self.name,
                    "posting_date": self.posting_date,
                    "company": self.company,
                    "total_amount_in_words": money_in_words(net_payable_amount),
                    "branch": self.branch,
                    "reference_type": self.doctype,
                    "referece_doctype": self.name,
                }
            )
            if j["type"] == "payable":
                je.update(
                    {
                        "total_debit": flt(total_daily_wage_amount, 2)
                        + flt(total_ot_amount, 2),
                        "total_credit": flt(total_daily_wage_amount, 2)
                        + flt(total_ot_amount, 2),
                    }
                )
                je.append(
                    "accounts",
                    {
                        "account": wages_account,
                        "debit_in_account_currency": flt(total_daily_wage_amount, 2),
                        "debit": flt(total_daily_wage_amount, 2),
                        "reference_type": self.doctype,
                        "reference_name": self.name,
                        "cost_center": self.cost_center,
                    },
                )
                if total_ot_amount:
                    je.append(
                        "accounts",
                        {
                            "account": ot_account,
                            "debit_in_account_currency": flt(total_ot_amount, 2),
                            "debit": flt(total_ot_amount, 2),
                            "cost_center": self.cost_center,
                            "reference_type": self.doctype,
                            "reference_name": self.name,
                        },
                    )
                for mr in self.items:
                    je.append(
                        "accounts",
                        {
                            "account": credit_account,
                            "credit_in_account_currency": flt(mr.net_payable_amount, 2),
                            "party_type": "Muster Roll Employee",
                            "party": mr.mr_employee,
                            "credit": flt(mr.net_payable_amount, 2),
                            "cost_center": self.cost_center,
                            "reference_type": self.doctype,
                            "reference_name": self.name
                        },
                    )
                if self.deductions:
                    for d in self.deductions:
                        je.append(
                            "accounts",
                            {
                                "account": d.account,
                                "credit": flt(d.amount, 2),
                                "credit_in_account_currency": flt(d.amount, 2),
                                "party_type": "Muster Roll Employee",
                                "party": self.mr_employee,
                                "reference_name": self.name,
                                "reference_type": self.doctype,
                                "cost_center": self.cost_center,
                                "reference_type": self.doctype,
                                "reference_name": self.name,
                            },
                        )
            else:
                je.update(
                    {
                        "total_debit": flt(net_payable_amount, 2),
                        "total_credit": flt(net_payable_amount, 2),
                    }
                )
                for mrb in self.items:
                    je.append(
                            "accounts",
                            {
                                "account": credit_account,
                                "debit_in_account_currency": flt(mrb.net_payable_amount, 2),
                                "debit": flt(mrb.net_payable_amount, 2),
                                "party_type": "Muster Roll Employee",
                                "party": mrb.mr_employee,
                                "cost_center": self.cost_center,
                                "reference_type": self.doctype,
                                "reference_name": self.name,
                            },
                        )
                je.append(
                    "accounts",
                    {
                        "account": bank_account,
                        "credit_in_account_currency": flt(net_payable_amount, 2),
                        "credit": flt(net_payable_amount, 2),
                        "cost_center": self.cost_center,
                    },
                )
            if j["is_submitable"] == 1:
                je.submit()
            else:
                je.insert()
    '''

    # Added by Dawa Tshering
    @frappe.whitelist()
    def post_to_account(self):
        total_payable_amount = 0
        accounts = []
        bank_account = frappe.db.get_value("Company",self.company,"default_bank_account")
        if not bank_account:
            frappe.throw('Set default bank account in company {}'.format(self.company))
        for d in frappe.db.sql('''
				select name from `tabMR Employee Invoice` 
				where docstatus = 1 and mr_invoice_entry = '{}'
				and branch = '{}' and outstanding_amount > 0 
				'''.format(self.name, self.branch), as_dict=True):
                mr_invoice = frappe.get_doc("MR Employee Invoice",d.name)
                total_payable_amount += flt(mr_invoice.net_payable_amount,2)
                accounts.append({
					"account": mr_invoice.credit_account,
					"debit_in_account_currency": flt(mr_invoice.net_payable_amount,2),
					"cost_center": mr_invoice.cost_center,
					"party_check": 1,
					"party_type": "Muster Roll Employee",
					"party": mr_invoice.mr_employee,
					"party_name":mr_invoice.mr_employee_name,
					"reference_type": mr_invoice.doctype,
					"reference_name": mr_invoice.name,
				})
        accounts.append({
            "account": bank_account,
            "credit_in_account_currency": flt(total_payable_amount,2),
            "cost_center": self.cost_center
        })
        je = frappe.new_doc("Journal Entry")
        je.flags.ignore_permissions=1
        je.update({
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"naming_series": "Bank Payment Voucher",
			"title": "MR Employee Invoice Payment ",
			"user_remark": "Note: MR Employee Invoice Payment of {} for year {}".format(self.month, self.fiscal_year),
			"posting_date": self.posting_date,
			"company": self.company,
			"total_amount_in_words": money_in_words(total_payable_amount),
			"branch": self.branch,
			"reference_type":self.doctype,
			"reference_doctype":self.name,
			"accounts":accounts
		})
        je.insert()
        frappe.msgprint(_('Journal Entry {0} posted to accounts').format(frappe.get_desk_link("Journal Entry", je.name)))

    def submit_mr_invoice(self):
        if self.mr_invoice_created == 0:
            frappe.throw("Please create MR Employee Invoice.")

        bank_account = frappe.db.get_value(
            "Branch", self.branch, "expense_bank_account"
        )
        if not bank_account:
            bank_account = frappe.db.get_value(
                "Company", self.company, "default_bank_account"
            )
        successful = failed = 0
        for inv in self.items:
            error = None
            try:
                mr_invoice = frappe.get_doc(
                    "MR Employee Invoice",
                    {
                        "mr_employee": inv.mr_employee,
                        "docstatus": 0,
                        "branch": self.branch,
                        "mr_invoice_entry": self.name,
                    },
                )
                mr_invoice.submit()
                successful += 1
            except Exception as e:
                error = e
                failed += 1
            inv_item = frappe.get_doc(inv.doctype, inv.name)
            if error:
                inv.error_message = error
                inv_item.db_set("submission_status", "Failed")
            else:
                inv_item.db_set("submission_status", "Successful")
        if successful > failed:
            self.db_set("mr_invoice_submit", 1)

    @frappe.whitelist()
    def get_mr_employee(self):
        cond = ""
        if not self.branch or not self.month or not self.fiscal_year:
            frappe.throw("Either Branch/Month/Fiscal Year is missing")
        if self.individual == 1:
            cond = "and name = '{}'".format(self.mr_employee)
        self.set("items", [])
        mr_cond = ""
        if self.muster_roll_type:
            mr_cond += " and muster_roll_type = '{}'".format(self.muster_roll_type)
        if self.muster_roll_group:
            mr_cond += " and muster_roll_group = '{}'".format(self.muster_roll_group)
        if self.team_lead:
            mr_cond += " and team_lead = '{}'".format(self.team_lead)

        for e in frappe.db.sql(
            """select 
					name as mr_employee, person_name as mr_employee_name 
					from `tabMuster Roll Employee` where status = 'Active'
					and branch = {0} {1} {2}
			""".format(
                frappe.db.escape(self.branch), cond, mr_cond
            ),
            as_dict=True,
        ):
            self.append("items", e)
    
    # @frappe.whitelist()
    # def check_mr_employee(self, args=None):
    #     flag = 0
    #     for a in self.items:
    #         if args.mr_employee == a.mr_employee:
    #             flag = 1
    #     if flag == 0:
    #         frappe.throw("No MR employee")

    # @frappe.whitelist()
    # def get_tds_amount(self, args=None):
    #     account = ""
    #     amount = 0
    #     if not args.mr_employee:
    #         frappe.throw("No MR Employee Set")

    #     if args:
    #         query = frappe.db.sql("""select * from `tabTDS Account Item`""", as_dict=True)
    #         for a in query:
    #             if a.tds_percent == args.tds_percent:
    #                 account = a.account
           
    #     return 300, account

    @frappe.whitelist()
    def get_advance(self):
        self.set("advances", [])
        for item in self.items:
            res = self.get_advance_entries(item.mr_employee)
            for d in res:
                advance_row = {
					"doctype": self.doctype + " Advance",
					"reference_type": d.reference_type,
					"reference_name": d.reference_name,
					"party_type": "Muster Roll Employee",
					"party": d.mr_employee,
					"party_name": d.mr_employee_name,
					"cost_center": d.cost_center,
					"advance_amount": flt(d.advance_amount),
					"advance_account": d.account,
					# "allocated_amount": d.allocated_amount,
				}
                self.append("advances", advance_row)
    
    def get_advance_entries(self, mr_employee):
        national_mr_emp_advance = frappe.db.sql("""
                                        select
                                            'Muster Roll Advance' as reference_type, name as reference_name, advance_account as account, balance_amount as advance_amount, cost_center, mr_employee, mr_employee_name
                                            from 
                                                `tabMuster Roll Advance` 
                                            where
                                                docstatus = 1 and balance_amount > 0 and mr_employee = '{}'
                                        """.format(mr_employee), as_dict=True)
        non_national_mr_emp_advance = frappe.db.sql("""
                                    select
                                            'Muster Roll Advance' as reference_type, adv.name as reference_name, adv.advance_account as account, adv_item.balance_amount as advance_amount, adv.cost_center, adv_item.mr_employee, adv_item.mr_employee_name
                                            from 
                                                `tabMuster Roll Advance` adv, `tabMuster Roll Advance Item` adv_item  
                                            where
                                                adv_item.parent = adv.name and adv.journal_entry_status = "Paid"
                                                and adv.docstatus = 1 and adv_item.balance_amount > 0 and adv_item.mr_employee = '{}'
                                        """.format(mr_employee), as_dict=True)
        
        total_advance = national_mr_emp_advance + non_national_mr_emp_advance
        
        return total_advance

    @frappe.whitelist()
    def create_mr_invoice(self):
        self.check_permission("write")
        account = "national_wage_payable" if self.muster_roll_group == "National" else "foreign_wage_payable"
        credit_account = frappe.db.get_single_value("Projects Settings", account)
        if not credit_account:
            frappe.throw(
                _(
                    "Mr Payable account is not set in Projects Settings"
                    )
                )

        # self.created = 1
        args = frappe._dict(
            {
                "mr_invoice_entry": self.name,
                "doctype": "MR Employee Invoice",
                "branch": self.branch,
                "cost_center": self.cost_center,
                "posting_date": self.posting_date,
                "company": self.company,
                "status": "Draft",
                "fiscal_year": self.fiscal_year,
                "month": self.month,
                "currency": self.currency,
                "credit_account": credit_account,
            }
        )
        failed = successful = 0
        for item in self.items:
            args.update(
                {
                    "mr_employee": item.mr_employee,
                    "mr_employee_name": item.mr_employee_name,
                }
            )
            error = None
            try:
                mr_invoice = frappe.get_doc(args)
                mr_invoice.get_ot()
                mr_invoice.get_attendance()
                mr_invoice.set("deductions", [])

                for d in self.deductions:
                    if d.mr_employee == item.mr_employee:
                        mr_invoice.append(
                            "deductions",
                            {
                                "account": d.account,
                                "amount": d.amount,
                                "remarks": d.remarks,
                            },
                        )
                    
                for adv in self.advances:
                    if adv.party == item.mr_employee:
                        mr_invoice.append(
                            "advances",
                            {   
                                "reference_type": adv.reference_type,
                                "reference_name": adv.reference_name,
                                "account": adv.advance_account,
                                "amount": adv.allocated_amount,
                                "remarks": adv.remarks,
                            },
                        )

                for a in self.arrears_and_allownace:
                    if a.mr_employee == item.mr_employee:
                        mr_invoice.append(
                            "arrears_and_allowance",
                            {
                                "account": a.account,
                                "amount": a.amount,
                                "remarks": a.remarks
                            }
                        )
                mr_invoice.save()
                item.total_days_worked = mr_invoice.total_days_worked
                item.total_daily_wage_amount = mr_invoice.total_daily_wage_amount
                item.other_deduction = mr_invoice.other_deduction
                item.tds_amount = mr_invoice.total_tds_amount
                item.total_advance = mr_invoice.total_advance
                item.net_payable_amount = mr_invoice.net_payable_amount
                item.total_ot_hrs = mr_invoice.total_ot_hrs
                item.total_ot_amount = mr_invoice.total_ot_amount
                item.grand_total = mr_invoice.grand_total
                item.reference = mr_invoice.name
                successful += 1
            except Exception as e:
                error = str(e)
                failed += 1

            item_invoic = frappe.get_doc(item.doctype, item.name)
            if error:
                item.creation_status = "Failed"
                item.error_message = error
            else:
                item.creation_status = "Successful"
        if successful > failed:
            self.mr_invoice_created = 1
        self.save()
        self.reload()
