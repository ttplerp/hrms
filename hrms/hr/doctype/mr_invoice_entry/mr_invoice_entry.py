# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
    flt,
    money_in_words,
)


class MRInvoiceEntry(Document):
    pass

    def on_submit(self):
        self.submit_mr_invoice()
        
    def on_cancel(self):
        frappe.db.sql("""
            UPDATE  
                `tabJournal Entry` 
            SET 
                docstatus = 2 
            WHERE 
                referece_doctype = '{0}'
            """.format(self.name))
        
        frappe.db.sql("""
            UPDATE  
                `tabMR Employee Invoice` 
            SET 
                docstatus = 2 
            WHERE 
                mr_invoice_entry = '{0}'
            """.format(self.name))
        # self.post_to_account(cancel=True)

    @frappe.whitelist()
    def post_to_account(self):
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
                je.append(
                    "accounts",
                    {
                        "account": wages_account,
                        "debit_in_account_currency": flt(total_daily_wage_amount, 2),
                        "cost_center": self.cost_center,
                        "reference_type": self.doctype,
                        "reference_name": self.name,
                    },
                )
                if total_ot_amount:
                    je.append(
                        "accounts",
                        {
                            "account": ot_account,
                            "debit_in_account_currency": flt(total_ot_amount, 2),
                            "cost_center": self.cost_center,
                            "reference_type": self.doctype,
                            "reference_name": self.name,
                        },
                    )

                je.append(
                    "accounts",
                    {
                        "account": credit_account,
                        "credit_in_account_currency": flt(net_payable_amount, 2),
                        "cost_center": self.cost_center,
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
                                "reference_name": self.name,
                                "reference_type": self.doctype,
                                "cost_center": self.cost_center,
                                # "voucher_type": self.doctype,
                                # "voucher_no": self.name,
                            },
                        )
            else:
                je.append(
                    "accounts",
                    {
                        "account": credit_account,
                        "debit_in_account_currency": flt(net_payable_amount, 2),
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
                        "cost_center": self.cost_center,
                    },
                )
            if j["is_submitable"] == 1:
                je.submit()
            else:
                je.insert()
                

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
        for e in frappe.db.sql(
            """select 
					name as mr_employee, person_name as mr_employee_name 
					from `tabMuster Roll Employee` where status = 'Active'
					and branch = {0} {1}
			""".format(
                frappe.db.escape(self.branch), cond
            ),
            as_dict=True,
        ):
            self.append("items", e)

    @frappe.whitelist()
    def create_mr_invoice(self):
        self.check_permission("write")
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
                mr_invoice.save()
                item.total_days_worked = mr_invoice.total_days_worked
                item.total_daily_wage_amount = mr_invoice.total_daily_wage_amount
                item.other_deduction = mr_invoice.other_deduction
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

