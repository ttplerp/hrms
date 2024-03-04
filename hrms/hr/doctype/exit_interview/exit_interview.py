# -*- coding: utf-8 -*-
# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.naming import make_autoname
from frappe.model.document import Document
from frappe import _

class ExitInterview(Document):
	def validate(self):
		self.validate_checkbox_answers()

	def on_submit(self):
		if not self.employee_separation:
			frappe.throw(_("Exit interview must be created from employee separation."))

		frappe.db.set_value("Employee Separation", self.employee_separation, "exit_interview", self.name)

	def validate_checkbox_answers(self):
		for js in self.job_satisfaction:
			if js.strongly_agree == 0 and js.agree == 0 and js.disagree == 0 and js.strongly_disagree == 0:
				frappe.throw("Please select an answer for Question: {}, in Part III: Job Satisfaction".format(js.question))
		for m in self.management:
			if m.strongly_agree == 0 and m.agree == 0 and m.disagree == 0 and m.strongly_disagree == 0:
				frappe.throw("Please select an answer for Question: {}, in Part IV: Management".format(m.question))
		for r in self.remuneration_benefits:
			if r.strongly_agree == 0 and r.agree == 0 and r.disagree == 0 and r.strongly_disagree == 0:
				frappe.throw("Please select an answer for Question: {}, in Part V: Remuneration & Benefits".format(r.question))
		for c in self.the_company:
			if c.strongly_agree == 0 and c.agree == 0 and c.disagree == 0 and c.strongly_disagree == 0:
				frappe.throw("Please select an answer for Question: {}, in Part VI : The Company".format(c.question))
		for s in self.supervisor:
			if s.strongly_agree == 0 and s.agree == 0 and s.disagree == 0 and s.strongly_disagree == 0:
				frappe.throw("Please select an answer for Question: {}, in Part VII : Supervisor".format(s.question))
	def autoname(self):
		name = "HR-EXIT-INT-"
		self.name = make_autoname(str(name)+".YYYY.-.####")
	@frappe.whitelist()
	def get_questions(self):
		job_satisfaction = frappe.db.sql("""
			SELECT 
				eiq.question,
				"0" as strongly_disagree,
				"0" as disagree,
				"0" as agree,
				"0" as strongly_agree
			FROM 
				`tabExit Interview Question` eiq 
			WHERE
				eiq.type = '{}' 
			ORDER BY eiq.idx
			""".format(self.part_iii), as_dict=True)
		management = frappe.db.sql("""
			SELECT 
				eiq.question,
				"0" as strongly_disagree,
				"0" as disagree,
				"0" as agree,
				"0" as strongly_agree
			FROM 
				`tabExit Interview Question` eiq 
			WHERE
				eiq.type = '{}' 
			ORDER BY eiq.idx
			""".format(self.part_iv), as_dict=True)


		remuneration = frappe.db.sql("""
			SELECT 
				eiq.question,
				"0" as strongly_disagree,
				"0" as disagree,
				"0" as agree,
				"0" as strongly_agree
			FROM 
				`tabExit Interview Question` eiq 
			WHERE
				eiq.type = '{}' 
			ORDER BY eiq.idx
			""".format(self.part_v), as_dict=True)

		company = frappe.db.sql("""
			SELECT 
				eiq.name as table_name,
				eiq.question,
				"0" as strongly_disagree,
				"0" as disagree,
				"0" as agree,
				"0" as strongly_agree
			FROM 
				`tabExit Interview Question` eiq 
			WHERE
				eiq.type = '{}' 
			ORDER BY eiq.idx
			""".format(self.part_vi), as_dict=True)

		supervisor = frappe.db.sql("""
			SELECT 
				eiq.question,
				"0" as strongly_disagree,
				"0" as disagree,
				"0" as agree,
				"0" as strongly_agree
			FROM 
				`tabExit Interview Question` eiq 
			WHERE
				eiq.type = '{}' 
			ORDER BY eiq.idx
			""".format(self.part_vii), as_dict=True)
		
		self.set('job_satisfaction', [])
		# frappe.throw(str(data))
		if job_satisfaction:
			for js in job_satisfaction:
				row = self.append('job_satisfaction', {})
				row.update(js)

		self.set('management', [])
		if management:
			for m in management:
				row = self.append('management', {})
				row.update(m)
		
		self.set('remuneration_benefits', [])
		if remuneration:
			for r in remuneration:
				row = self.append('remuneration_benefits', {})
				row.update(r)

		self.set('the_company', [])
		if company:
			for c in company:
				row = self.append('the_company', {})
				row.update(c)
		
		self.set('supervisor', [])
		if supervisor:
			for s in supervisor:
				row = self.append('supervisor', {})
				row.update(s)

	
