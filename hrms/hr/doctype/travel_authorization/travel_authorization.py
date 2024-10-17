# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
from frappe.utils.data import add_days, date_diff, today
from frappe.model.mapper import get_mapped_doc
from datetime import timedelta
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account

class TravelAuthorization(Document):
    def validate(self):
        self.branch = frappe.db.get_value("Employee", self.employee, "branch")
        self.cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
        
        validate_workflow_states(self)
        #self.validate_project()
        self.assign_end_date()
        self.validate_advance()
        self.set_travel_period()
        self.validate_travel_dates(update=True)
        self.check_maintenance_project()
        self.workflow_action()
        if self.workflow_state != "Approved" and self.workflow_state != "Waiting for Verification":
            notify_workflow_states(self)
        if self.training_event:
            self.update_training_event()
            
    def workflow_action(self):
        action = frappe.request.form.get('action') 
        if action == "Apply" and self.travel_type!="Travel":
            self.workflow_state="Waiting for Verification"
            rcvpnt=frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "hr_verifier"), "user_id")
            self.notify_reviewers(rcvpnt)
        elif action== "Reject" and self.travel_type!="Travel":
            if self.workflow_state == "Waiting for Verification":
                if frappe.session.user!=frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "hr_verifier"), "user_id"):
                    frappe.throw(str("only {} can reject").format(frappe.db.get_value("Employee", frappe.db.get_single_value("HR Settings", "hr_verifier"), "user_id")))
            
                
    
    def notify_reviewers(self, recipients):
        parent_doc = frappe.get_doc(self.doctype, self.name)
        args = parent_doc.as_dict()
        
        try:
            email_template = frappe.get_doc("Email Template", 'Travel Authorization Status Notification')
            message = frappe.render_template(email_template.response, args)
            subject = email_template.subject
        
            frappe.sendmail(
                recipients=recipients,
                subject=_(subject),
                message= _(message),
                
            )
        except :
            frappe.msgprint(_("Travel Authorization Status Notification is missing."))
    
        
    def on_update(self):
        self.set_dsa_rate()
        self.validate_travel_dates()
        self.check_double_dates()
        self.check_leave_applications()

    def before_submit(self):
        self.create_copy()

    def on_submit(self):
        self.validate_travel_dates(update=True)
        self.check_status()
        self.create_attendance()
        notify_workflow_states(self)

    def before_cancel(self):
        if self.advance_journal:
            for t in frappe.get_all("Journal Entry", ["name"], {"name": self.advance_journal, "docstatus": ("<",2)}):
                msg = '<b>Reference# : <a href="#Form/Journal Entry/{0}">{0}</a></b>'.format(t.name)
                frappe.throw(_("Advance payment for this transaction needs to be cancelled first.<br>{0}").format(msg),title='<div style="color: red;">Not permitted</div>')
        ta = frappe.db.sql("""
            select name from `tabTravel Claim` where ta = '{}' and docstatus != 2
        """.format(self.name))
        if ta:
            frappe.throw("""There is Travel Claim <a href="#Form/Travel%20Claim/{0}"><b>{0}</b></a> linked to this Travel Authorization""".format(ta[0][0]))

    def on_cancel_after_draft(self):
        validate_workflow_states(self)
        notify_workflow_states(self)

    def on_cancel(self):
        if self.travel_claim:
            frappe.throw("Cancel the Travel Claim before cancelling Authorization")
        #if not self.cancellation_reason:
        #	frappe.throw("Cancellation Reason is Mandatory when Cancelling Travel Authorization")
        self.cancel_attendance()	
        if self.training_event:
            self.update_training_event(cancel=True)
        notify_workflow_states(self)

    def on_update_after_submit(self):
        if self.travel_claim:
            frappe.throw("Cannot change once claim is created")
        self.validate_travel_dates(update=True)
        self.check_double_dates()
        self.check_leave_applications()
        #self.assign_end_date()
        self.db_set("end_date_auth", self.items[len(self.items) - 1].date)
        self.cancel_attendance()
        self.create_attendance()

    def update_training_event(self, cancel = False):
        if not cancel:
            if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_authorization_id") in (None, ''):
                frappe.db.sql("""
                    update `tabTraining Event Employee` set travel_authorization_id = '{}' where name = '{}'
                    """.format(self.name, self.training_event_child_ref))
        else:
            if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_authorization_id") == self.name:
                frappe.db.sql("""
                    update `tabTraining Event Employee` set travel_authorization_id = NULL where name = '{}'
                    """.format(self.training_event_child_ref))

    def create_copy(self):
        self.details = []
        for a in self.items:
            self.append("details", {"date": a.date, "halt": a.halt, "till_date": a.till_date, "no_days": a.no_days, "from_place": a.from_place, "halt_at": a.halt_at})

    def validate_project(self):
        for a in self.items:
            if a.reference_type == "Project":
                if frappe.db.get_value("Project", a.reference_name, "status") in ("Completed", "Cancelled"):
                    frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", a.reference_name, "status")))
            elif a.reference_type == "Task":
                if frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status") in ("Completed", "Cancelled"):
                    frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status")))

    def validate_advance(self):
        self.advance_amount     = 0 if not self.need_advance else self.advance_amount
        if self.advance_amount > self.estimated_amount * 0.75:
            frappe.throw("Advance Amount cannot be greater than 75% of Total Estimated Amount")
        self.advance_amount_nu  = 0 if not self.need_advance else self.advance_amount_nu
        self.advance_journal    = None if self.docstatus == 0 else self.advance_journal

    @frappe.whitelist()
    def post_advance_jv(self):
        self.check_advance()

    def set_travel_period(self):
        period = frappe.db.sql("""select min(`date`) as min_date, max(till_date) as max_date
                from `tabTravel Authorization Item` where parent = '{}' """.format(self.name), as_dict=True)
        if period:
            self.from_date 	= period[0].min_date
            self.to_date 	= period[0].max_date

    def check_maintenance_project(self):
        row = 1
        if self.for_maintenance_project == 1:
            for item in self.items:
                if not item.reference_type or not item.reference_name:
                    frappe.throw("Project/Maintenance and Reference Name fields are Mandatory in Row {}".format(row),title="Cannot Save")
                row += 1 

    def create_attendance(self):
        for row in self.items:
            from_date = getdate(row.date)
            to_date = getdate(row.till_date) if cint(row.halt) else getdate(row.date)
            noof_days = date_diff(to_date, from_date) + 1
            for a in range(noof_days):
                attendance_date = from_date + timedelta(days=a)
                al = frappe.db.sql("""select name from tabAttendance 
                        where docstatus = 1 and employee = %s 
                        and attendance_date = %s""", (self.employee, str(attendance_date)), as_dict=True)
                if al:
                    doc = frappe.get_doc("Attendance", al[0].name)
                    doc.cancel()
                    
                #create attendance
                attendance = frappe.new_doc("Attendance")
                attendance.flags.ignore_permissions = 1
                attendance.employee = self.employee
                attendance.employee_name = self.employee_name 
                attendance.attendance_date = attendance_date
                attendance.status = "Tour"
                attendance.branch = self.branch
                attendance.company = frappe.db.get_value("Employee", self.employee, "company")
                attendance.reference_name = self.name
                attendance.submit()

    def cancel_attendance(self):
        
        if frappe.db.exists("Attendance", {"reference_name":self.name}):
            frappe.db.sql("delete from tabAttendance where reference_name = %s", (self.name))
    
    def assign_end_date(self):
        if self.items:
            self.end_date_auth = self.items[len(self.items) - 1].date 

    ##
    # check advance and make necessary journal entry
    ##
    def check_advance(self):
        if self.need_advance:
            if self.currency and flt(self.advance_amount_nu) > 0:
                cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
                advance_account = frappe.db.get_value("Company", self.company, "travel_advance_account")
                expense_bank_account = get_bank_account(self.branch)
                # expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
                if not cost_center:
                    frappe.throw("Setup Cost Center for employee in Employee Information")
                if not expense_bank_account:
                    frappe.throw("Setup Default Expense Bank Account for your Branch")
                if not advance_account:
                    frappe.throw("Setup Advance to Employee (Travel) in HR Accounts Settings")

                if frappe.db.exists('Company', {'abbr': 'BOBL'}):
                    voucher_type = 'Journal Entry'
                    naming_series = 'Journal Voucher'
                else:
                    voucher_type = 'Bank Entry'
                    naming_series = 'Bank Payment Voucher'

                je = frappe.new_doc("Journal Entry")
                je.flags.ignore_permissions = 1 
                je.title = "TA Advance (" + self.employee_name + "  " + self.name + ")"
                je.voucher_type = voucher_type
                je.naming_series = naming_series
                je.remark = 'Advance Payment against Travel Authorization: ' + self.name;
                je.posting_date = self.posting_date
                je.branch = self.branch
                # if self.reference_type:
                # 	je.reference_type = self.reference_type
                # 	je.reference_name = self.reference_name
    
                je.append("accounts", {
                    "account": advance_account,
                    "party_type": "Employee",
                    "party": self.employee,
                    "reference_type": "Travel Authorization",
                    "reference_name": self.name,
                    "cost_center": cost_center,
                    "debit_in_account_currency": flt(self.advance_amount_nu),
                    "debit": flt(self.advance_amount_nu),
                    "business_activity": self.business_activity,
                    "is_advance": "Yes"
                })

                je.append("accounts", {
                    "account": expense_bank_account,
                    "cost_center": cost_center,
                    "business_activity": self.business_activity,
                    "credit_in_account_currency": flt(self.advance_amount_nu),
                    "credit": flt(self.advance_amount_nu),
                })
                
                je.insert(ignore_permissions=True)
                
                #Set a reference to the advance journal entry
                self.db_set("advance_journal", je.name)
    
    ##
    # Allow only approved authorizations to be submitted
    ##
    def check_status(self):
        if self.document_status == "Rejected":
            frappe.throw("Rejected Documents cannot be submitted")
        return
        if not self.document_status == "Approved":
            frappe.throw("Only Approved Documents can be submitted")

    ##
    # Ensure the dates are consistent
    ##
    def validate_travel_dates(self, update=False):
        for idx, item in enumerate(self.get("items")):
            if item.halt:
                if not item.till_date:
                    frappe.throw(_("Row#{0} : Till Date is Mandatory for Halt Days.").format(item.idx),title="Invalid Date")
            else:
                if not item.till_date:
                    item.till_date = item.date

            from_date = item.date
            to_date   = item.date if not item.till_date else item.till_date
            item.no_days   = date_diff(to_date, from_date) + 1
            
            if update:
                frappe.db.set_value("Travel Authorization Item", item.name, "no_days", item.no_days)
        
        if self.items:
            # check if the travel dates are already used in other travel authorization
            tas = frappe.db.sql("""select t3.idx, t1.name, t2.date, t2.till_date
                    from 
                        `tabTravel Authorization` t1, 
                        `tabTravel Authorization Item` t2,
                        `tabTravel Authorization Item` t3
                    where t1.employee = "{employee}"
                    and t1.docstatus = 1
                    and t1.name != "{travel_authorization}"
                    and t2.parent = t1.name
                    and t3.parent = "{travel_authorization}"
                    and (
                        (t2.date <= t3.till_date and t2.till_date >= t3.date)
                        or
                        (t3.date <= t2.till_date and t3.till_date >= t2.date)
                    )
            """.format(travel_authorization = self.name, employee = self.employee), as_dict=True)
            for t in tas:
                frappe.throw("Row#{}: The dates in your current Travel Authorization have already been claimed in {} between {} and {}"\
                    .format(t.idx, frappe.get_desk_link("Travel Authorization", t.name), t.date, t.till_date))


    ##
    # Check if the dates are used under Leave Application
    ##
    def check_leave_applications(self):
        las = frappe.db.sql("""select t1.name from `tabLeave Application` t1 
                where t1.employee = "{employee}"
                and t1.docstatus != 2 and  case when t1.half_day = 1 then t1.from_date = t1.to_date end
                and exists(select 1
                        from `tabTravel Authorization Item` t2
                        where t2.parent = "{travel_authorization}"
                        and (
                            (t1.from_date <= t2.till_date and t1.to_date >= t2.date)
                            or
                            (t2.date <= t1.to_date and t2.till_date >= t1.from_date)
                        )
                )
        """.format(travel_authorization = self.name, employee = self.employee), as_dict=True)
        for t in las:
            frappe.throw("The dates in your current travel authorization have been used in leave application {}".format(frappe.get_desk_link("Leave Application", t.name)))

    ##
    # Send notification to the supervisor / employee
    ##
    def sendmail(self, to_email, subject, message):
        email = frappe.db.get_value("Employee", to_email, "user_id")
        if email:
            try:
                frappe.sendmail(recipients=email, sender=None, subject=subject, message=message)
            except:
                pass

    def set_dsa_rate(self):
        
        if self.place_type=="In-Country":
            if self.grade:
                self.db_set("dsa_per_day", frappe.db.get_value("Employee Grade", self.grade, "dsa"))
                
                
        elif self.place_type=="Out-Country":
            if "India" in self.countrys:
                roles=frappe.get_roles(self.owner)
            
                if "CEO" in roles:
                    ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "ceo"))
                else:
                    ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "others"))
            else:
                ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "dsa_rate"))
            currency_from=frappe.db.get_value("DSA Out Country", self.countrys, "currency")
            
            ex_country_dsa=ex_country_dsa*flt(get_exchange_rate(currency_from, "BTN", self.posting_date ))
            self.db_set("dsa_per_day", ex_country_dsa)

      
    @frappe.whitelist()
    def set_estimate_amount(self):
        total_days = 0.0
        percent=1
        
        if self.food==1 and self.lodge==1 and self.incidental_expense==1:
            percent=0.20
        elif self.food==1 and self.lodge==1:
            percent=0.30
        elif self.lodge==1:
            percent=0.5
        elif self.food==1:
            percent=0.75


        start_day=1
        return_day=1


        after30=frappe.get_doc("HR Settings").dsa_30_to_90
        after90=frappe.get_doc("HR Settings").dsa_90_plus

        if not after30:
            frappe.throw("Set DSA (30 to 90) in HR Settings")
        if not after90:
            frappe.throw("Set DSA (90 plus) in HR Settings")
            
        after30=flt(after30)
        after90=flt(after90)
        
        train_dsa= flt(frappe.get_doc("HR Settings").training_dsa)*percent
        dsa_rate  = frappe.db.get_value("Employee Grade", self.grade, "dsa")
        return_dsa = frappe.get_doc("HR Settings").return_day_dsa

        if not return_dsa:
            frappe.throw("Set Return Day DSA Percent in HR Settings")
        
        if not dsa_rate:
            frappe.throw("No DSA Rate set for Grade <b> {0} /<b> ".format(self.grade))

        if not train_dsa:
            frappe.throw("Set Training DSA in HR Settings") 
            
        if self.place_type == "In-Country":
            
            if self.travel_type == "Training" or  self.travel_type == "Meeting and Seminars":
            
                if self.within_same_locality==1:
                    start_day=0
                    return_day=0
                    within_same=frappe.get_doc("HR Settings").dsa_within_same_locality  
                    
                    train_dsa=flt(train_dsa)*flt(within_same/100)
                
                    if not within_same:
                        frappe.throw("Set DSA Within Same Locality in HR Settings")
            else:
                
                train_dsa=dsa_rate
            full_dsa = quarter_dsa = half_dsa = 0
                            
            for i in self.items:
                from_date = i.date
                to_date   = i.date if not i.till_date else i.till_date
                no_days   = date_diff(to_date, from_date) + 1
                # if i.quarantine:
                # 	no_days = 0
                total_days  += no_days
                # frappe.msgprint("{0} {1}".format(from_date, total_days))

            if flt(total_days)-flt(return_day)-flt(start_day) <= 30:
                full_dsa = flt(total_days) - flt(return_day)- flt(start_day)
                quarter_dsa = 0.0
                half_dsa = 0.0

            elif flt(total_days)-flt(return_day)-flt(start_day)>30  and flt(total_days)-flt(return_day)-flt(start_day) <= 90:
                full_dsa = 30
                quarter_dsa = flt(total_days) -30 - flt(return_day)- flt(start_day)
                half_dsa = 0.0

            elif flt(total_days)-flt(return_day)-flt(start_day) > 90:
                full_dsa = 30
                quarter_dsa = 60
                half_dsa =  flt(total_days) - 90 - flt(return_day) - flt(start_day)
            
            self.estimated_amount =(flt(start_day) * flt(dsa_rate))+ (flt(full_dsa) * flt(train_dsa))  + flt(return_day) * (flt(return_dsa)/100)* flt(dsa_rate)  
                    
        elif self.place_type == "Out-Country":
            
            start_day = 1
            return_day = 1
            
            if "India" in self.countrys:
                roles=frappe.get_roles(self.owner)
                if "CEO" in roles:
                    train_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "ceo"))*percent
                else:
                    train_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "others"))*percent
            else:
                
                currency_from=frappe.db.get_value("DSA Out Country", self.countrys, "currency")
                train_dsa=flt(frappe.db.get_value("DSA Out Country", self.countrys, "dsa_rate"))*flt(get_exchange_rate(currency_from, "BTN", self.posting_date ))


            full_dsa = quarter_dsa = half_dsa = 0
                            
            for i in self.items:
                from_date = i.date
                to_date   = i.date if not i.till_date else i.till_date
                no_days   = date_diff(to_date, from_date) + 1
                # if i.quarantine:
                # 	no_days = 0
                total_days  += no_days
                # frappe.msgprint("{0} {1}".format(from_date, total_days))
            
            if flt(total_days)-flt(return_day)-flt(start_day) <= 30:
                full_dsa = flt(total_days) - flt(return_day)- flt(start_day)
                quarter_dsa = 0.0
                half_dsa = 0.0

            elif flt(total_days)-flt(return_day)-flt(start_day)>30  and flt(total_days)-flt(return_day)-flt(start_day) <= 90:
                full_dsa = 30
                quarter_dsa = flt(total_days) -30 - flt(return_day)- flt(start_day)
                half_dsa = 0.0

            elif flt(total_days)-flt(return_day)-flt(start_day) > 90:
                full_dsa = 30
                quarter_dsa = 60
                half_dsa =  flt(total_days) - 90 - flt(return_day) - flt(start_day)
            
            self.estimated_amount =(flt(start_day) * flt(train_dsa))+ (flt(full_dsa) * flt(train_dsa)) 

                    
              
    @frappe.whitelist()
    def check_double_dates(self):
        for i in self.get('items'):
        	for j in self.get('items'):
        		if i.name != j.name and str(i.date) <= str(j.till_date) and str(i.till_date) >= str(j.date):
        			frappe.throw(_("Row#{}: Dates are overlapping with Row#{}").format(i.idx, j.idx))

