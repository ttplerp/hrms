# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import pandas as pd
from datetime import datetime

class AssignShift(Document):
    def validate(self):
        self.check_existing()
        # self.validate_dates()
        self.check_shift_type()
        
    @frappe.whitelist()
    def get_employees(self):
        self.set('shift_details', [])
        for a in frappe.db.sql("""  SELECT name, employee_name
                                 FROM `tabEmployee`
                                   WHERE reports_to = '{supervisor}'
                            """.format(supervisor=self.supervisor), as_dict=True):
        
            row = self.append('shift_details', {})
            row.employee = a.name
            row.employee_name = a.employee_name
            row.update(a)
   
    def check_shift_type(self):
        start_time = frappe.db.get_value("Shift Type", self.shift_type, "start_time")
        end_time = frappe.db.get_value("Shift Type", self.shift_type, "end_time")
        # frappe.msgprint(str(end_time))
        for i, v in enumerate(self.shift_details):
            self.shift_details[i].start_time = start_time
            self.shift_details[i].end_time = end_time
                
    def check_existing(self):
        import json
        for item in self.shift_details:
            if item.as_dict()["1"] == 1:
                self.check_existing_date("1",item.employee)
            if item.as_dict()["2"] == 1:
                self.check_existing_date("2",item.employee)
            if item.as_dict()["3"] == 1:
                self.check_existing_date("3",item.employee)
            if item.as_dict()["4"] == 1:
                self.check_existing_date("4",item.employee)
            if item.as_dict()["5"] == 1:
                self.check_existing_date("5",item.employee)
            if item.as_dict()["6"] == 1:
                self.check_existing_date("6",item.employee)
            if item.as_dict()["7"] == 1:
                self.check_existing_date("7",item.employee)
            if item.as_dict()["8"] == 1:
                self.check_existing_date("8",item.employee)
            if item.as_dict()["9"] == 1:
                self.check_existing_date("9",item.employee)
            if item.as_dict()["10"] == 1:
                self.check_existing_date("10",item.employee)
            if item.as_dict()["11"] == 1:
                self.check_existing_date("11",item.employee)
            if item.as_dict()["12"] == 1:
                self.check_existing_date("12",item.employee)
            if item.as_dict()["13"] == 1:
                self.check_existing_date("13",item.employee)
            if item.as_dict()["14"] == 1:
                self.check_existing_date("14",item.employee)
            if item.as_dict()["15"] == 1:
                self.check_existing_date("15",item.employee)
            if item.as_dict()["16"] == 1:
                self.check_existing_date("16",item.employee)
            if item.as_dict()["17"] == 1:
                self.check_existing_date("17",item.employee)
            if item.as_dict()["18"] == 1:
                self.check_existing_date("18",item.employee)
            if item.as_dict()["19"] == 1:
                self.check_existing_date("19",item.employee)
            if item.as_dict()["20"] == 1:
                self.check_existing_date("20",item.employee)
            if item.as_dict()["21"] == 1:
                self.check_existing_date("21",item.employee)
            if item.as_dict()["22"] == 1:
                self.check_existing_date("22",item.employee)
            if item.as_dict()["23"] == 1:
                self.check_existing_date("23",item.employee)
            if item.as_dict()["24"] == 1:
                self.check_existing_date("24",item.employee)
            if item.as_dict()["25"] == 1:
                self.check_existing_date("25",item.employee)
            if item.as_dict()["26"] == 1:
                self.check_existing_date("26",item.employee)
            if item.as_dict()["27"] == 1:
                self.check_existing_date("27",item.employee)
            if item.as_dict()["28"] == 1:
                self.check_existing_date("28",item.employee)
            if item.as_dict()["29"] == 1:
                self.check_existing_date("29",item.employee)
            if item.as_dict()["30"] == 1:
                self.check_existing_date("30",item.employee)
            if item.as_dict()["31"] == 1:
                self.check_existing_date("31",item.employee)

    def check_existing_date(self, date, employee):
        existing = frappe.db.sql("""
            select a.name, a.from_date, a.to_date, a.shift_type from `tabAssign Shift` a, `tabShift Details` b 
            where a.name = b.parent and a.docstatus != 2 and  b.employee = '{0}' and a.month = '{1}' and a.fiscal_year = '{2}'
            and b.{3} = 1 and a.name != '{4}'
            """.format(employee, self.month, self.fiscal_year, date, self.name), as_dict = True)
        if existing:
            doc_list = []
            for a in existing:
                doc_list.append(a.name)
            if doc_list != []:
                frappe.throw("Another document exists: {0} for employee {1}({2}) with shift assigned on date {3} of month {4} and fiscal year {5}.".format(tuple(doc_list), employee, frappe.db.get_value("Employee",employee,"employee_name"), date, self.month, self.fiscal_year))
    def check_date(self, date):
        #To check if date exists in the selected month in the selected fiscal year //Kinley Dorji
        exists = "no"
        month = str(datetime.strptime(self.month,"%B").month)
        if int(month) < int(10):
            month = "0"+month
        month_start = str(self.fiscal_year)+"-"+month+"-01"
        dates = pd.Period(month_start)
        if int(dates.days_in_month) >= int(date):
            exists = "yes"
        return exists
    # def validate_dates(self):
    #     for item in self.shift_details:
    #         existing = frappe.db.sql("""
    #                                  select a.name, a.from_date, a.to_date, a.shift_type from `tabAssign Shift` a, `tabShift Details` b 
    #                                  where a.name = b.parent and a.docstatus != 2 and  a.employee = '{0}' and (a.from_date between '{1}'
    #                                  and '{2}') or (a.to_date between '{1}' and '{2}')
    #                                  """.format(item.employee, self.from_date, self.to_date), as_dict = True)
    #         if existing:
    #             for a in existing:
    #                 doc = frappe.get_doc("Assign Shift", a.name)
    #                 for b in doc.shift_details:
    #                     frappe.msgprint(b)