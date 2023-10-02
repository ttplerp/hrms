# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import (
    cint,
    flt,
    nowdate,
    add_days,
    getdate,
    fmt_money,
    add_to_date,
    DATE_FORMAT,
    date_diff,
    get_last_day,
)
from frappe.model.document import Document


class ProcessPerformanceEvaluation(Document):
    def validate(self):
        self.set_month_dates()

    def set_month_dates(self):
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        month = str(int(months.index(self.month_name)) + 1).rjust(2, "0")

        # month_start_date = "-".join([str(self.fiscal_year), month, "01"])
        # month_end_date = get_last_day(month_start_date)

        # self.start_date = month_start_date
        # self.end_date = month_end_date
        self.month = month

    def check_mandatory(self):
        for fieldname in ["company", "fiscal_year", "month"]:
            if not self.get(fieldname):
                frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

    def get_filter_condition(self):
        self.check_mandatory()
        cond = ""
        for f in ["company", "branch", "department", "designation", "employee"]:
            if self.get(f):
                cond += " and e." + f + " = '" + self.get(f).replace("'", "'") + "'"
        return cond

    def get_emp_list(self, process_type=None):
        self.set_month_dates()

        cond = self.get_filter_condition()
        emp_list = frappe.db.sql(
            """
								select e.name as employee, e.employee_name, e.department, e.designation, e.branch
			   					from `tabEmployee` e
			   					where not exists(
									select 1 from `tabPerformance Evaluation` as pe
			   						where pe.employee = e.name
			   						and pe.docstatus != 2
			   						and pe.fiscal_year = '{}'
			   						and pe.month = '{}'
								)
			   					{}
			   					order by e.branch, e.name
								""".format(
                self.fiscal_year, self.month, cond
            ),
            as_dict=True,
        )
        if not emp_list:
            frappe.msgprint(
                _("No employees found for processing or performance evaluation is already created")
            )
        return emp_list
    
    def get_mr_emp_list(self, process_type=None):
        condition = ""
        # for f in ["company", "branch", "designation", "mr_employee"]:
        #     if self.get(f):
        #         condition += " and e." + f + " = '" + self.get(f).replace("'", "'") + "'"
        if self.mr_employee:
            condition += " and e.name = '"+str(self.mr_employee).replace("'", "'") + "'"
        if self.branch:
            condition += " and e.branch = '"+str(self.branch).replace("'", "'") + "'"
        mr_emp_list = frappe.db.sql("""
                                    select e.name as mr_employee, e.person_name as mr_employee_name,
                                    e.designation, e.branch from `tabMuster Roll Employee` e
                                    where not exists(
                                        select 1 from `tabPerformance Evaluation` as pe
                                        where pe.mr_employee = e.name
                                        and pe.docstatus != 2
                                        and pe.fiscal_year = '{}'
                                        and pe.month = '{}'
                                    ) {}
                                    """.format(self.fiscal_year, self.month, condition), as_dict=True)
        if not mr_emp_list:
            frappe.msgprint(
                _("No MR employees found for processing or performance evaluation is already created")
            )
        return mr_emp_list

    @frappe.whitelist()
    def get_employee_details(self):
        self.set("employees", [])
        employees = self.get_emp_list()
        if not employees:
            frappe.throw(_("No employees for the mentioned criteria"))

        for a in employees:
            self.append("employees", a)

        self.number_of_employees = len(employees)
        return self.number_of_employees
    
    @frappe.whitelist()
    def get_mr_employee_details(self):
        self.set("mr_employees", [])
        mr_employees = self.get_mr_emp_list()
        if not mr_employees:
            frappe.throw(_("No employees for the mentioned criteria"))

        for a in mr_employees:
            self.append("mr_employees", a)
        
        self.number_of_mr_employees = len(mr_employees)
        return self.number_of_mr_employees

    @frappe.whitelist()
    def create_performance_evaluation(self):
        """
        Creates performance evaluation for selected employees if not created
        """
        self.check_permission("write")
        self.created = 1
        emp_list = [d.employee for d in self.get_emp_list()]
        mr_emp_list = [d.mr_employee for d in self.get_mr_emp_list()]

        args = frappe._dict({
            "fiscal_year": self.fiscal_year,
            "month": self.month,
            "month_name": self.month_name,
            "posting_date": self.posting_date,
            "company": self.company,
            "process_performance_evaluation": self.name,
        })
        
        if emp_list:        
            if len(emp_list) > 300:
                frappe.enqueue(
                    create_performance_evaluation_for_employees,
                    timeout=600,
                    employee=emp_list,
                    args=args,
                )
            else:
                create_performance_evaluation_for_employees(
                    emp_list, args, publish_progress=False
                )
                # since this method is called via frm.call this doc needs to be updated manually
                self.reload()

        if mr_emp_list:
            if len(mr_emp_list) > 300:
                frappe.enqueue(create_performance_evaluation_for_mr_employees, timeout=600, employee=mr_emp_list, args=args,)
            else:
                create_performance_evaluation_for_mr_employees(mr_emp_list, args, publish_progress=True)
                self.reload()

