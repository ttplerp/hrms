# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, flt, nowdate, money_in_words, getdate, date_diff, today, add_days, get_first_day, get_last_day
from erpnext.accounts.utils import get_account_currency, get_fiscal_year
import collections
from erpnext.setup.utils import get_exchange_rate
from erpnext.custom_workflow import validate_workflow_states, notify_workflow_states
from erpnext.accounts.doctype.accounts_settings.accounts_settings import get_bank_account

class TravelClaim(Document):
    def validate(self):
        validate_workflow_states(self)
        #self.check_return_date()
        self.validate_project()
        self.validate_dates()
        # self.check_approval()
        # self.validate_dsa_ceiling()
        self.validate_duplicate()
        # Following line commented by SHIV on 2020/09/22 as the same code is taken care in on_submit
        self.update_amounts()
        self.validate_cost_center()
        if self.travel_type not in ("Training", "Meeting and Seminars") and self.supervisor:
            self.set_supervisor_manager()
        if self.training_event:
            self.update_training_event()
        if self.workflow_state not in ("Claimed","Cancelled"):
            notify_workflow_states(self)

    def validate_project(self):
        row = 1
        for a in self.items:
            if a.reference_type == "Project":
                if frappe.db.get_value("Project", a.reference_name, "status") in ("Completed", "Cancelled"):
                    frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", a.reference_name, "status")))
            elif a.reference_type == "Task":
                if frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status") in ("Completed", "Cancelled"):
                    frappe.throw("Cannot create or submit Journal Entry {} since the project {} is {}".format(self.name, a.reference_name, frappe.db.get_value("Project", frappe.db.get_value("Task", a.reference_name, "project"), "status")))
        if self.for_maintenance_project == 1:
            for item in self.items:
                if not item.reference_type or not item.reference_name:
                    frappe.throw("Project/Maintenance and Reference Name fields are Mandatory in Row {}".format(row),title="Cannot Save")
                row += 1

    def validate_duplicate(self):
        existing = []
        existing = frappe.db.sql("""
            select name from `tabTravel Claim` where name != '{}' and docstatus != 2 and workflow_state != 'Rejected'
            and ta = '{}'
        """.format(self.name, self.ta), as_dict=True)

        for a in existing:
            frappe.throw("""Another {} already exists for Travel Authorization {}.""".format(frappe.get_desk_link("Travel Claim",a.name), self.ta))

    def validate_cost_center(self):
        if self.reference_type and self.reference_name: 
            self.cost_center = frappe.db.get_value(self.reference_type, self.reference_name, 'cost_center')

    def set_supervisor_manager(self):
        self.supervisor_manager, self.supervisor_manager_name, supervisor_manager_designation = frappe.db.get_value("Employee",frappe.db.get_value("Employee", {"user_id":self.supervisor},["reports_to"]),['user_id','employee_name','designation'])

    def on_update(self):
        self.check_double_dates()
        self.check_double_date_inside()

    def on_submit(self):
        #self.get_status()
        #self.validate_submitter()
        #self.check_status()
        self.post_journal_entry()
        self.update_travel_authorization()

        if self.supervisor_approval and self.hr_approval:
            self.db_set("hr_approved_on", nowdate())
        
        # Following line commented by SHIV on 2020/10/04
        #self.sendmail(self.employee, "Travel Claim Approved" + str(self.name), "Your " + str(frappe.get_desk_link("Travel Claim", self.name)) + " has been approved and sent to Accounts Section. Kindly follow up.")
        notify_workflow_states(self)
        if self.for_maintenance_project:
            self.update_project_and_maintenance()
            self.update_project_and_maintenance_cost()

    def update_training_event(self, cancel = False):
        if not cancel:
            if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_claim_id") in (None, ''):
                frappe.db.sql("""
                    update `tabTraining Event Employee` set travel_claim_id = '{}' where name = '{}'
                    """.format(self.name, self.training_event_child_ref))
        else:
            if frappe.db.get_value("Training Event Employee", self.training_event_child_ref, "travel_claim_id") == self.name:
                frappe.db.sql("""
                    update `tabTraining Event Employee` set travel_claim_id = NULL where name = '{}'
                    """.format(self.training_event_child_ref))

    # added by phuntsho and kinley on oct 12,2021
    def update_project_and_maintenance(self):
        references = {}
        for a in self.items:
            if self.for_maintenance_project == 1 and not a.reference_name:
                frappe.throw("Reference cannot be empty for Project/Maintenance Travel")
            if a.reference_name:
                if a.reference_name not in references:
                    references.update({a.reference_name: {"reference_type": a.reference_type, "amount": flt(a.amount), "from_date": a.date, "to_date": None}})
                else:
                    references[a.reference_name]['amount'] += flt(a.amount)
                    references[a.reference_name]['to_date'] = a.date
            else:
                if "no_ref" not in references:
                    references.update({"no_ref": {"reference_type": "Travel Claim", "amount": flt(a.amount)}})
                else:
                    references["no_ref"]["amount"] += flt(a.amount)
        for ref in references:
            if ref != "no_ref" and references[ref]['reference_type']:
                if references[ref]['reference_type'] in ("Project", "Maintenance Order"):
                    query = """
                        INSERT INTO {table}(name, parentfield, parenttype, employee, employee_name, 
                                from_date, to_date,	total_claim_amount,	travel_claim, parent)
                        VALUES('{name}','{parentfield}','{parenttype}',	'{emp}','{emp_name}',
                                '{from_date}', '{to_date}', {amount},'{claim}',	'{parent}')
                        """.format(
                            table='`tabProject and Maintenance Travel Log`', 
                            name=self.name+" "+ref, 
                            parentfield = 'travel_log', 
                            parenttype = references[ref]['reference_type'],
                            emp=self.employee, 
                            emp_name=self.employee_name, 
                            from_date = references[ref]['from_date'], 
                            to_date = references[ref]['to_date'] if references[ref]['to_date'] else references[ref]['from_date'],
                            amount = flt(references[ref]['amount']), 
                            claim = self.name, 
                            parent=ref)
                    frappe.db.sql(query)
                elif references[ref]['reference_type'] == "Task":
                    query_one = """
                        INSERT INTO {table}(name, parentfield, parenttype, employee, employee_name, 
                                from_date, to_date,	total_claim_amount,	travel_claim, parent)
                        VALUES ('{name}', '{parentfield}', '{parenttype}', '{emp}', '{emp_name}',
                                '{from_date}', '{to_date}', {amount}, '{claim}', '{parent}')
                        """.format(
                            table='`tabProject and Maintenance Travel Log`', 
                            name=self.name+" "+ref, 
                            parentfield = 'travel_log', 
                            parenttype = "Project",
                            emp=self.employee, 
                            emp_name=self.employee_name, 
                            from_date = references[ref]['from_date'], 
                            to_date = references[ref]['to_date']  if references[ref]['to_date'] else references[ref]['from_date'],
                            amount = flt(references[ref]['amount']), 
                            claim = self.name, 
                            parent=frappe.db.get_value("Task",ref,"project"))
                    query_two = """
                        INSERT INTO {table}(name, parentfield, parenttype, employee, employee_name, 
                                from_date, to_date,	total_claim_amount,	travel_claim, parent)
                        VALUES('{name}', '{parentfield}', '{parenttype}', '{emp}', '{emp_name}',
                                '{from_date}', '{to_date}', {amount}, '{claim}', '{parent}')
                        """.format(
                            table='`tabProject and Maintenance Travel Log`', 
                            name=str(self.name+" "+ref)+"_1", 
                            parentfield = 'travel_log', 
                            parenttype = references[ref]['reference_type'],
                            emp=self.employee, 
                            emp_name=self.employee_name, 
                            from_date = references[ref]['from_date'], 
                            to_date = references[ref]['to_date']  if references[ref]['to_date'] else references[ref]['from_date'],
                            amount = flt(references[ref]['amount']), 
                            claim = self.name, 
                            parent=ref)
                    frappe.db.sql(query_one)
                    frappe.db.sql(query_two)

    # added by phuntsho and kinley on oct 12,2021
    def update_project_and_maintenance_cost(self):
        """ update the cost on the specified project. """
        references = {}
        for a in self.items:
            if self.for_maintenance_project == 1 and not a.reference_name:
                frappe.throw("Reference cannot be empty for Project/Maintenance Travel")
            if a.reference_name:
                if a.reference_name not in references:
                    references.update({a.reference_name: {"reference_type": a.reference_type, "amount": flt(a.amount)}})
                else:
                    references[a.reference_name]['amount'] += flt(a.amount)
            else:
                if "no_ref" not in references:
                    references.update({"no_ref": {"reference_type": "Travel Claim", "amount": flt(a.amount)}})
                else:
                    references["no_ref"]["amount"] += flt(a.amount)
        for ref in references:
            if ref != "no_ref" and references[ref]['reference_type'] in ("Project", "Maintenance Order"):
                previous_costs = frappe.db.get_value(references[ref]['reference_type'], ref, ['total_cost', 'travel_cost'],as_dict= 1)
                # frappe.msgprint(str(previous_costs))
                if self.docstatus == 1:
                    overall_cost = previous_costs.total_cost + references[ref]['amount']
                    total_travel_cost = previous_costs.travel_cost + references[ref]['amount']

                elif self.docstatus == 2:
                    overall_cost = previous_costs.total_cost - references[ref]['amount']
                    total_travel_cost = previous_costs.travel_cost - references[ref]['amount']

                if self.docstatus == 1 or self.docstatus == 2: 
                    frappe.db.sql("""
                        UPDATE 
                            `tab{table}` 
                        SET 
                            total_cost={cost}, 
                            travel_cost={travel_cost} 
                        WHERE 
                            name ='{ref}'""".format(
                        table = references[ref]['reference_type'], 
                        cost = overall_cost, 
                        travel_cost = total_travel_cost, 
                        ref = ref))
            elif ref != "no_ref" and references[ref]['reference_type'] == "Task":	
                task_previous_costs = frappe.db.get_value(references[ref]['reference_type'], ref, ['total_cost', 'travel_cost'],as_dict= 1)
                project_previous_costs = frappe.db.get_value("Project", frappe.db.get_value(references[ref]['reference_type'],ref,"project"), ['total_cost', 'travel_cost'],as_dict= 1)
                # frappe.msgprint(str(previous_costs))
                if self.docstatus == 1:
                    task_total_cost = task_previous_costs.total_cost + references[ref]['amount']
                    project_total_cost = project_previous_costs.total_cost + references[ref]['amount']
                    task_travel_cost = task_previous_costs.travel_cost + references[ref]['amount']
                    project_travel_cost = project_previous_costs.travel_cost + references[ref]['amount']

                elif self.docstatus == 2:
                    task_total_cost = task_previous_costs.total_cost - references[ref]['amount']
                    project_total_cost = project_previous_costs.total_cost - references[ref]['amount']
                    task_travel_cost = task_previous_costs.travel_cost - references[ref]['amount']
                    project_travel_cost = project_previous_costs.travel_cost - references[ref]['amount']

                if self.docstatus == 1 or self.docstatus == 2: 
                    frappe.db.sql("""
                        UPDATE 
                            `tab{table}` 
                        SET 
                            total_cost={cost}, 
                            travel_cost={travel_cost} 
                        WHERE 
                            name ='{ref}'""".format(
                        table = references[ref]['reference_type'], 
                        cost = task_total_cost, 
                        travel_cost = task_travel_cost, 
                        ref = ref))

                    frappe.db.sql("""
                        UPDATE 
                            `tab{table}` 
                        SET 
                            total_cost={cost}, 
                            travel_cost={travel_cost} 
                        WHERE 
                            name ='{ref}'""".format(
                        table = "Project", 
                        cost = project_total_cost, 
                        travel_cost = project_travel_cost, 
                        ref = frappe.db.get_value("Task",ref,"project")))

    def before_cancel(self):
        self.unlink_travel_authorization()

    def on_cancel_after_draft(self):
        validate_workflow_states(self)
        notify_workflow_states(self)

    def on_cancel(self):
        self.check_journal_entry()
        # Following line commented by SHIV on 2020/10/04
        #self.sendmail(self.employee, "Travel Claim Cancelled by HR" + str(self.name), "Your travel claim " + str(self.name) + " has been cancelled by the user")
        notify_workflow_states(self)
        if self.for_maintenance_project:
            self.cancel_project_maintenance()
            self.update_project_and_maintenance_cost()
        if self.ta:
            self.ta = None
        if self.training_event:
            self.update_training_event(cancel=True)

    def cancel_project_maintenance(self):
        frappe.db.sql("DELETE FROM `tabProject and Maintenance Travel Log` WHERE travel_claim = '{}'".format(self.name))


    # Following method created by SHIV on 2020/09/22
    def check_journal_entry(self):
        if self.claim_journal and frappe.db.exists("Journal Entry", {"name": self.claim_journal, "docstatus": ("<","2")}):
            frappe.throw(_("You need to cancel {} first").format(frappe.get_desk_link("Journal Entry", self.claim_journal)))

    # Following method added by SHIV on 2020/09/22
    def before_cancel_after_draft(self):
        self.unlink_travel_authorization()

    def unlink_travel_authorization(self):
        cl_status = frappe.db.get_value("Journal Entry", self.claim_journal, "docstatus")
        if cl_status and cl_status != 2:
            frappe.throw("You need to cancel the claim journal entry first!")

        tas = frappe.db.sql("select distinct(travel_authorization) as ta from `tabTravel Claim Item` where parent = %s", str(self.name), as_dict=True)
        for a in tas:
            ta = frappe.get_doc("Travel Authorization", a.ta)
            ta.db_set("travel_claim", "")

        if self.ta:
            travel_a = frappe.get_doc("Travel Authorization", self.ta)
            travel_a.db_set("travel_claim","")

    def get_monthly_count(self, items):
        counts = {}
        for i in items:
            i.till_date     = i.date if not i.till_date else i.till_date
            from_month      = str(i.date)[5:7]
            to_month        = str(i.till_date)[5:7]
            from_year       = str(i.date)[:4]
            to_year         = str(i.till_date)[:4]
            from_monthyear  = str(from_year)+str(from_month)
            to_monthyear    = str(to_year)+str(to_month)

            if int(to_monthyear) >= int(from_monthyear):
                for y in range(int(from_year), int(to_year)+1):
                    m_start = from_month if str(y) == str(from_year) else '01'
                    m_end   = to_month if str(y) == str(to_year) else '12'
                                    
                    for m in range(int(m_start), int(m_end)+1):
                        key          = str(y)+str(m).rjust(2,str('0'))
                        m_start_date = key[:4]+'-'+key[4:]+'-01'
                        m_start_date = i.date if str(y)+str(m).rjust(2,str('0')) == str(from_year)+str(from_month) else m_start_date
                        m_end_date   = i.till_date if str(y)+str(m).rjust(2,str('0')) == str(to_year)+str(to_month) else get_last_day(m_start_date)
                        if counts.has_key(key):
                            counts[key] += date_diff(m_end_date, m_start_date)+1
                        else:
                            counts[key] = date_diff(m_end_date, m_start_date)+1
            else:
                frappe.throw(_("Row#{0} : Till Date cannot be before from date.").format(i.idx), title="Invalid Data")
        return collections.OrderedDict(sorted(counts.items()))
    
    def validate_dsa_ceiling(self):
            max_days_per_month  = 0
            tt_list             = []
            local_count         = {}
            claimed_count       = {}
            mapped_count        = {}
            months              = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
            cond1               = ""
            cond2               = ""
            cond3               = ""
            format_string       = ""
            lastday_dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
            
            if self.place_type.lower().replace("-","") == "incountry":
                    max_days_per_month = frappe.db.get_single_value("HR Settings", "max_days_incountry")
                    if max_days_per_month:
                            tt_list = frappe.db.sql_list("select travel_type from `tabHR Settings Incountry`")
            else:
                    max_days_per_month = frappe.db.get_single_value("HR Settings", "max_days_outcountry")
                    if max_days_per_month:
                            tt_list = frappe.db.sql_list("select travel_type from `tabHR Settings Outcountry`")

            if tt_list:
                    format_string = ("'"+"','".join(['%s'] * len(tt_list))+"'") % tuple(tt_list)
                    cond1 += "and t1.travel_type in ({0}) ".format(format_string, self.travel_type)

            if max_days_per_month and (not tt_list or self.travel_type in (format_string)):
                    local_count    = self.get_monthly_count(self.items)
                    for k in local_count:
                            cond2 += " '{0}' between date_format(t2.`date`,'%Y%m') and date_format(ifnull(t2.`till_date`,t2.`date`),'%Y%m') or".format(k)
                    cond2 = cond2.rsplit(' ',1)[0]
                    cond2 = "and (" + cond2 + ")"
                    cond3 = "and t2.last_day = 0" if not lastday_dsa_percent else ""

                    query = """
                                    select
                                            t2.date,
                                            t2.till_date,
                                            t2.no_days
                                    from
                                            `tabTravel Claim` as t1,
                                            `tabTravel Claim Item` as t2
                                    where t1.employee = '{0}'
                                    and t1.docstatus = 1
                                    and t1.place_type = '{1}'
                                    {2}                                        
                                    and t2.parent = t1.name
                                    {3}
                                    {4}
                    """.format(self.employee, self.place_type, cond1, cond2, cond3)

                    tc_list = frappe.db.sql(query, as_dict=True)

                    if tc_list:
                            claimed_count = self.get_monthly_count(tc_list)

                    for k,v in local_count.iteritems():
                            mapped_count[k] = {'local': v, 'claimed': claimed_count.get(k,0), 'balance': flt(max_days_per_month)-flt(claimed_count.get(k,0))}

                    for i in self.get("items"):
                            i.remarks        = ""
                            i.days_allocated = 0                                
                            if i.last_day and not lastday_dsa_percent:
                                    i.days_allocated = 0
                                    continue
                            
                            record_count     = self.get_monthly_count([i])
                            for k,v in record_count.iteritems():                
                                    lapsed  = 0
                                    counter = 0
                                    if mapped_count[k]['balance'] >= v:
                                            i.days_allocated = flt(i.days_allocated) + v
                                            mapped_count[k]['balance'] -= v
                                    else:
                                            if mapped_count[k]['balance'] < 0:
                                                    lapsed = v
                                            else:
                                                    lapsed = v - mapped_count[k]['balance']
                                                    i.days_allocated = flt(i.days_allocated) + mapped_count[k]['balance']
                                                    mapped_count[k]['balance'] = 0
                                                    
                                            if lapsed:
                                                    counter += 1
                                                    frappe.msgprint(_("Row#{0}: You have crossed the DSA({4} days) limit by {1} days for the month {2}-{3}").format(i.idx, int(lapsed), months[int(str(k)[4:])-1], str(k)[:4],max_days_per_month))
                                                    i.remarks = str(i.remarks)+"{3}) {0} Day(s) lapsed for the month {1}-{2}\n".format(int(lapsed), months[int(str(k)[4:])-1], str(k)[:4], counter)
            else:
                    for i in self.get("items"):
                            i.remarks        = ""
                            i.days_allocated = 1 
    
    def update_amounts(self):
            #dsa_per_day         = flt(frappe.db.get_value("Employee Grade", self.grade, "dsa"))
            lastday_dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
            total_claim_amount  = 0
            exchange_rate       = 0
            company_currency    = "BTN"
            
            if self.place_type!="In-Country" or self.within_the_dzongkhag==1:
                lastday_dsa_percent=0
        
            
            for i in self.get("items"):
                    
                    i.days_allocated = i.no_days
                    exchange_rate      = 1 if i.currency == company_currency else get_exchange_rate(i.currency, company_currency, transaction_date=i.currency_exchange_date)
                    i.exchange_rate  = exchange_rate
                    visa_exchange_rate  = 1 if i.visa_fees_currency == company_currency else get_exchange_rate(i.visa_fees_currency, company_currency,transaction_date=i.currency_exchange_date)
                    passport_exchange_rate  = 1 if i.passport_fees_currency == company_currency else get_exchange_rate(i.passport_fees_currency, company_currency, transaction_date=i.currency_exchange_date)
                    incidental_exchange_rate  = 1 if i.incidental_fees_currency == company_currency else get_exchange_rate(i.incidental_fees_currency, company_currency, transaction_date=i.currency_exchange_date)
                    #i.dsa             = flt(dsa_per_day)
                    i.dsa              = flt(i.dsa)
                    ##### Ver 3.0.190213 Begins, Following line replaced by SHIV on 13/02/2019
                    i.dsa_percent      = lastday_dsa_percent if i.last_day else i.dsa_percent
                    # i.dsa_percent      = (i.dsa_percent if cint(i.dsa_percent) <= cint(lastday_dsa_percent) else lastday_dsa_percent) if i.last_day else i.dsa_percent
                    i.dsa_percent = cint(i.dsa_percent)
                    ##### Ver 3.0.190213 Ends
                    # frappe.throw(str(i.days_allocated)+" "+str(i.dsa)+" "+str(i.dsa_percent))
                    
                    if self.place_type == "In-Country" or ("India" in self.country):
                        
                        if i.halt != 1:
                            
                            i.amount = (flt(i.days_allocated)*(flt(i.dsa)*flt(i.dsa_percent)/100)) + (flt(i.mileage_rate) * flt(i.distance)) + flt(i.porter_pony_charges)
                        else:
                            
                            percent='100'
                            if self.food==1 and self.lodge==1 and self.incidental_expense==1:
                                percent='20'
                            elif self.food==1 and self.lodge==1:
                                percent='30'
                            elif self.lodge==1:
                                percent='50'
                            elif self.food==1:
                                percent='75'
                            i.dsa_percent=percent
                            
                            train_dsa=frappe.get_doc("HR Settings").training_dsa
                            dsa_rate  = frappe.db.get_value("Employee Grade", self.grade, "dsa")
                            return_dsa = frappe.get_doc("HR Settings").return_day_dsa
                            after30=frappe.get_doc("HR Settings").dsa_30_to_90
                            after90=frappe.get_doc("HR Settings").dsa_90_plus
                            within=frappe.get_doc("HR Settings").dsa_within_same_locality
                            
                            if not return_dsa:
                                frappe.throw("Set Return Day DSA Percent in HR Settings")
                            
                            if not dsa_rate:
                                frappe.throw("No DSA Rate set for Grade <b> {0} /<b> ".format(self.grade))

                            if not train_dsa:
                                frappe.throw("Set Training DSA in HR Settings")
                                
                            if not within:
                                frappe.throw("Se DSA Within Same Locality Percent in HR Settings")
                                
                            
                            
                            if self.travel_type=="Training":
                                
                                if self.within_the_dzongkhag==1:
                                    i.dsa_percent= str(within)
                                    
                                
                                i.dsa=flt(train_dsa)
                                
                                if flt(i.days_allocated)<30:
                                    
                                    i.amount = (flt(i.days_allocated)*(flt(train_dsa)))
                                    
                                elif flt(i.days_allocated)>30 and flt(i.days_allocated)<90:
                                    tot=0
                                    tot = (flt(30)*(flt(train_dsa)*flt(100)/100))
                                    tot+= (flt(flt(i.days_allocated)-30)*(flt(train_dsa)*flt(after30)/100))
                                    i.amount=tot
                                    
                                else:
                                    tot=0
                                    tot = (flt(30)*(flt(train_dsa)*flt(100)/100))
                                    tot += (flt(60)*(flt(train_dsa)*flt(after30)/100))
                                    tot += ((flt(i.days_allocated)-90)*(flt(train_dsa)*flt(after90)/100))
                                    
                                    i.amount=tot
                                
                                i.amount= i.amount*(flt(i.dsa_percent)/100)
                            else:
                                i.amount = (flt(i.days_allocated)*(flt(i.dsa)*flt(i.dsa_percent)/100))
                                
                        
                        i.amount = flt(i.amount) * flt(exchange_rate)
                        
                    elif self.place_type == "Out-Country":
                        
                        if "India" in self.country:
                            roles=frappe.get_roles(self.owner)
                        
                            if "CEO" in roles:
                                ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.country, "ceo"))
                            else:
                                ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.country, "others"))
                        else:
                            ex_country_dsa=flt(frappe.db.get_value("DSA Out Country", self.country, "dsa_rate"))
                        currency_from=frappe.db.get_value("DSA Out Country", self.country, "currency")
                        ex_country_dsa=ex_country_dsa*flt(get_exchange_rate(currency_from, company_currency, i.currency_exchange_date ))
                            
                        if i.halt != 1:
                            i.amount = (flt(i.days_allocated)*(flt(ex_country_dsa)*flt(i.dsa_percent)/100)) + (flt(i.mileage_rate) * flt(i.distance))
                            i.amount = flt(i.amount) * flt(exchange_rate)
                            i.amount += flt(i.visa_fees) * flt(visa_exchange_rate) + flt(i.passport_fees) * flt(passport_exchange_rate) + flt(i.incidental_fees) * flt(incidental_exchange_rate)
                        else:
                            i.amount = (flt(i.days_allocated)*(flt(ex_country_dsa)*flt(i.dsa_percent)/100))
                            i.amount = flt(i.amount) * flt(exchange_rate)
                            i.amount += flt(i.visa_fees) * flt(visa_exchange_rate) + flt(i.passport_fees) * flt(passport_exchange_rate) + flt(i.incidental_fees) * flt(incidental_exchange_rate)
                    
                        
                    i.actual_amount  = flt(i.amount)
                    total_claim_amount = flt(total_claim_amount) +  flt(i.actual_amount)

            self.total_claim_amount = flt(total_claim_amount)
            self.balance_amount     = flt(self.total_claim_amount) + flt(self.extra_claim_amount) - flt(self.advance_amount)

            if flt(self.balance_amount) < 0:
                    frappe.throw(_("Balance Amount cannot be a negative value."), title="Invalid Amount")
                
    def check_return_date(self):
                pass
                """
        dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
                percent = flt(flt(dsa_percent) / 100.0)
        total_claim_amount = 0
        for a in self.items:
            if a.last_day:
                a.dsa_percent = dsa_percent
                a.amount = flt(a.amount) * percent
                a.actual_amount = flt(a.amount) * flt(a.exchange_rate)
            total_claim_amount = total_claim_amount + a.actual_amount
        self.total_claim_amount = total_claim_amount
        self.balance_amount = flt(self.total_claim_amount) + flt(self.extra_claim_amount) - flt(self.advance_amount)
        """
    def check_double_date_inside(self):
        for i in self.get('items'):
        	for j in self.get('items'):
        		if i.name != j.name and str(i.date) <= str(j.till_date) and str(i.till_date) >= str(j.date):
        			frappe.throw(_("Row#{}: Dates are overlapping with Row#{}").format(i.idx, j.idx))
    def check_double_dates(self):
        if self.items:
            # check if the travel dates are already used in other travel authorization
            tas = frappe.db.sql("""select t3.idx, t1.name, t2.date, t2.till_date
                    from 
                        `tabTravel Claim` t1, 
                        `tabTravel Claim Item` t2,
                        `tabTravel Claim Item` t3
                    where t1.employee = "{employee}"
                    and t1.docstatus != 2
                    and t1.name != "{travel_claim}"
                    and t2.parent = t1.name
                    and t3.parent = "{travel_claim}"
                    and (
                        (t2.date <= t3.till_date and t2.till_date >= t3.date)
                        or
                        (t3.date <= t2.till_date and t3.till_date >= t2.date)
                    )
                    and t1.workflow_state not like '%Rejected%'
            """.format(travel_claim = self.name, employee = self.employee), as_dict=True)
            for t in tas:
                frappe.throw("Row#{}: The dates in your current Travel Claim have already been claimed in {} between {} and {}"\
                    .format(t.idx, frappe.get_desk_link("Travel Claim", t.name), t.date, t.till_date))

    ##
    # make necessary journal entry
    ##
    def post_journal_entry(self):
        if self.cost_center: 
            cost_center = self.cost_center
        else:
            cost_center = frappe.db.get_value("Employee", self.employee, "cost_center")
        if not cost_center:
            frappe.throw("Setup Cost Center for employee in Employee Information")
        # expense_bank_account = frappe.db.get_value("Branch", self.branch, "expense_bank_account")
        expense_bank_account = get_bank_account(self.branch)
        if not expense_bank_account:
            frappe.throw("Setup Default Expense Bank Account for your Branch")
        
        gl_account = ""	
        if self.travel_type == "Travel":
            if self.place_type == "In-Country":
                gl_account =  "travel_in_country_account"
            else:
                gl_account = "travel_out_country_account"
        elif self.travel_type == "Training":
            if self.place_type == "In-Country":
                gl_account = "training_in_country_account"
            else:
                gl_account = "training_out_country_account"
        # elif self.travel_type == "Project Visit":
        # 	gl_account = "project_travel_account"
        # elif self.travel_type == "BT DAY":
        # 	gl_account = "bt_day_account"
        # elif self.travel_type == "Maintenance":
        # 	if self.place_type == "In-Country":
        # 		gl_account = "travel_incountry_account"
        # elif self.travel_type == "Medical":
            # gl_account = "medical_expenses_account"
        else:
            if self.place_type == "In-Country":
                gl_account = "meeting_and_seminars_incountry_account"
            else:
                gl_account = "meeting_and_seminars_outcountry_account"
        expense_account = frappe.db.get_value("Company", self.company, gl_account)
        payable_account = frappe.get_cached_value("Company", self.company, "default_expense_claim_payable_account")
        if not expense_account:
            frappe.throw("Setup Travel/Training Accounts in Company Settings")
        advance_je = frappe.db.get_value("Travel Authorization", self.ta, "need_advance")
        je = frappe.new_doc("Journal Entry")
        je.flags.ignore_permissions = 1
        je.title = "Travel Payable (" + self.employee_name + "  " + self.name + ")"
        je.voucher_type = "Journal Entry"
        je.naming_series = "Journal Voucher"
        je.remark = 'Claim payment against : ' + self.name
        je.posting_date = self.posting_date
        je.branch = self.branch
        default_cc = frappe.db.get_value("Company", self.company, "company_cost_center")
        # if self.reference_type:
        # 	je.reference_type = self.reference_type
        # 	je.reference_name = self.reference_name

        total_amt = flt(self.total_claim_amount) + flt(self.extra_claim_amount)
        references = {}
        for a in self.items:
            if self.for_maintenance_project == 1 and not a.reference_name:
                frappe.throw("Reference cannot be empty for Project/Maintenance Travel")
            if a.reference_name:
                if a.reference_name not in references:
                    references.update({a.reference_name: {"reference_type": a.reference_type, "amount": flt(a.amount), "cost_center": frappe.db.get_value(a.reference_type, a.reference_name, "cost_center")}})
                else:
                    references[a.reference_name]['amount'] += flt(a.amount)
            else:
                if "no_ref" not in references:
                    references.update({"no_ref": {"reference_type": "Travel Claim", "amount": flt(a.amount)+flt(self.extra_claim_amount), "cost_center": cost_center}})
                else:
                    references["no_ref"]["amount"] += flt(a.amount)
        # for ref in references:
            # if references[ref]["reference_type"] == "Maintenance Order":
            # 	expense_account = frappe.db.get_value("HR Accounts Settings", "travel_incountry_account")
            # elif references[ref]["reference_type"] == "Project":
            # 	expense_account = frappe.db.get_single_value("HR Accounts Settings", "project_travel_account")
        je.append("accounts", {
                "account": expense_account,
                "reference_type": "Travel Claim",
                "reference_name": self.name,
                "cost_center": self.cost_center if self.place_type != "Out-Country" else default_cc,
                "debit_in_account_currency": flt(total_amt,2),
                "debit": flt(total_amt,2),
                "business_activity": self.business_activity,
            })
        je.append("accounts", {
                "account": payable_account,
                "reference_type": "Travel Claim",
                "reference_name": self.name,
                "cost_center": self.cost_center if self.place_type != "Out-Country" else default_cc,
                "credit_in_account_currency": flt(self.balance_amount,2),
                "credit": flt(self.balance_amount,2),
                "business_activity": self.business_activity,
                "party_type": "Employee",
                "party": self.employee, 
            })
        
        advance_amt = flt(self.advance_amount)
        bank_amt = flt(self.balance_amount)

        if (self.advance_amount) > 0:
            advance_account = frappe.db.get_value("Company", self.company,  "travel_advance_account")
            if not advance_account:
                frappe.throw("Setup Advance to Employee (Travel) in Company Settings")
            if flt(self.balance_amount) <= 0:
                advance_amt = total_amt

            je.append("accounts", {
                "account": advance_account,
                "party_type": "Employee",
                "party": self.employee,
                "reference_type": "Travel Claim",
                "reference_name": self.name,
                "cost_center": cost_center,
                "credit_in_account_currency": advance_amt,
                "credit": advance_amt,
                "business_activity": self.business_activity,
            })

        # if flt(self.balance_amount) > 0:
        # 	je.append("accounts", {
        # 			"account": payable_account if advance_je == 0 else expense_bank_account,
        # 			"party_type": "Employee" if advance_je == 0 else None,
        # 			"party": self.employee if advance_je == 0 else None,
        # 			"reference_type": "Travel Claim",
        # 			"reference_name": self.name,
        # 			"cost_center": cost_center,
        # 			"credit_in_account_currency": bank_amt,
        # 			"credit": bank_amt,
        # 			"business_activity": self.business_activity,
        # 		})
        je.insert()
        je_references = je.name
        if self.is_settlement == 0:
            if self.place_type != "Out-Country":
                je.submit()


        #Added by Thukten to make payable
        if flt(self.balance_amount) > 0:
            jeb = frappe.new_doc("Journal Entry")
            jeb.flags.ignore_permissions = 1
            jeb.title = "Travel Payment(" + self.employee_name + "  " + self.name + ")"
            jeb.voucher_type = "Bank Entry"
            jeb.naming_series = "Bank Payment Voucher"
            jeb.remark = 'Claim payment against : ' + self.name
            jeb.posting_date = self.posting_date
            jeb.branch = self.branch
            jeb.append("accounts", {
                    "account": payable_account,
                    "party_type": "Employee",
                    "party": self.employee,
                    "reference_type": "Journal Entry",
                    "reference_name": je.name,
                    "cost_center": cost_center,
                    "debit_in_account_currency": bank_amt,
                    "debit": bank_amt,
                    "business_activity": self.business_activity,
                })

            jeb.append("accounts", {
                    "account": expense_bank_account,
                    "cost_center": cost_center,
                    "reference_type": "Travel Claim",
                    "reference_name": self.name,
                    "credit_in_account_currency": bank_amt,
                    "credit": bank_amt,
                    "business_activity": self.business_activity,
                })
            jeb.insert()
            je_references = je_references + ", "+ str(jeb.name)
        self.db_set("claim_journal", je_references)

        #Set a reference to the claim journal entry

    ##
    # Update the claim reference on travel authorization
    ##
    def update_travel_authorization(self):
        count_a = 0
        for i in self.get("items"):
            count_b = 0
            idtc = count_a	
            ta = frappe.get_doc("Travel Authorization", i.travel_authorization)
            if ta.travel_claim and ta.travel_claim != self.name:
                frappe.throw("A travel claim <b>" + str(ta.travel_claim) + "</b> has already been created for the authorization <b>" + str(i.travel_authorization) + "</b>")
            ta.db_set("travel_claim", self.name)
            for a in ta.items:
                tai = frappe.get_doc("Travel Authorization Item", a.name)
                idta = count_b
                if idtc == idta:
                    tai.db_set("date",i.date)
                    tai.db_set("till_date",i.till_date)
                count_b += 1
            count_a += 1

    ##
    # Allow only approved authorizations to be submitted
    ##
    def check_status(self):
        if self.supervisor_approval == 1 and self.hr_approval == 1:
            pass
        else:
            frappe.throw("Both Supervisor and HR has to approve to submit the travel claim")
    
    ##
    # Allow only approved authorizations to be submitted
    ##
    def check_approval(self):
        if self.supervisor_approval == 0 and self.hr_approval == 1:
            frappe.throw("Supervisor has to approve the claim before HR")
    
    ##
    #Ensure the dates are consistent
    ##
    def validate_dates(self):
        if self.ta:
            self.ta_date = frappe.db.get_value("Travel Authorization", self.ta, "posting_date")
        if str(self.ta_date) > str(self.posting_date):
            frappe.throw("The Travel Claim Date cannot be earlier than Travel Authorization Date")

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
            
    

        
    

