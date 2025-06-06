# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
    if not filters:
        filters = {}
    
    validate_filters(filters)
    
    salary_components = get_salary_components(filters)
    columns = get_columns(salary_components)
    data = get_data(filters, salary_components)
    
    return columns, data

def validate_filters(filters):
    """Validate that required filters are provided"""
    if not filters.get("fiscal_year"):
        frappe.throw(_("Fiscal Year is required"))
    if not filters.get("month"):
        frappe.throw(_("Month is required"))

def get_salary_components(filters):
    """Get all unique salary components from salary slips matching filters"""
    conditions, filters = get_conditions(filters)
    
    components = frappe.db.sql("""
        SELECT DISTINCT salary_component 
        FROM `tabSalary Detail`
        WHERE parent IN (
            SELECT name FROM `tabSalary Slip` 
            WHERE docstatus = 1 {conditions}
        )
        ORDER BY salary_component
    """.format(conditions=conditions), filters, as_dict=True)
    
    return [c['salary_component'] for c in components]

def get_columns(salary_components):
    """Return columns including one for each salary component"""
    base_columns = [
        {"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
        {"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
        {"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 120},
        {"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 120},
        {"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": _("Fiscal Year"), "fieldname": "fiscal_year", "fieldtype": "Link", "options": "Fiscal Year", "width": 100},
        {"label": _("Month"), "fieldname": "month", "fieldtype": "Data", "width": 80},
    ]
    
    # Add a column for each salary component
    component_columns = [
        {
            "label": component, 
            "fieldname": frappe.scrub(component), 
            "fieldtype": "Float", 
            "width": 120
        } 
        for component in salary_components
    ]
    
    # Add total columns
    total_columns = [
        {"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Float", "width": 120},
        {"label": _("Total Deduction"), "fieldname": "total_deduction", "fieldtype": "Float", "width": 120},
        {"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Float", "width": 120},
    ]
    
    return base_columns + component_columns + total_columns

def get_data(filters, salary_components):
    """Get the data for the report with proper filtering"""
    conditions, filters = get_conditions(filters)
    
    # Get base employee data with all filters applied
    employees = frappe.db.sql("""
        SELECT 
            name, employee, employee_name, designation, department,
            company, fiscal_year, month, gross_pay, total_deduction, net_pay
        FROM `tabSalary Slip`
        WHERE docstatus = 1 {conditions}
        ORDER BY employee, fiscal_year, month
    """.format(conditions=conditions), filters, as_dict=1)
    
    if not employees:
        return []
    
    # Get all salary components for the filtered employees
    component_data = frappe.db.sql("""
        SELECT 
            t1.employee,
            t1.fiscal_year,
            t1.month,
            t2.salary_component,
            SUM(t2.amount) as amount
        FROM `tabSalary Slip` t1
        JOIN `tabSalary Detail` t2 ON t2.parent = t1.name
        WHERE t1.docstatus = 1 {conditions}
        GROUP BY t1.employee, t1.fiscal_year, t1.month, t2.salary_component
    """.format(conditions=conditions), filters, as_dict=1)
    
    # Convert month number to name for display
    month_map = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    
    # Organize component data by employee+period
    component_map = {}
    for row in component_data:
        key = (row['employee'], row['fiscal_year'], row['month'])
        if key not in component_map:
            component_map[key] = {}
        component_map[key][row['salary_component']] = row['amount']
    
    # Prepare final data
    data = []
    for emp in employees:
        key = (emp['employee'], emp['fiscal_year'], emp['month'])
        
        # Convert month number to name
        if emp.get("month"):
            emp["month"] = month_map.get(int(emp["month"]), str(emp["month"]))
        
        # Initialize row with employee data
        row = {
            "employee": emp.get("employee"),
            "employee_name": emp.get("employee_name"),
            "designation": emp.get("designation"),
            "department": emp.get("department"),
            "company": emp.get("company"),
            "fiscal_year": emp.get("fiscal_year"),
            "month": emp.get("month"),
            "gross_pay": emp.get("gross_pay", 0),
            "total_deduction": emp.get("total_deduction", 0),
            "net_pay": emp.get("net_pay", 0)
        }
        
        # Add salary components (default to 0 if not present)
        components = component_map.get(key, {})
        for component in salary_components:
            row[frappe.scrub(component)] = components.get(component, 0)
        
        data.append(row)
    
    return data

def get_conditions(filters):
    """Build SQL conditions based on filters"""
    conditions = []
    filters_dict = {}
    
    if filters.get("fiscal_year"):
        conditions.append("fiscal_year = %(fiscal_year)s")
        filters_dict["fiscal_year"] = filters["fiscal_year"]
    
    if filters.get("month"):
        month_num = convert_month_to_number(filters["month"])
        if month_num:
            conditions.append("month = {0}".format(month_num))
    
    if filters.get("company"):
        conditions.append("company = %(company)s")
        filters_dict["company"] = filters["company"]
    
    if filters.get("employee"):
        conditions.append("employee = %(employee)s")
        filters_dict["employee"] = filters["employee"]
    
    if filters.get("department"):
        conditions.append("department = %(department)s")
        filters_dict["department"] = filters["department"]
    
    if filters.get("employment_type"):
        conditions.append("employment_type = %(employment_type)s")
        filters_dict["employment_type"] = filters["employment_type"]
    
    return " AND " + " AND ".join(conditions) if conditions else "", filters_dict

def convert_month_to_number(month):
    """Convert month name to number (1-12)"""
    month_map = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
    }
    return month_map.get(month.lower().strip())