def get_existing_performance_evaluation(employees, args):
    return frappe.db.sql_list(
        """
			select distinct employee from `tabPerformance Evaluation`
            where docstatus !=2 and company = %s
            and month = %s
            and employee in (%s)
            """
        % ("%s", "%s", ", ".join(["%s"] * len(employees))),
        [args.company, args.month] + employees,
    )

def get_eval_list(employee):
    evaluator_list = frappe.db.sql("""
                select evaluator from `tabPerformance Evaluator` where parent = '{}'
            """.format(employee), as_dict=True)
    return evaluator_list

def get_work_competency(emp_group):
    competency = frappe.db.sql("""
                select wc.competency, wc.weightage, wc.rating_4, wc.rating_3, wc.rating_2, wc.rating_1
                from `tabWork Competency` wc
                inner join `tabWork Competency Item` wci
                on wc.name = wci.parent
                where wci.applicable = 1
                and wci.employee_group = '{}'
                order by wc.competency
            """.format(emp_group), as_dict=True)
    return competency

def create_performance_evaluation_for_mr_employees(mr_employees, args, title=None, publish_progress=True):
    performance_evaluation_exists_for = get_existing_performance_evaluation(mr_employees, args)
    count = 0
    process_performance_evaluation = frappe.get_doc("Process Performance Evaluation", args.process_performance_evaluation)
    for mr_emp in process_performance_evaluation.get("mr_employees"):
        pms_employee_group = frappe.get_value("Muster Roll Employee", mr_emp.mr_employee, "pms_employee_group")
        if not pms_employee_group:
            frappe.throw(_("Set PMS Employee Group for Muster Roll Emplyee ID {}".format(mr_emp.mr_employee)))

        if (mr_emp.mr_employee in mr_employees and mr_emp.mr_employee not in performance_evaluation_exists_for):
            evaluator_list = get_eval_list(mr_emp.mr_employee)
            if not evaluator_list: 
                frappe.throw('Set Evaluator for Muster Roll Employee ID {} '.format(mr_emp.mr_employee))
            
            evals = []
            for a in evaluator_list:
                evals.append(a.evaluator)
            
            data_wc = get_work_competency(pms_employee_group)
            if not data_wc:
                frappe.throw(_('There is no Work Competency defined for Muster Roll Employee'))

            for ev in evals:
                if ev:
                    doc = frappe.new_doc("Performance Evaluation")
                    doc.mr_employee = mr_emp.mr_employee
                    doc.employee_name = mr_emp.mr_employee_name
                    doc.designation = mr_emp.designation
                    doc.branch = mr_emp.branch
                    doc.for_muster_roll_employee = 1
                    doc.employee_group = pms_employee_group
                    doc.fiscal_year = args.get("fiscal_year")
                    doc.month = args.get("month")
                    doc.month_name = args.get("month_name")
                    doc.posting_date = args.get("posting_date")
                    doc.company = args.get("company")
                    doc.process_performance_evaluation = args.get("process_performance_evaluation")
                    if frappe.db.exists("Muster Roll Employee", {"name": ev}):
                        # doc.document_type = "Muster Roll Employee"
                        doc.evaluator = str(ev)
                        doc.evaluator_name = frappe.get_value("Muster Roll Employee", ev, "person_name")
                        doc.evaluator_user_id = frappe.get_value("Muster Roll Employee", ev, "user_id")
                    else:
                        # doc.document_type = "Employee"
                        doc.evaluator = str(ev)

                    doc.set('work_competency', [])
                    for d in data_wc:
                        row = doc.append('work_competency', {})
                        row.update(d)
                        row.evaluator = 0

                    ppe_detail = frappe.get_doc("PPE MR Employee Detail", mr_emp.name)
                    try:
                        doc.save()
                        ppe_detail.db_set("performance_evaluation", doc.name)
                    except Exception as e:
                        error = str(e)
                    count += 1

    process_performance_evaluation.reload()