@frappe.whitelist()
def get_travel_detail(employee, start_date, end_date, place_type, travel_type):
    if employee and start_date and end_date and place_type and travel_type:
        data=[]
        query1 = "select name, dsa_per_day, currency, advance_amount from `tabTravel Authorization`  \
            where posting_date between \'"+ str(start_date) +"\' and \'"+ str(end_date) +"\' \
            and employee = \'"+ str(employee) + "\' and place_type = \'"+ str(place_type) + "\' \
            and travel_type = \'"+ str(travel_type) + "\' and docstatus = 1 and (travel_claim ='' or travel_claim is NULL)"

        for b in frappe.db.sql(query1, as_dict=True):
            for a in frappe.db.sql("select halt, from_place, to_place, date, no_days, till_date, \
                halt_to_date, halt_at, no_days from `tabTravel Authorization Item` i \
                where i.parent = %s order by `date`",b.name, as_dict=True):
                if b.currency == "BTN":
                    exchange_rate = 1
                else:
                    exchange_rate = frappe.db.get_value("Currency Exchange", {"from_currency": b.currency, "to_currency": "BTN"}, "exchange_rate")
                data.append({"name":b.name, "halt":a.halt, "from_place":a.from_place, "to_place":a.to_place, "date":a.date, "no_days":a.no_days, "till_date":a.till_date, "halt_at":a.halt_at, "dsa_per_day":b.dsa_per_day, "currency":b.currency, "exchange_rate":exchange_rate, "dsa_percent":100, "last_day":0, "advance_amount":0})
                    
            data[len(data)-1]['last_day'] = 1
            # dsa_percent = frappe.db.get_single_value("HR Settings", "return_day_dsa")
            # data[len(data)-1]['dsa_percent'] = dsa_percent
            data[len(data)-1]['advance_amount'] = b.advance_amount
            
        return data

