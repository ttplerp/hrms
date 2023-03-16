# Copyright (c) 2018, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, nowdate, today
from frappe.utils import date_diff, flt, cint
from hrms.hr.doctype.leave_application.leave_application import get_leaves_for_period
from hrms.hr.doctype.leave_ledger_entry.leave_ledger_entry import create_leave_ledger_entry
from hrms.hr.utils import set_employee_name, validate_active_employee
from hrms.payroll.doctype.salary_structure.salary_structure import get_basic_and_gross_pay, get_salary_tax
from hrms.hr.hr_custom_functions import get_salary_tax
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states

class LeaveEncashment(Document):
	def validate(self):
		validate_workflow_states(self)
		set_employee_name(self)
		validate_active_employee(self.employee)
		self.get_leave_details_for_encashment()
		self.check_duplicate_entry()
		if not self.encashment_date:
			self.encashment_date = getdate(nowdate())
		if self.workflow_state != "Approved":
			notify_workflow_states(self)


	def before_submit(self):
		if self.encashment_amount <= 0:
			frappe.throw(_("You can only submit Leave Encashment for a valid encashment amount"))

	def on_submit(self):
		self.post_expense_claim()
		self.create_leave_ledger_entry()
		notify_workflow_states(self)

		# self.create_leave_ledger_entry()
	def on_cancel(self):
		if self.leave_allocation:
			frappe.db.set_value(
				"Leave Allocation",
				self.leave_allocation,
				"total_leaves_encashed",
				frappe.db.get_value("Leave Allocation", self.leave_allocation, "total_leaves_encashed")
				- self.encashable_days,
			)
		self.create_leave_ledger_entry(submit=False)

	def post_expense_claim(self):
		cost_center = frappe.get_value("Employee", self.employee, "cost_center")
		branch = frappe.get_value("Employee", self.employee, "branch")
		company =frappe.get_value("Employee", self.employee, "company")
		default_payable_account = frappe.get_cached_value("Company", company, "default_expense_claim_payable_account")
		taxt_account_head = frappe.get_cached_value("Company", company, "salary_tax_account")

		expense_claim 					= frappe.new_doc("Expense Claim")
		expense_claim.flags.ignore_mandatory = True
		expense_claim.company 			= company
		expense_claim.employee 			= self.employee
		expense_claim.payable_account 	= default_payable_account
		expense_claim.cost_center 		= cost_center 
		expense_claim.is_paid 			= cint(0)
		expense_claim.expense_approver	= frappe.db.get_value('Employee',self.employee,'expense_approver')
		expense_claim.branch			= branch

		expense_claim.append('expenses',{
			"expense_date":			nowdate(),
			"expense_type":			self.doctype,
			"amount":				self.basic_pay,
			"sanctioned_amount":	self.basic_pay,
			"reference_type":		self.doctype,
			"reference":			self.name,
			"cost_center":			cost_center
		})
		expense_claim.append('taxes',{
			"account_head":	taxt_account_head,
			"add_or_deduct" :"Deduct",
			"tax_amount":	self.encashment_tax,
			"cost_center":	cost_center,
			"description":	"Leave Encashment Tax"
		})
		expense_claim.docstatus = 0

		expense_claim.save(ignore_permissions=True)
		expense_claim.submit()
		self.db_set("expense_claim", expense_claim.name)
		frappe.db.commit()
		frappe.msgprint(
			_("Expense Claim record {0} created")
			.format("<a href='/app/Form/Expense Claim/{0}'>{0}</a>")
			.format(expense_claim.name))

	def create_leave_ledger_entry(self, submit=True):
		args = frappe._dict(
			leaves=self.encashable_days * -1,
			from_date=self.encashment_date,
			to_date=self.encashment_date,
			is_carry_forward=0
		)
		create_leave_ledger_entry(self, args, submit)

		# create reverse entry for expired leaves
		to_date = self.get_leave_allocation().get('to_date')
		if to_date < getdate(nowdate()):
			args = frappe._dict(
				leaves=self.encashable_days,
				from_date=to_date,
				to_date=to_date,
				is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)
	def check_duplicate_entry(self):
		count = frappe.db.count(self.doctype,{"employee": self.employee, "leave_period": self.leave_period, "leave_type": self.leave_type, "docstatus": 1}) \
					if frappe.db.count(self.doctype,{"employee": self.employee, "leave_period": self.leave_period, "leave_type": self.leave_type, "docstatus": 1}) else 0
		employee_grp = frappe.db.get_value("Employee",self.employee,"employee_group")
		frequency = frappe.db.get_value("Employee Group",employee_grp,"encashment_frequency")
		
		if flt(count) >= flt(frequency):
			frappe.throw("You had already Encash {} time for leave period {}".format(frappe.bold(count), frappe.bold(self.leave_period)))

	@frappe.whitelist()
	def get_leave_details_for_encashment(self):
		salary_structure =  frappe.db.sql("""select name 
						from `tabSalary Structure`
						where employee='{}'
						and'{}' >= from_date 
						order by from_date desc limit 1""".format(self.employee, self.encashment_date)
					)
		
		if not salary_structure:
			frappe.throw(
				_("No Salary Structure assigned for Employee {0} on given date {1}").format(
					self.employee, self.encashment_date
				)
			)

		if not frappe.db.get_value("Leave Type", self.leave_type, "allow_encashment"):
			frappe.throw(_("Leave Type {0} is not encashable").format(self.leave_type))

		allocation = self.get_leave_allocation()

		if not allocation:
			frappe.throw(
				_("No Leaves Allocated to Employee: {0} for Leave Type: {1}").format(
					self.employee, self.leave_type
				)
			)

		self.leave_balance = (
			allocation.total_leaves_allocated
			- allocation.carry_forwarded_leaves_count
			# adding this because the function returns a -ve number
			+ get_leaves_for_period(
				self.employee, self.leave_type, allocation.from_date, self.encashment_date
			)
		)
		employee_group = frappe.db.get_value("Employee", self.employee, "employee_group")
		encashable_days = frappe.db.get_value("Employee Group", employee_group, "max_encashment_days")

		if self.leave_balance < frappe.db.get_value("Employee Group", employee_group, "max_encashment_days"):
			frappe.msgprint(_("Minimum '{}' days is Mandatory for Encashment").format(cint(encashable_days)),title="Leave Balance")
		
		self.encashable_days = encashable_days if encashable_days > 0 else 0
		self.encashment_days = encashable_days
		# per_day_encashment = frappe.db.get_value("Salary Structure", salary_structure, "leave_encashment_amount_per_day")
		
		# getting encashment amount from salary structure
		pay = get_basic_and_gross_pay(employee=self.employee, effective_date=today())
		leave_encashment_type = frappe.db.get_value("Employee Group", employee_group, "leave_encashment_type")
		if leave_encashment_type == "Flat Amount":
			self.flat_amount	   	= flt(employee_group.leave_encashment_amount)
			self.encashment_amount 	= flt(employee_group.leave_encashment_amount)
		elif leave_encashment_type == "Basic Pay":
			self.basic_pay			= flt(pay.get("basic_pay"))
			self.encashment_amount 	= (flt(pay.get("basic_pay"))/30)*flt(self.encashment_days)
		elif leave_encashment_type == "Gross Pay":
			self.gross_pay			= flt(pay.get("gross_pay"))
			self.encashment_amount 	= (flt(pay.get("gross_pay"))/30)*flt(self.encashment_days)
		else:
			self.encashment_amount = 0

		self.leave_encashment_type = leave_encashment_type
		# self.salary_structure = salary_structure
		self.encashment_tax = get_salary_tax(self.encashment_amount)
		# frappe.throw(str(self.encashment_tax))
		self.payable_amount = flt(self.encashment_amount) - flt(self.encashment_tax)

		self.leave_allocation = allocation.name
		return True

	def get_leave_allocation(self):
		date = self.encashment_date or getdate()

		LeaveAllocation = frappe.qb.DocType("Leave Allocation")
		leave_allocation = (
			frappe.qb.from_(LeaveAllocation)
			.select(
				LeaveAllocation.name,
				LeaveAllocation.from_date,
				LeaveAllocation.to_date,
				LeaveAllocation.total_leaves_allocated,
				LeaveAllocation.carry_forwarded_leaves_count,
			)
			.where(
				((LeaveAllocation.from_date <= date) & (date <= LeaveAllocation.to_date))
				& (LeaveAllocation.docstatus == 1)
				& (LeaveAllocation.leave_type == self.leave_type)
				& (LeaveAllocation.employee == self.employee)
			)
		).run(as_dict=True)

		return leave_allocation[0] if leave_allocation else None

	def create_leave_ledger_entry(self, submit=True):
		args = frappe._dict(
			leaves=self.encashable_days * -1,
			from_date=self.encashment_date,
			to_date=self.encashment_date,
			is_carry_forward=0,
		)
		create_leave_ledger_entry(self, args, submit)

		# create reverse entry for expired leaves
		leave_allocation = self.get_leave_allocation()
		if not leave_allocation:
			return

		to_date = leave_allocation.get("to_date")
		if to_date < getdate(nowdate()):
			args = frappe._dict(
				leaves=self.encashable_days, from_date=to_date, to_date=to_date, is_carry_forward=0
			)
			create_leave_ledger_entry(self, args, submit)


def create_leave_encashment(leave_allocation):
	"""Creates leave encashment for the given allocations"""
	for allocation in leave_allocation:
		if not get_assigned_salary_structure(allocation.employee, allocation.to_date):
			continue
		leave_encashment = frappe.get_doc(
			dict(
				doctype="Leave Encashment",
				leave_period=allocation.leave_period,
				employee=allocation.employee,
				leave_type=allocation.leave_type,
				encashment_date=allocation.to_date,
			)
		)
		leave_encashment.insert(ignore_permissions=True)

def get_permission_query_conditions(user):
	if not user: user = frappe.session.user
	user_roles = frappe.get_roles(user)

	if user == "Administrator":
		return
	if "HR User" in user_roles or "HR Manager" in user_roles:
		return

	return """(
		`tabLeave Encashment`.owner = '{user}'
		or
		exists(select 1
				from `tabEmployee`
				where `tabEmployee`.name = `tabLeave Encashment`.employee
				and `tabEmployee`.user_id = '{user}')
		or
		(`tabLeave Encashment`.approver = '{user}' and `tabLeave Encashment`.workflow_state not in ('Draft','Rejected','Approved','Cancelled'))
	)""".format(user=user)