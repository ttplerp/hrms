# Copyright (c) 2023, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe


# def execute(filters=None):
# 	columns = get_columns()
# 	data = get_data(filters)
# 	return columns, data
# def get_columns():
# 	columns = [
# 		  {
#             'fieldname': 'name',
#             'label': 'Reference Name',
#             'fieldtype': 'Link',
#             'options': 'Employee Advance',
# 			'link' : 'id'
#         },
#         {
#             'fieldname': 'employee_name',
#             'label': 'Employee Name',
#             'fieldtype': 'Read Only',
#             'options': 'Employee Name'
#         },
#         {
#             'fieldname': 'advance_type',
#             'label': 'Advance Type',
#             'fieldtype': 'Select',
#             'options': 'Advance Type'
#         },
# 		{
#             'fieldname': 'month',
#             'label': 'Month',
#             'fieldtype': 'Int',
#             'options': 'month'
#         },
		
# 		 {
#             'fieldname': 'advance_amount',
#             'label':'Advance Amount',
#             'fieldtype': 'Int',
#             'options': 'Advance Amount'
#         },
# 		 {
#             'fieldname': 'deduction_month',
#             'label': 'No.of Installments',
#             'fieldtype': 'Int',
#             'options': 'No.of Installments'
#         },
# 		 {
#             'fieldname': 'recovery_start_date',
#             'label': 'Recovery Start Date',
#             'fieldtype': 'Date',
#             'options': 'Recovery Start Date'
#         },
# 		 {
#             'fieldname': 'recovery_end_date',
#             'label': 'Recovery End Date',
#             'fieldtype': 'Date',
#             'options': 'Recovery End Date'
#         },
# 		 {
#             'fieldname': 'total_deducted_amount',
#             'label': 'Total Deducted Amount',
#             'fieldtype': 'Int',
#             'options': 'Total Deducted Amount'
#         },
# 		 {
#             'fieldname': 'total_outstanding_amount',
#             'label': 'Total Outstanding Amount',
#             'fieldtype': 'Int',
#             'options': 'Total Outstanding Amont'
#         },
# 	]


# 	return columns

# def get_data(filters):
#     conditions = get_conditions(filters)
# 	data = frappe.db.sql(
#      """
#    select
# 	 ea.name,
# 	  ea.employee_name,
# 	   ea.advance_type,
# 	   ea.advance_amount,
	
# 	   ea.deduction_month,
# 	   ea.recovery_start_date,
# 	   ea.recovery_end_date,
# 	   sd.total_deducted_amount,
# 	   sd.total_outstanding_amount,
# 	   ss.month
	   
#    from 
#    `tabEmployee Advance` as ea 
#    join 
#    `tabSalary Detail` as sd 
#    on
#    ea.name = sd.reference_number
#    join `tabSalary Slip` ss on  ss.name = sd.parent
   
# """

     
     
#      ,conditions = conditions,as_dict = True)
	
# 	return data

# def get_conditions(filters):
#     conditions = {key:value for key,value in  filters.items()}
    
#     return conditions



import frappe

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    columns = [
        {
            'fieldname': 'name',
            'label': 'Reference Name',
            'fieldtype': 'Link',
            'options': 'Employee Advance',
            'link': 'id'
        },
        {
            'fieldname': 'employee_name',
            'label': 'Employee Name',
            'fieldtype': 'Read Only',
            'options': 'Employee Name'
        },
        {
            'fieldname': 'advance_type',
            'label': 'Advance Type',
            'fieldtype': 'Select',
            'options': 'Advance Type'
        },
        {
            'fieldname': 'month',
            'label': 'Month',
            'fieldtype': 'Int',
            'options': 'month'
        },
        {
            'fieldname': 'advance_amount',
            'label': 'Advance Amount',
            'fieldtype': 'Int',
            'options': 'Advance Amount'
        },
        {
            'fieldname': 'deduction_month',
            'label': 'No.of Installments',
            'fieldtype': 'Int',
            'options': 'No.of Installments'
        },
        {
            'fieldname': 'recovery_start_date',
            'label': 'Recovery Start Date',
            'fieldtype': 'Date',
            'options': 'Recovery Start Date'
        },
        {
            'fieldname': 'recovery_end_date',
            'label': 'Recovery End Date',
            'fieldtype': 'Date',
            'options': 'Recovery End Date'
        },
        {
            'fieldname': 'total_deducted_amount',
            'label': 'Total Deducted Amount',
            'fieldtype': 'Int',
            'options': 'Total Deducted Amount'
        },
        {
            'fieldname': 'total_outstanding_amount',
            'label': 'Total Outstanding Amount',
            'fieldtype': 'Int',
            'options': 'Total Outstanding Amount'
        },
    ]

    return columns

def get_data(filters):
  
    conditions = get_conditions(filters)
    query = """
        SELECT
            ea.name,
            ea.employee_name,
            ea.advance_type,
            ea.advance_amount,
            ea.deduction_month,
            ea.recovery_start_date,
            ea.recovery_end_date,
            sd.total_deducted_amount,
            sd.total_outstanding_amount,
            ss.month,
            ss.branch
        FROM 
            `tabEmployee Advance` AS ea 
            JOIN `tabSalary Detail` AS sd ON ea.name = sd.reference_number
            JOIN `tabSalary Slip` AS ss ON ss.name = sd.parent
        WHERE
            {conditions}
    """.format(conditions=conditions)

    data = frappe.db.sql(query, filters, as_dict=True)
    return data



def get_conditions(filters):
    conditions = []

    if filters.get('name'):
        conditions.append("ea.name = %(name)s")

    if filters.get('recovery_start_date'):
        conditions.append("ea.recovery_start_date = %(recovery_start_date)s")

    if filters.get('recovery_end_date'):
        conditions.append("ea.recovery_end_date = %(recovery_end_date)s")
    if filters.get('branch'):
        conditions.append("ss.branch = %(branch)s")

    return " AND ".join(conditions) if conditions else "1=1"