@frappe.whitelist()
def make_travel_claim(source_name, target_doc=None):
    

    def update_date(obj, target, source_parent):
        target.posting_date = nowdate()
        target.supervisor = None
        # target.for_maintenance_project = 1
        

    def transfer_currency(obj, target, source_parent):
        
            
        if obj.halt:
            target.from_place = None
            target.to_place = None
        else:
            target.no_days = 1
            target.halt_at = None
            
            
        target.currency = source_parent.currency
        target.currency_exchange_date = source_parent.posting_date
        target.within_same_locality=source_parent.within_same_locality
        target.food=source_parent.food
        target.lodge=source_parent.lodge
        target.place_type=source_parent.place_type
        target.incidental_expense=source_parent.incidental_expense 
        
        target.dsa = source_parent.dsa_per_day
        target.country=source_parent.countrys
            
        if target.currency == "BTN":
            target.exchange_rate = 1
        else:
            target.exchange_rate = get_exchange_rate(target.currency, "BTN", date=source_parent.posting_date)
        
        target.amount = target.dsa
        target.dsa_percent='100'
        
        if (source_parent.travel_type=="Training" or source_parent.travel_type == "Meeting and Seminars" or source_parent.travel_type == "Workshop") and source_parent.place_type=="In-Country":
            target.dsa = frappe.get_doc("HR Settings").training_dsa
            
        if source_parent.within_same_locality==1:
            target.dsa_percent= frappe.get_doc("HR Settings").dsa_within_same_locality
                
        if target.halt:
            
            if (source_parent.travel_type=="Training" or source_parent.travel_type == "Meeting and Seminars" or source_parent.travel_type == "Workshop") and source_parent.place_type=="In-Country":
                    
                target.dsa = frappe.get_doc("HR Settings").training_dsa
            
            
                
            target.amount = flt(target.dsa) * flt(target.no_days)
            
            if source_parent.food==1 and source_parent.lodge==1 and source_parent.incidental_expense==1:
                target.dsa_percent='20'
            elif source_parent.food==1 and source_parent.lodge==1:
                target.dsa_percent='30'
            elif source_parent.lodge==1:
                target.dsa_percent='50'
            elif source_parent.food==1:
                target.dsa_percent='75'
            
            target.dsa=flt(target.dsa)
            after30=flt(frappe.get_doc("HR Settings").dsa_30_to_90)
            after90=flt(frappe.get_doc("HR Settings").dsa_90_plus)
            
            if flt(target.no_days)<=30:
                target.amount = flt(target.dsa) * flt(target.no_days)
            elif flt(target.no_days)>30 and flt(target.no_days)<=90:
                target.amount = flt(target.dsa)*30 + flt(target.dsa) * (flt(target.no_days)-30) * (after30/100)
            else:
                target.amount = flt(target.dsa)*30 + flt(target.dsa)*60*flt(after30/100) +flt(target.dsa) * (flt(target.no_days)-90) * (after90/100)
        else:
            if source_parent.within_same_locality:
                target.dsa = flt(frappe.get_doc("HR Settings").training_dsa)
                target.amount = flt(target.dsa)
            
             
            
            
        target.actual_amount = target.amount * target.exchange_rate * (flt(target.dsa_percent)/100)
        target.amount=target.actual_amount
        
    def adjust_last_date(source, target):
        target.within_same_locality=source.within_same_locality
        dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
        dsa_rate  = frappe.db.get_value("Employee Grade", self.grade, "dsa")
        
        #Tandin
        if source.place_type=="In-Country":
            
            if source.within_same_locality:
                dsa_percent=100
                
            percent = flt(dsa_percent) / 100.0
        
        
        if target.items[len(target.items) - 1].halt!=1:
            target.items[len(target.items) - 1].dsa_percent = dsa_percent
            target.items[len(target.items) - 1].actual_amount = flt(dsa_rate) * percent
            target.items[len(target.items) - 1].amount = flt(dsa_rate) * percent
            target.items[len(target.items) - 1].last_day = 1 
        

    doc = get_mapped_doc("Travel Authorization", source_name, {
            "Travel Authorization": {
                "doctype": "Travel Claim",
                "field_map": {
                    "name": "ta",
                    "posting_date": "ta_date",
                    "advance_amount_nu": "advance_amount"
                },
                "postprocess": update_date,
                "validation": {"docstatus": ["=", 1]}
            },
            "Travel Authorization Item": {
                "doctype": "Travel Claim Item",
                "postprocess": transfer_currency,
                "travel_authorization": "parent"
            },
        }, target_doc, adjust_last_date)
    return doc

