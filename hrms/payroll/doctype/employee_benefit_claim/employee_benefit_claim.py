# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
# from __future__ import unicode_literals
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, nowdate
from datetime import date
# from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
# from erpnext.accounts.doctype.hr_accounts_settings.hr_accounts_settings import get_bank_account
from hrms.payroll.doctype.salary_structure.salary_structure import get_basic_and_gross_pay, get_salary_tax
from hrms.hr.hr_custom_functions import get_salary_tax
from hrms.hr.doctype.leave_application.leave_application import get_leave_balance_on, get_leaves_for_period
import math

class EmployeeBenefitClaim(Document):
	def validate(self):
		# validate_workflow_states(self)
		self.check_duplicates()
		self.validate_benefits()
		# notify_workflow_states(self)
		self.set_total()

	def on_submit(self):
		if self.purpose == "Separation":
			self.update_employee()
		self.post_journal_entry()
		self.check_leave_encashment()
		self.update_reference()

	def on_cancel(self):
		self.check_journal_entry()
		self.check_leave_encashment()

	def check_duplicates(self):
		if self.employee_separation_id:
			for r in frappe.db.get_all("Employee Benefit Claim", {"employee_separation_id": self.employee_separation_id, \
					"name": ("!=", self.name), "docstatus": ("!=", 2)}):
				frappe.throw(_("Separation Benefits for this employee already processed via {}").format(frappe.get_desk_link("Employee Benefit Claim", r.name)))
		
		if self.employee_transfer_id:
			for r in frappe.db.get_all("Employee Benefit Claim", {"employee_transfer_id": self.employee_transfer_id, \
					"name": ("!=", self.name), "docstatus": ("!=", 2)}):
				frappe.throw(_("Transfer Benefits for this employee already processed via {}").format(frappe.get_desk_link("Employee Benefit Claim", r.name)))

	def update_reference(self):
		if self.employee_separation_id:
			id = frappe.get_doc("Employee Separation",self.employee_separation_id)
			id.employee_benefit_claim_status = "Claimed"
			id.benefit_claim_reference = self.name
			id.save()
		elif self.employee_transfer_id:
			id = frappe.get_doc("Employee Transfer",self.employee_transfer_id)
			id.employee_benefit_claim_status = "Claimed"
			id.save()
		 
		# if self.deduction_details:
		# 	for a in self.deduction_details:
		# 		if a.deduction_type in ("Salary Advance Deduction"):
		# 			ssd = frappe.db.sql("select name from `tabSalary Detail` where salary_component = '{0}' and parent = '{1}' and total_outstanding_amount > 0""".format(a.deduction_type, a.salary_structure_id))[0][0]
		# 			doc = frappe.get_doc("Salary Detail", ssd)
		# 			doc.db_set("total_outstanding_amount",flt(doc.total_outstanding_amount,2)-flt(a.amount,2))
		# 			doc.db_set("total_deducted_amount",flt(doc.total_deducted_amount,2)+flt(a.amount,2))

	def validate_benefits(self):
		emp = frappe.db.sql("""SELECT employment_type, grade, employee_group, date_of_joining,
						TIMESTAMPDIFF(YEAR, date_of_joining, "{separation_date}") years_in_service
					FROM `tabEmployee` e
					WHERE e.name = "{employee}"
                """.format(employee = self.employee, separation_date = self.separation_date), as_dict=True)[0]

		if str(self.separation_date) < str(emp.date_of_joining):
			frappe.throw(_("<b>Separation Date</b> cannot be earlier to Employee's <b>Data Of Joining</b>"))

		for a in self.items:
			if a.benefit_type == "Balance EL reimbursement" and self.purpose != "Separation":
				frappe.throw(_("Row#{}: Leave Encashment cannot be claimed for purpose <b>{}</b>").format(a.idx, self.purpose))
			elif a.benefit_type == "Gratuity":
				if emp.employment_type != "Contract":
					if emp.years_in_service < 5 and emp.employee_group != "ESP":
						frappe.throw(_("Row#{}: Employee should have minimum of <b>5</b> years in service for Gratuity. Only <b>{0}</b> year(s) in Service as of now").format(a.idx, emp.years_in_service))
				elif emp.employee_group == "ESP" and emp.years_in_service < 1:
					frappe.throw(_("Row#{}: <b>ESP</b> Employee should have minimum of <b>1</b> year in service for Gratuity").format(a.idx))
			# elif a.benefit_type == "Carriage Charges":
			# 	if flt(a.amount,2) > flt(emp.carriage_ceiling,2):
			# 		frappe.throw("Carriage Charges <b>{0}</b> is exceeding the ceiling of {1}".format(flt(a.amount), flt(emp.carriage_ceiling)))

	def set_total(self):
		''' validate amounts in benefits and deductions '''
		self.total_amount = self.total_deducted_amount = self.net_amount = 0
		for e in self.items:
			e.amount, e.tax_amount, e.net_amount = flt(e.amount,2), flt(e.tax_amount,2), flt(e.net_amount,2)
			if flt(e.amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")
			elif flt(e.tax_amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Tax Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")
			elif flt(e.net_amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Net Amount</b> for <b>{}</b>").format(e.idx, e.benefit_type), title="Benefit Details")

			self.total_amount 			+= flt(e.amount,2)
			self.total_deducted_amount 	+= flt(e.tax_amount,2)
		for d in self.deduction_details:
			d.amount = flt(d.amount,2)
			if flt(d.amount) < 0:
				frappe.throw(_("Row#{}: Invalid <b>Amount</b> for <b>{}</b>").format(d.idx, d.deduction_type), title="Deduction Details")
			self.total_deducted_amount += flt(d.amount)
		self.net_amount = self.total_amount - self.total_deducted_amount

		# if flt(self.total_deducted_amount,2) > flt(self.total_amount):
		# 	frappe.throw(_("<b>Total Deduction Amount</b> cannot be more than Total Benefits"))

		self.net_amount = flt(self.total_amount) - flt(self.total_deducted_amount)

	def post_journal_entry(self):
		emp = frappe.get_doc("Employee", self.employee)

		je = frappe.new_doc("Journal Entry")
		je.flags.ignore_permissions=1
		je.branch = emp.branch
		je.posting_date = self.posting_date
		je.title = str(self.purpose) + " Benefit (" + str(self.employee_name) + ")"
		je.voucher_type = 'Journal Entry'
		je.naming_series = 'Journal Voucher'
		je.remark = str(self.purpose) + ' Benefit payments for ' + str(self.employee_name) + "("+str(self.employee)+")";

		Company = "State Mining Corporation Ltd"
		tax_account = frappe.db.get_value("Company",Company,"Salary_tax_account")
		expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")

		# Benefits
		for a in self.items:
			if not flt(a.amount):
				continue

			account_type = frappe.db.get_value("Account", a.gl_account, "account_type")
			party_type, party = None, None
			if account_type in ('Payable', 'Receivable'):
				party_type = "Employee"
				party = self.employee

			je.append("accounts", {
				"account": a.gl_account,
				"debit_in_account_currency": flt(a.amount,2),
				"debit": flt(a.amount,2),
				"party_type": party_type,
				"party": party,
				"cost_center": emp.cost_center,
				"business_activity": emp.business_activity,
				"reference_type": "Employee Benefit Claim",
				"reference_name": self.name,
			})

			if flt(a.tax_amount) > 0:
				je.append("accounts", {
					"account": tax_account,
					"credit_in_account_currency": flt(a.tax_amount,2),
					"credit": flt(a.tax_amount,2),
					"cost_center": emp.cost_center,
					"business_activity": emp.business_activity,
					"reference_type": "Employee Benefit Claim",
					"reference_name": self.name,
				})

		# # Deductions
		for b in self.deduction_details:
			if not flt(b.amount):
				continue

			account_type = frappe.db.get_value("Account", b.deduction_account, "account_type")
			party_type, party = None, None
			if account_type in ('Payable', 'Receivable'):
				party_type = "Employee"
				party = self.employee

			je.append("accounts", {
				"account": b.deduction_account,
				"credit_in_account_currency": flt(b.amount,2),
				"credit": flt(b.amount,2),
				"party_type": party_type,
				"party": party,
				"cost_center": emp.cost_center,
				"business_activity": emp.business_activity,
				"reference_type": "Employee Benefit Claim",
				"reference_name": self.name,
			})

		# Credit Account
		je.append("accounts", {
			"account": expense_bank_account,
			"credit_in_account_currency" if flt(self.net_amount,2) > 0 else "debit_in_account_currency": abs(flt(self.net_amount,2)),
			"credit" if flt(self.net_amount) > 0 else "debit": abs(flt(self.net_amount,2)),
			"cost_center": emp.cost_center,
			"business_activity": emp.business_activity,
			"reference_type": "Employee Benefit Claim",
			"reference_name": self.name,
		})
		je.insert()
		self.db_set("journal", je.name)
	def check_journal_entry(self):
		if self.journal and frappe.db.exists("Journal Entry", {"name": self.journal, "docstatus": ("!=",2)}):
			frappe.throw("Cancel {} before cancelling this document".format(frappe.get_desk_link("Journal Entry", self.journal)))

	@frappe.whitelist()
	def get_leave_encashment_amount(self, employee, date):
		basic_pay = amount = 0
		query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
		data = frappe.db.sql(query, as_dict=True)
		if not data:
			frappe.throw("Basic Salary is not been assigned to the employee.")
		else:
			for a in data:
				basic_pay += a.amount
		leave_balance = get_leave_balance_on(employee, "Earned Leave", date)
		amount = (flt(basic_pay)/30.0) * flt(leave_balance)
		encashment_tax = get_salary_tax(amount)
		return amount, leave_balance, encashment_tax

	@frappe.whitelist()
	def get_gratuity_amount(self, employee):
		basic_pay = amount = 0
		query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
		data = frappe.db.sql(query, as_dict=True)
		if not data:
			frappe.throw("Basic Salary is not been assigned to the employee.")
		else:
			for a in data:
				basic_pay += a.amount
		date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
		employee_group = frappe.db.get_value("Employee", employee, "employee_group")
		today_date = date.today()
		years_in_service = flt(((today_date - date_of_joining).days)/364)
		years_in_service = math.ceil(years_in_service) if (years_in_service - int(years_in_service)) >= 0.5 else math.floor(years_in_service)
		if frappe.db.get_value("Employee", employee, "employment_type") != "Contract":
			if years_in_service < 5 and employee_group != "ESP":
				frappe.throw("Should have minimum of 5 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
		elif employee_group == "ESP" and years_in_service < 1:
			frappe.throw("ESP Employee should have minimum of 1 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
		if years_in_service > 0:
			amount = flt(basic_pay) * years_in_service
		return amount

	@frappe.whitelist()
	def get_basic_pay(self, employee):
		if not frappe.db.exists("Salary Structure", {"employee": employee, "is_active": "Yes"}):
			frappe.throw(_("Active Salary Structure not found for {}").format("Employee", employee))

		amount = frappe.db.sql("""SELECT SUM(amount) 
					FROM `tabSalary Structure` s, `tabSalary Detail` d 
					WHERE s.name = d.parent 
					AND s.employee = "{employee}" 
					AND d.salary_component = 'Basic Pay'
					AND is_active='Yes'""".format(employee=employee))[0][0]
		tax = get_salary_tax(amount)

		return flt(amount,2), flt(tax, 2)

	def check_leave_encashment(self):
		for a in self.items:
			if a.benefit_type == "Balance EL reimbursement":
				balance = 0
				le = frappe.get_doc("Employee Group",frappe.db.get_value("Employee",self.employee,"employee_group"))
				las = frappe.db.sql("""SELECT name FROM `tabLeave Allocation` 
						WHERE employee = "{employee}"
						AND leave_type = "{leave_type}"
						AND "{ason_date}" BETWEEN from_date AND to_date
						AND docstatus = 1
						""".format(employee = self.employee, leave_type = "Earned Leave", 
								ason_date = nowdate()), as_dict=True)
				if flt(a.earned_leave_balance) > flt(le.encashment_lapse):
					a.actual_earned_leave_balance = flt(le.encashment_lapse)
					a.earned_leave_balance = flt(le.encashment_lapse)

				for l in las:
					if l.name != None:
						doc = frappe.get_doc("Leave Allocation", l.name)
						# carry_forwarded = flt(doc.carry_forwarded_leaves_count) - flt(a.difference)
						# balance = flt(doc.new_leaves_allocated) - flt(a.difference)
						balance = -1*(flt(a.earned_leave_balance))
						if self.docstatus == 2:
							# carry_forwarded = flt(doc.carry_forwarded_leaves_count) + flt(a.difference)
							# balance = flt(doc.new_leaves_allocated) + flt(a.difference)
							balance = a.earned_leave_balance
						# if flt(carry_forwarded) > flt(le.encashment_lapse):
						# 	carry_forwarded = le.encashment_lapse
						# if flt(balance) > flt(le.encashment_lapse):
						# 	balance = le.encashment_lapse

						# doc.db_set("carry_forwarded_leaves_count", carry_forwarded)
						doc.db_set("new_leaves_allocated", balance)

					self.create_additional_leave_ledger_entry(doc, balance, nowdate())


	def update_employee(self, cancel=0):
		if cancel == 0:
			emp = frappe.get_doc("Employee", self.employee)
			if emp.status != "Left":
				emp.status = "Left"
				emp.relieving_date = self.separation_date
				emp.reason_for_resignation = self.reason_for_resignation
				history = emp.append("internal_work_history")
				history.reference_doctype = "Employee Separation"
				history.reference_docname = self.employee_separation_id
				history.from_date = self.separation_date
				emp.save()
			sst = frappe.db.sql("""
				select name from `tabSalary Structure` where employee = '{}'
				and is_active = 'Yes'
			""", as_dict=1)
			if sst:
				for a in sst:
					frappe.db.sql("""update `tabSalary Structure` set is_active = 'Yes'
					where name = '{}'""".format(a.name))
			
		# for a in self.items:
		# 	doc = frappe.new_doc("Separation Benefits")
		# 	doc.parent = self.employee
		# 	doc.parentfield = "separation_benefits"
		# 	doc.parenttype = "Employee"
		# 	doc.s_b_type = a.benefit_type
		# 	doc.s_b_currency = a.amount
		# 	doc.save()
		leave_encashed = 0
		for a in self.items:
			if a.benefit_type == "Leave Encashment":
				leave_encashed = 1
		if leave_encashed == 1 and self.purpose == "Employee Separation":
			doc = frappe.get_doc("Employee Separation", self.employee_separation_id)
			frappe.db.sql("""
				update `tabEmployee` set leave_encashed = '{}'
				reason_for_leaving = '{}'
				feedback = '{}'
				encashment_date = '{}'
				where name = '{}'
			""".format('Yes' if cancel == 0 else '', doc.reason_for_separation if cancel == 0 else None, doc.exit_interview if cancel == 0 else None, self.separation_date if cancel == 0 else '', self.employee))
		if leave_encashed == 0 and self.purpose == "Employee Separation":
			doc = frappe.get_doc("Employee Separation", self.employee_separation_id)
			frappe.db.sql("""
				update `tabEmployee` set leave_encashed = '{}'
				reason_for_leaving = '{}'
				feedback = '{}'
				where name = '{}'
			""".format('YNo' if cancel == 0 else '', doc.reason_for_separation if cancel == 0 else None, doc.exit_interview if cancel == 0 else None, self.employee))
		



@frappe.whitelist()
def get_leave_encashment_amount(employee, date):
	basic_pay = amount = 0
	query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
	data = frappe.db.sql(query, as_dict=True)
	if not data:
		frappe.throw("Basic Salary is not been assigned to the employee.")
	else:
		for a in data:
			basic_pay += a.amount
	leave_balance = get_leave_balance_on(employee, "Earned Leave", date)
	amount = (flt(basic_pay)/30.0) * flt(leave_balance)
	encashment_tax = get_salary_tax(amount)
	return amount, leave_balance, encashment_tax

@frappe.whitelist()
def get_gratuity_amount(employee):
	basic_pay = amount = 0
	query = "select amount from `tabSalary Structure` s, `tabSalary Detail` d where s.name = d.parent and s.employee=\'" + str(employee) + "\' and d.salary_component in ('Basic Pay') and is_active='Yes'"
	data = frappe.db.sql(query, as_dict=True)
	if not data:
		frappe.throw("Basic Salary is not been assigned to the employee.")
	else:
		for a in data:
			basic_pay += a.amount
	date_of_joining = frappe.db.get_value("Employee", employee, "date_of_joining")
	employee_group = frappe.db.get_value("Employee", employee, "employee_group")
	today_date = date.today()
	years_in_service = flt(((today_date - date_of_joining).days)/364)
	years_in_service = math.ceil(years_in_service) if (years_in_service - int(years_in_service)) >= 0.5 else math.floor(years_in_service)
	if frappe.db.get_value("Employee", employee, "employment_type") != "Contract":
		if years_in_service < 5 and employee_group != "ESP":
			frappe.throw("Should have minimum of 5 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
	elif employee_group == "ESP" and years_in_service < 1:
		frappe.throw("ESP Employee should have minimum of 1 years in service for Gratuity. Only <b>{0}</b> year/s in Services as of now ".format(years_in_service))
	if years_in_service > 0:
		amount = flt(basic_pay) * years_in_service
	return amount

@frappe.whitelist()
def get_transfer_grant(employee):
	if not frappe.db.exists("Salary Structure", {"employee": employee, "is_active": "Yes"}):
		frappe.throw(_("Active Salary Structure not found for {}").format("Employee", employee))

	amount = frappe.db.sql("""SELECT SUM(amount) 
				FROM `tabSalary Structure` s, `tabSalary Detail` d 
				WHERE s.name = d.parent 
				AND s.employee = "{employee}" 
				AND d.salary_component IN ('Basic Pay','Banking Allowance','Corporate Allowance') 
				AND is_active='Yes'""".format(employee=employee))[0][0]
	return flt(amount,2)

@frappe.whitelist()
def get_outstanding_amount(employee, salary_component):
	if not frappe.db.exists("Salary Structure", {"employee": employee, "is_active": "Yes"}):
		frappe.throw(_("Active Salary Structure not found for {}").format("Employee", employee))

	oa = frappe.db.sql("""SELECT SUM(d.total_outstanding_amount), d.parent, d.reference_number
				FROM `tabSalary Structure` s, `tabSalary Detail` d 
				WHERE s.name = d.parent 
				AND s.employee = "{employee}" 
				AND d.salary_component = "{salary_component}"
				AND s.is_active='Yes'""".format(employee=employee, salary_component=salary_component))[0]
	return flt(oa[0],2), oa[1], oa[2]