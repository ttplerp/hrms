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
								select e.name as employee, e.employee_name, e.department, e.designation
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
    def create_performance_evaluation(self):
        """
        Creates perforacne evaluation for selected employees if not created
        """
        self.check_permission("write")
        self.created = 1
        emp_list = [d.employee for d in self.get_emp_list()]

        if emp_list:
            args = frappe._dict(
                {
                    "fiscal_year": self.fiscal_year,
                    "month": self.month,
                    "month_name": self.month_name,
                    # "start_date": self.start_date,
                    # "end_date": self.end_date,
                    "posting_date": self.posting_date,
                    "company": self.company,
                    "process_performance_evaluation": self.name,
                }
            )
            # frappe.throw("<pre>{}</pre>".format(frappe.as_json(args)))
            
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


def create_performance_evaluation_for_employees(
    employees, args, title=None, publish_progress=True
):
    performance_evaluation_exists_for = get_existing_performance_evaluation(
        employees, args
    )
    count = 0
    successful = 0
    failed = 0
    process_performance_evaluation = frappe.get_doc(
        "Process Performance Evaluation", args.process_performance_evaluation
    )

    process_performance_evaluation.set("employees_failed", [])
    refresh_interval = 25
    total_count = len(set(employees))

    for emp in process_performance_evaluation.get("employees"):
        employee_group = frappe.get_value("Employee", emp.employee, "employee_group")
        if not employee_group:
            frappe.throw(_("Set Employee Group for emplyee ID {}".format(emp.employee)))
        if (
            emp.employee in employees
            and emp.employee not in performance_evaluation_exists_for
        ):
            error = None
            args.update(
                {
                    "doctype": "Performance Evaluation",
                    "employee": emp.employee,
                    "employee_group": employee_group,
                }
            )
            ppe_detail = frappe.get_doc("PPE Employee Detail", emp.name)

            try:
                pe = frappe.get_doc(args)
                pe.insert()
                successful += 1
                ppe_detail.db_set("performance_evaluation", pe.name)
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
                        " Processing {}: ".format(pe.name if pe else emp.employee)
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
