# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, money_in_words, now_datetime, nowdate
from frappe import _
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class MusterRollAdvance(Document):
	def validate(self):
		self.set_status()
		self.set_defaults()
		validate_workflow_states(self)

	def on_submit(self):
		if flt(self.advance_amount <= 0):
			frappe.throw(_("Please input valid advance amount"), title="Invalid Amount")
		self.post_journal_entry()

	def set_status(self):
		self.status = {
			"0": "Draft",
			"1": "Submitted",
			"2": "Cancelled"
		}[str(self.docstatus or 0)]

	def set_defaults(self):
		if self.docstatus < 2:
			self.journal_entry = None
			self.journal_entry_status = None
			self.paid_amount = 0
			self.adjustment_amount = 0
			self.balance_amount = 0

		if self.advance_amount <= 0:
			frappe.throw("Advance amount must be greater than 0.")

	
	@frappe.whitelist()
	def get_advance_account(self):
		account_name = "foreign_worker_advance_account" if self.muster_roll_group == "Non-National" else "national_worker_advance_account"
		account = frappe.db.get_value("Company", self.company, account_name)
		if not account:
			frappe.throw("Please set Advance Account in Company.")
		return account


	def post_journal_entry(self):
		if self.advance_account:
			adv_gl = self.advance_account

		if not adv_gl:
			frappe.throw(_("Advance GL is not defined."))
		adv_gl_det = frappe.db.get_value(doctype="Account", filters=adv_gl, fieldname=["account_type","is_an_advance_account"], as_dict=True)

		# Fetching Revenue & Expense GLs
		rev_gl, exp_gl = frappe.db.get_value("Branch", self.branch, ["revenue_bank_account", "expense_bank_account"])
		
		if not exp_gl:
				frappe.throw(_("Expense GL is not defined for this Branch '{0}'.").format(self.branch), title="Data Missing")
		exp_gl_det = frappe.db.get_value(doctype="Account", filters=exp_gl, fieldname=["account_type","is_an_advance_account"], as_dict=True)

		if self.settle_imprest_advance_account:
			exp_gl = frappe.db.get_value("Company", self.company, "imprest_advance_account")
			if not exp_gl:
				frappe.throw(_("Imprest Advance Account is not defined for this Company '{0}'.").format(self.company), title="Data Missing")

		# Posting Journal Entry
		accounts = []
		accounts.append({"account": adv_gl,
			"debit_in_account_currency": flt(self.advance_amount),
			"cost_center": self.cost_center,
			"party_check": 1,
			"party_type": "Muster Roll Employee",
			"party": self.mr_employee,
			"account_type": adv_gl_det.account_type,
			"is_advance": "Yes" if adv_gl_det.is_an_advance_account == 1 else None,
			"reference_type": "Muster Roll Advance",
			"reference_name": self.name,
		})
		if self.settle_imprest_advance_account:
			accounts.append({"account": exp_gl,
				"credit_in_account_currency": flt(self.advance_amount),
				"cost_center": self.cost_center,
				"party_check": 1,
				"party_type": "Employee",
				"party": self.imprest_party,
				"account_type": exp_gl_det.account_type,
				"is_advance": "Yes",
			})
		else:
			accounts.append({"account": exp_gl,
				"credit_in_account_currency": flt(self.advance_amount),
				"cost_center": self.cost_center,
				"party_check": 0,
				"account_type": exp_gl_det.account_type,
				# "is_advance": "Yes" if exp_gl_det.is_an_advance_account == 1 else "No",
				"is_advance": "Yes",
			})

		je = frappe.new_doc("Journal Entry")
		
		je.update({
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry" if self.settle_imprest_advance_account else "Bank Entry",
				"naming_series": "Journal Voucher" if self.settle_imprest_advance_account else "Bank Payment Voucher",
				"mode_of_payment": "Adjustment Entry" if self.settle_imprest_advance_account else "Online Payment",
				"title": "Muster Roll Advance - "+self.name,
				"user_remark": "Muster Roll Advance - "+self.name,
				"posting_date": self.posting_date,
				"company": self.company,
				"total_amount_in_words": money_in_words(self.advance_amount),
				"accounts": accounts,
				"branch": self.branch
		})

		if self.advance_amount:
			je.save(ignore_permissions = True)
			self.db_set("journal_entry", je.name)
			self.db_set("journal_entry_status", "Forwarded to accounts for processing payment on {0}".format(now_datetime().strftime('%Y-%m-%d %H:%M:%S')))
			frappe.msgprint(_('{} posted to accounts').format(frappe.get_desk_link(je.doctype,je.name)))
	