def create_performance_evaluation_for_employees(employees, args, title=None, publish_progress=True):
    performance_evaluation_exists_for = get_existing_performance_evaluation(employees, args)
    count = 0
    successful = 0
    failed = 0
    process_performance_evaluation = frappe.get_doc("Process Performance Evaluation", args.process_performance_evaluation)

    process_performance_evaluation.set("employees_failed", [])
    refresh_interval = 25
    total_count = len(set(employees))

    for emp in process_performance_evaluation.get("employees"):
        employee_group = frappe.get_value("Employee", emp.employee, "employee_group")
        if not employee_group:
            frappe.throw(_("Set Employee Group for emplyee ID {}".format(emp.employee)))
        
        if (emp.employee in employees and emp.employee not in performance_evaluation_exists_for):
            evaluator_list = frappe.db.sql("""
                select evaluator from `tabPerformance Evaluator` where parent = {}
            """.format(emp.employee), as_dict=True)

            if not evaluator_list: 
                frappe.throw('Set Evaluator for Employee ID {} '.format(emp.employee))

            evals = []
            for a in evaluator_list:
                evals.append(a.evaluator)

            error = None

            # get work competency
            data = frappe.db.sql("""
                select wc.competency, wc.weightage, wc.rating_4, wc.rating_3, wc.rating_2, wc.rating_1
                from `tabWork Competency` wc
                inner join `tabWork Competency Item` wci
                on wc.name = wci.parent
                where wci.applicable = 1
                and wci.employee_group = '{}'
                order by wc.competency
            """.format(employee_group), as_dict=True)

            if not data:
                frappe.throw(_('There is no Work Competency defined'))

            for ev in evals:
                if ev:
                    doc = frappe.new_doc("Performance Evaluation")
                    doc.employee = emp.employee
                    doc.employee_name = emp.employee_name
                    doc.designation = emp.designation
                    doc.branch = emp.branch
                    doc.employee_group = employee_group
                    doc.fiscal_year = args.get("fiscal_year")
                    doc.month = args.get("month")
                    doc.month_name = args.get("month_name")
                    doc.posting_date = args.get("posting_date")
                    doc.company = args.get("company")
                    doc.process_performance_evaluation = args.get("process_performance_evaluation")
                    if frappe.db.exists("Muster Roll Employee", {"name": ev}):
                        # doc.document_type = "Muster Roll Employee"
                        doc.evaluator = str(ev)
                        doc.evaluator_name = frappe.get_value("Muster Roll Employee", ev, "person_name")
                        doc.evaluator_user_id = frappe.get_value("Muster Roll Employee", ev, "user_id")
                    else:
                        # doc.document_type = "Employee"
                        doc.evaluator = str(ev)

                    doc.set('work_competency', [])
                    for d in data:
                        row = doc.append('work_competency', {})
                        row.update(d)
                        row.evaluator = 0
                    ppe_detail = frappe.get_doc("PPE Employee Detail", emp.name)
                    try:
                        doc.save()
                        successful += 1
                        ppe_detail.db_set("performance_evaluation", doc.name)
                    except Exception as e:
                        error = str(e)
                        failed += 1
                    count += 1

            # ppe_detail.db_set("performance_evaluation", pe.name)
            if error:
                ppe_detail.db_set("status", "Failed")
                ppe_detail.db_set("error", error)
                process_performance_evaluation.append(
                    "employees_failed",
                    {
                        "employee": emp.employee,
                        "employee_name": emp.employee_name,
                        "status": "Failed",
                        "error": error,
                    },
                )
            else:
                ppe_detail.db_set("status", "Success")

            if publish_progress:
                show_progress = 0
                if count <= refresh_interval:
                    show_progress = 1
                elif refresh_interval > total_count:
                    show_progress = 1
                elif count % refresh_interval == 0:
                    show_progress = 1
                if show_progress:
                    description = (
                        " Processing {}: ".format(doc.name if doc else emp.employee)
                        + "["
                        + str(count)
                        + "/"
                        + str(total_count)
                        + "]"
                    )
                    frappe.publish_progress(
                        count
                        * 100
                        / len(set(employees) - set(performance_evaluation_exists_for)),
                        title=title
                        if title
                        else _("Creating Performance Evaluation..."),
                        description=description,
                    )
                    pass
    process_performance_evaluation.db_set("performance_evaluation_created", 0 if failed else 1)
    process_performance_evaluation.db_set(
        "successful", cint(process_performance_evaluation.successful) + cint(successful)
    )
    process_performance_evaluation.db_set(
        "failed",
        cint(process_performance_evaluation.number_of_employees)
        - (cint(process_performance_evaluation.successful)),
    )
    process_performance_evaluation.reload()