# Following code added by SHIV on 2020/09/21
def get_permission_query_conditions(user):
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)
    permitted_regions = []
    if user == "Administrator":
        return
    if "HR User" in user_roles or "HR Manager" in user_roles:
        return
    
    if "Travel Administrator" in user_roles:
        permitted_regions = frappe.db.sql_list("""
            select 'Western Region' region from `tabWestern Region Administrators` where user = '{user}'
            union
            select 'Eastern Region' region from `tabEastern Region Administrators` where user = '{user}'
            union
            select 'South Western Region' region from `tabSouth Western Region Administrators` where user = '{user}'
            union
            select 'Central Region' region from `tabCentral Region Administrators` where user = '{user}'
            union
            select 'CHQ' region from `tabCHQ Administrators` where user = '{user}'
        """.format(user=user))

        if len(permitted_regions):
            permitted_regions = "('{}')".format(permitted_regions[0]) if len(permitted_regions) == 1 else tuple(permitted_regions)
            qry = """
                (`tabTravel Claim`.workflow_state = 'Approved'
                and (
                    exists(select 1
                        from `tabEmployee`
                        where `tabEmployee`.name = `tabTravel Claim`.employee
                        and (
                            `tabEmployee`.region in {permitted_regions}
                            or
                            ('CHQ' in {permitted_regions} and `tabEmployee`.region not in ('Western Region', 'Eastern Region',
                                'South Western Region', 'Central Region'))
                        )
                    )
                )
            )""".format(permitted_regions=permitted_regions)
            return qry

        # return """(
        # 	case when `tabTravel Claim`.workflow_state = 'Approved' then case 
        # 	when (select `tabEmployee`.region from `tabEmployee`
        # 	where `tabEmployee`.name = `tabTravel Claim`.employee
        # 	) = 'Western Region' then exists(select 1 from `tabWestern Region Administrators` where '{user}' = `tabWestern Region Administrators`.user)
         # 	when (select `tabEmployee`.region from `tabEmployee`
        # 	where `tabEmployee`.name = `tabTravel Claim`.employee
        # 	) = 'Eastern Region' then exists(select 1 from `tabEastern Region Administrators` where '{user}' = `tabEastern Region Administrators`.user)
         # 	when (select `tabEmployee`.region from `tabEmployee`
        # 	where `tabEmployee`.name = `tabTravel Claim`.employee
        # 	) = 'South Western Region' then exists(select 1 from `tabSouth Western Region Administrators` where '{user}' = `tabSouth Western Region Administrators`.user)
         # 	when (select `tabEmployee`.region from `tabEmployee`
        # 	where `tabEmployee`.name = `tabTravel Claim`.employee
        # 	) = 'Central Region' then exists(select 1 from `tabCentral Region Administrators` where '{user}' = `tabCentral Region Administrators`.user)
        # 	else exists(select 1 from `tabCHQ Administrators` where '{user}' = `tabCHQ Administrators`.user)
        # 	end
        # 	end
        # )""".format(user=user)

    return """(
        `tabTravel Claim`.owner = '{user}'
        or
        exists(select 1
                from `tabEmployee`
                where `tabEmployee`.name = `tabTravel Claim`.employee
                and `tabEmployee`.user_id = '{user}')
        or
        (`tabTravel Claim`.supervisor = '{user}' and `tabTravel Claim`.workflow_state not in ('Draft','Claimed','Approved','Rejected','Rejected By Supervisor','Waiting HR','Cancelled'))
    )""".format(user=user)


    # or
    # 	(`tabTravel Claim`.supervisor_manager = '{user}' and `tabTravel Claim`.workflow_state not in ('Draft','Approved','Claimed','Rejected','Rejected By Supervisor','Cancelled'))
    # 	or
    # 	(
    # 		case when `tabTravel Claim`.workflow_state = 'Approved' then case when (select `tabEmployee`.region from `tabEmployee`
    # 		where `tabEmployee`.name = `tabTravel Claim`.employee
    # 		) = 'Western Region' then exists(select 1 from `tabWestern Region Administrators` where '{user}' = `tabWestern Region Administrators`.user)
     # 		when (select `tabEmployee`.region from `tabEmployee`
    # 		where `tabEmployee`.name = `tabTravel Claim`.employee
    # 		) = 'Eastern Region' then exists(select 1 from `tabEastern Region Administrators` where '{user}' = `tabEastern Region Administrators`.user)
     # 		when (select `tabEmployee`.region from `tabEmployee`
    # 		where `tabEmployee`.name = `tabTravel Claim`.employee
    # 		) = 'South Western Region' then exists(select 1 from `tabSouth Western Region Administrators` where '{user}' = `tabSouth Western Region Administrators`.user)
     # 		when (select `tabEmployee`.region from `tabEmployee`
    # 		where `tabEmployee`.name = `tabTravel Claim`.employee
    # 		) = 'Central Region' then exists(select 1 from `tabCentral Region Administrators` where '{user}' = `tabCentral Region Administrators`.user)
    # 		else exists(select 1 from `tabCHQ Administrators` where '{user}' = `tabCHQ Administrators`.user)
    # 		end
    # 		end
    # 	)