@frappe.whitelist()
def get_exchange_rate(from_currency, to_currency, date=None):
    # Following line is replaced by subsequent code by SHIV on 2020/09/22
    #ex_rate = frappe.db.get_value("Currency Exchange", {"from_currency": from_currency, "to_currency": to_currency}, "exchange_rate")
    if not date or date == "" or date == " ":
        frappe.throw("Please select Currency Exchange Date.")
    
    ex_rate = frappe.db.sql("""select exchange_rate 
                    from `tabCurrency Exchange`
                    where from_currency = '{from_currency}'
                    and to_currency = '{to_currency}'
                    and `date` = '{data}'
                    order by `date` desc
                    limit 1
    """.format(from_currency=from_currency, to_currency=to_currency, data=date), as_dict=False)
 
    
    if not ex_rate:
        frappe.throw("No Exchange Rate defined in Currency Exchange for the date {}! Kindly contact your accounts section".format(date))
    else:
        return ex_rate[0][0]

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)

    if user == "Administrator":
        return
    if "HR User" in user_roles or "HR Manager" in user_roles:
        return

    return """(
        `tabTravel Authorization`.owner = '{user}'
        or
        exists(select 1
                from `tabEmployee`
                where `tabEmployee`.name = `tabTravel Authorization`.employee
                and `tabEmployee`.user_id = '{user}' and `tabTravel Authorization`.docstatus != 2)
        or
        exists(select 1
                from `tabEmployee`, `tabHas Role`
                where `tabEmployee`.user_id = `tabHas Role`.parent
                and `tabHas Role`.role = 'Travel Administrator'
                and (select region from `tabEmployee` where `tabEmployee`.name = `tabTravel Authorization`.employee limit 1) = (select region from `tabEmployee` where `tabEmployee`.user_id = '{user}' limit 1)
                and `tabEmployee`.user_id = '{user}')
        or
        (`tabTravel Authorization`.supervisor = '{user}' and `tabTravel Authorization`.workflow_state not in ('Draft','Approved','Rejected','Rejected By Supervisor','Cancelled'))
        or 
        (`tabTravel Authorization`.supervisor_manager = '{user}' and `tabTravel Authorization`.workflow_state not in ('Draft', 'Rejected', 'Cancelled','Approved','Rejected By Supervisor'))
    )""".format(user=user)

# @frappe.whitelist()
# def update_date_authorization(idIdx, auth_date, ta_id):
# 	frappe.db.sql("update `tabTravel Authorization Item` set date='{}' where idx= '{}' and parent='{}'".format(auth_date, idIdx, ta_id))
