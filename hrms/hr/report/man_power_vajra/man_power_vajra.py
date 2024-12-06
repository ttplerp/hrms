# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns, data = [], []
	designations = get_designation()
	columns = get_columns(designations)
	data = get_data(filters,designations)
	return columns, data


def get_data(filters,designations):
   
    data =  frappe.db.sql(""" 
        SELECT 
		e.cost_center,
		dg.name1 as designation,  
		COUNT(e.name) as employee_count
	FROM 
		`tabEmployee` e
	INNER JOIN 
		`tabDesignation` d ON e.designation = d.name
	INNER JOIN 
		`tabDesignation Group` dg ON d.designation_group = dg.name
	WHERE 
		e.status = 'Active'
	GROUP BY 
 e.cost_center,
		dg.name1;
        """, as_dict=True)
    
    result = {}
    
    
    for row in data:
        cost_center = row['cost_center']
        designation = frappe.scrub(row['designation'])
        employee_count = row['employee_count']
        
        if cost_center not in result:
            result[cost_center] = {"cost_center":cost_center}
            
        result[cost_center][designation] = employee_count
    
    msw_data = frappe.db.sql('''
                             SELECT 
                                multiskilled_workers AS msw, 
                                cost_center, 
                                foreign_workers AS fw, 
                                local_workers AS lw,
                                ojt, 
                                internship, 
                                `leave`, 
                                absent, 
                                present
                            FROM 
                                `tabMuster Roll Attendance for Dashboard` where posting_date= CURDATE();
                             ''', as_dict=True)
    
    msw_att = {}
    for i in msw_data:
        result[i.cost_center]['msw'] = i['msw']
        result[i.cost_center]['fw'] = i['fw']
        result[i.cost_center]['lw'] = i['lw']
        result[i.cost_center]['ojt'] = i['ojt']
        result[i.cost_center]['internship'] = i['internship']
        
        
        if i.cost_center not in msw_att:
            msw_att[i.cost_center] = {"cost_center":cost_center}
            
        msw_att[i.cost_center]['leave'] = i['leave']
        msw_att[i.cost_center]['absent'] = i['absent']
        msw_att[i.cost_center]['present'] = i['present']
    
        
        
    regular_emp_att = frappe.db.sql('''
                             SELECT COUNT(a.name) AS attendance_count, a.status, e.cost_center as cost_center
                            FROM `tabAttendance` a
                            INNER JOIN `tabEmployee` e ON a.employee = e.name
                            WHERE a.attendance_date = CURDATE()
                            GROUP BY a.status, e.cost_center;
                             ''', as_dict=True)
    
    
    
    
    for i in regular_emp_att:
        if i.cost_center in result:
            
            leave = int(msw_att.get(i.cost_center, {}).get('leave', 0))
            absent = int(msw_att.get(i.cost_center, {}).get('absent', 0))
            present = int(msw_att.get(i.cost_center, {}).get('present', 0))

            # Add attendance counts
            if i.status == "On Leave":
                result[i.cost_center]['leave'] = int(i.attendance_count) + leave
            elif i.status == "Absent":
                result[i.cost_center]['absent'] = int(i.attendance_count) + absent
            elif i.status == "Present":
                result[i.cost_center]['present'] = int(i.attendance_count) + present
            
            # Ensure all keys are populated
            result[i.cost_center]['leave'] = result[i.cost_center].get('leave', leave)
            result[i.cost_center]['absent'] = result[i.cost_center].get('absent', absent)
        result[i.cost_center]['present'] = result[i.cost_center].get('present', present)   
    
    for cost_center, data in result.items():
        if 'leave' not in data:
            data['leave'] = msw_att.get(cost_center, {}).get('leave', 0)
        if 'absent' not in data:
            data['absent'] = msw_att.get(cost_center, {}).get('absent', 0)
        if 'present' not in data:
            data['present'] = msw_att.get(cost_center, {}).get('present', 0) 
    
    total_emp = frappe.db.sql('''
                              select count(name) as count, cost_center from `tabEmployee` where cost_center is not null and status="Active" group by cost_center;
                              ''', as_dict=True)
    muster_roll_total_emp= frappe.db.sql('''
                                select count(name) as count, cost_center from `tabMuster Roll Employee` where status="Active"  group by cost_center;
                                ''',as_dict=True)
    # frappe.throw(str(total_emp))
    for i in total_emp:
        # frappe.throw(str(i.count))
        if i.cost_center in result:
            result[i.cost_center]['total'] = i.count
        
    for j in muster_roll_total_emp:
        # frappe.throw(str(i.count))
        if j.cost_center in result:
            result[j.cost_center]['total'] += j.count
        
        
    
    return list(result.values())
    # for row in data:
    #     # Initialize the result row with the cost_center
    #     result_row = {
            
    #         "cost_center": row["cost_center"]
            
    #     }
    #     # Dynamically add the employee count per designation
    #     for designation in designations:
    #         if row["designation"] == designation.name:
    #             result_row[frappe.scrub(designation['name'])] = row["employee_count"]
        
    #     result.append(result_row)
    
    # return result
    
def get_designation():
    return frappe.db.sql('''
                         select name from `tabDesignation Group`;
                         ''', as_dict=True)
		
	

def get_columns(designations):
    columns = [
       { "label": _("Cost Center"),
            "fieldname": 'cost_center',
            "fieldtype": "Data",
            "width": 120,},
       { "label": _("Total"),
            "fieldname": 'total',
            "fieldtype": "Data",
            "width": 65,}
    ]
    for designation in designations:
        columns.append({
            "label": _(designation['name']),
            "fieldname": frappe.scrub(designation['name']),
            "fieldtype": "Data",
            "width": 65,
        })
        
    columns.append({
            "label": 'MSW',
            "fieldname": 'msw',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'FW',
            "fieldname": 'fw',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'LW',
            "fieldname": 'lw',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'OJT',
            "fieldname": 'ojt',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'Interns',
            "fieldname": 'internship',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'Leave',
            "fieldname": 'leave',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'Absent',
            "fieldname": 'absent',
            "fieldtype": "Data",
            "width": 65,
        })
    columns.append({
            "label": 'Present',
            "fieldname": 'present',
            "fieldtype": "Data",
            "width": 65,
        })
    # frappe.throw(str(columns))
    return columns