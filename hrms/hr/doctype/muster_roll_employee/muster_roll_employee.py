# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowdate
# from frappe.utils.data import get_first_day, get_last_day, add_days

class MusterRollEmployee(Document):
    def validate(self):
        # self.calculate_rates()
        self.cal_rates()
        if len(self.musterroll) > 1:
            for a in range(len(self.musterroll)-1):
                self.musterroll[a].to_date = frappe.utils.data.add_days(getdate(self.musterroll[a + 1].from_date), -1)

        self.check_status()
        self.populate_work_history()
        self.update_user_permissions()
        self.check_for_duplicate_entry()
    
    def check_for_duplicate_entry(self):
        if self.get("__islocal"):
            if frappe.db.exists("Muster Roll Employee", {"name": self.name, "status": "Active"}):
                frappe.throw("Muster Roll Emplloyee Already Exist with CID No. <b>{}</b>".format(self.id_card))

    def update_user_permissions(self):
        prev_branch  = self.get_db_value("branch")
        prev_company = self.get_db_value("company")
        prev_user_id = self.get_db_value("user_id")

        if prev_user_id:
            frappe.permissions.remove_user_permission("Muster Roll Employee", self.name, prev_user_id)
            frappe.permissions.remove_user_permission("Company", prev_company, prev_user_id)
            frappe.permissions.remove_user_permission("Branch", prev_branch, prev_user_id)

        if self.user_id:
            frappe.permissions.add_user_permission("Muster Roll Employee", self.name, self.user_id)
            frappe.permissions.add_user_permission("Company", self.company, self.user_id)
            frappe.permissions.add_user_permission("Branch", self.branch, self.user_id)
            
    def calculate_rates(self):
        if not self.rate_per_hour:
            self.rate_per_hour = (flt(self.rate_per_day) * 1.5) / 8

    def cal_rates(self):
        for a in self.get('musterroll'):
            if a.rate_per_day:
                a.rate_per_hour = (flt(a.rate_per_day) * 1.5) / 8	

    def check_status(self):
        if self.status == "Left" and self.separation_date:
            self.docstatus = 1

    def populate_work_history(self):
        if not self.internal_work_history:
            self.append("internal_work_history",{
                "branch": self.branch,
                "cost_center": self.cost_center,
                "from_date": self.joining_date,
                "owner": frappe.session.user,
                "creation": nowdate(),
                "modified_by": frappe.session.user,
                "modified": nowdate(),
                "reference_doctype": self.temp_doctype,
                "reference_docname": self.temp_docname
            })
        else:
            # Fetching previous document from db
            # if not self.date_of_transfer:
            prev_doc = frappe.get_doc(self.doctype,self.name)
            # self.date_of_transfer = self.date_of_transfer if self.date_of_transfer else today()
            
            if (getdate(self.joining_date) != prev_doc.joining_date) or \
                (self.status == 'Left' and self.separation_date) or \
                (self.cost_center != prev_doc.cost_center):
                for wh in self.internal_work_history:
                    # For change in joining_date
                    if (getdate(self.joining_date) != prev_doc.joining_date):
                        if (getdate(prev_doc.joining_date) == getdate(wh.from_date)):
                            wh.from_date = self.joining_date

                        # For change in separation_date, cost_center
                        if (self.status == 'Left' and self.separation_date):
                            if not wh.to_date:
                                wh.to_date = self.separation_date
                            elif prev_doc.separation_date:
                                if (getdate(prev_doc.separation_date) == getdate(wh.to_date)):
                                    wh.to_date = self.separation_date
                                                    
                            # elif (self.cost_center != prev_doc.cost_center):
                            #     if getdate(self.date_of_transfer) > getdate(today()):
                            #         frappe.throw(_("Date of transfer cannot be a future date."),title="Invalid Date")      
                            #     elif not wh.to_date:
                            #         if getdate(self.date_of_transfer) < getdate(wh.from_date):
                            #             frappe.throw(_("Row#{0} : Date of transfer({1}) cannot be beyond current effective entry.").format(wh.idx,self.date_of_transfer),title="Invalid Date")
                                                    
                            #         wh.to_date = wh.from_date if add_days(getdate(self.date_of_transfer),-1) < getdate(wh.from_date) else add_days(self.date_of_transfer,-1)
                                                
                        # if (self.cost_center != prev_doc.cost_center):
                        #     self.append("internal_work_history",{
                        #         "branch": self.branch,
                        #         "cost_center": self.cost_center,
                        #         "from_date": self.date_of_transfer,
                        #         "owner": frappe.session.user,
                        #         "creation": nowdate(),
                        #         "modified_by": frappe.session.user,
                        #         "modified": nowdate(),
                        #         "reference_doctype": self.temp_doctype,
                        #         "reference_docname": self.temp_docname
                        #     })

