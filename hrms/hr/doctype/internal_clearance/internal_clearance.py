# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document
from frappe.utils import validate_email_address
from frappe import _
from datetime import datetime

class InternalClearance(Document):

    def validate(self):
        self.setAprovers()
        self.workflow_action()
        
        if frappe.request.form.get('action') in ("Apply","Reject","Verify","Reapply"):
            self.send_notification()
        
    def on_submit(self):
        self.send_notification()
        
            
    def workflow_action(self):  
        action = frappe.request.form.get('action')
        
        if action == "Save":
            if self.owner !=frappe.session.user and self.iad !=frappe.session.user and self.afd !=frappe.session.user and self.ceo !=frappe.session.user and self.ictcr !=frappe.session.user and self.icthr !=frappe.session.user:
                frappe.throw("Only the Owner and Verifier and Approver can edit.")
    
        if action == "Verify":
            self.verifyUpdate()
            
            if self.icthr_clearance + self.ictcr_clearance + self.afd_clearance + self.iad_clearance == 4 :
                self.workflow_state = "Waiting Approval"
            else:
                self.workflow_state = "Waiting for Verification"
        
        if action == "Reapply":
            em= frappe.db.sql("Select user_id from `tabEmployee` where name='{}'".format(self.employee), as_dict=True)
            if frappe.session.user != em[0].user_id:
                frappe.throw("You cannot apply for another employee.")
            self.verifyUpdate()
            
    def reApply(self):
        self.iad_clearance = 0
        self.afd_clearance = 0
        self.icthr_clearance = 0
        self.ictcr_clearance = 0
        self.ceo_clearance = 0
        self.ceo_date = None
        self.iad_remarks = ""
        self.afd_remarks = ""
        self.icthr_remarks = ""
        self.ictcr_remarks = ""
        self.ceo_remarks = ""
        
        
    def verifyUpdate(self):
        user = frappe.session.user
        if user == self.iad:
            self.iad_clearance=1
        if user == self.icthr:
            self.icthr_clearance=1
        if user == self.afd:
            self.afd_clearance=1
        if user == self.ictcr:
            self.ictcr_clearance=1
        if user == self.ceo:
            self.ceo_clearance=1
            self.ceo_date=datetime.now().strftime('%Y-%m-%d')
    
    
    def send_notification(self):
        action = frappe.request.form.get('action')  
        
        if action == "Apply" or action == "Reapply":
            em= frappe.db.sql("Select user_id from `tabEmployee` where name='{}'".format(self.employee), as_dict=True)
            if frappe.session.user != em[0].user_id:
                frappe.throw("You cannot apply for another employee.")
            if self.iad_clearance + self.afd_clearance + self.icthr_clearance + self.ictcr_clearance == 0:
                recipients=[self.iad, self.ictcr, self.icthr, self.afd]
                self.notify_reviewers(recipients)
                
        if self.workflow_state == "Draft" or action == "Save":
            return
        elif self.workflow_state in ("Approved", "Rejected", "Cancelled"):
            self.notify_employee()

            if self.workflow_state == "Approved":
                self.notify_audits()
                
   
        elif self.workflow_state == "Waiting for Verification":
            if self.iad + self.afd + self.icthr + self.ictcr ==0:
                recipients=[self.iad, self.ictcr, self.icthr, self.afd]
                self.notify_reviewers(recipients)
   
        elif self.workflow_state == "Waiting Approval":
            recipients=[self.ceo]
            self.notify_reviewers(recipients)
   
    def notify_employee(self):
        self.doc = self
        parent_doc = frappe.get_doc(self.doc.doctype, self.doc.name)
        args = parent_doc.as_dict()
        args.update({
            "workflow_state": self.doc.workflow_state
        })
        
        try:
            email_template = frappe.get_doc("Email Template", 'Internal Audit Clearance Employee Notification')
            message = frappe.render_template(email_template.response, args)
            recipients = self.doc.owner
            subject = email_template.subject
            self.send_mail(recipients, message, subject)
        except :
            frappe.msgprint(_("Internal Audit Clearance notification is missing."))
        
        
    def notify_audits(self):
        audit=frappe.db.sql("select verifier_mail from `tabInternal Audit Clearance Verifier List` where parent ='Audit Settings' and parentfield='auditlist'", as_dict=True)
        audit_list=[]
        for au in audit:
            audit_list.append(au.verifier_mail)
        
        if len(audit_list)==0:
            frappe.msgprint(_("The Audit List in the Audit Settings  are missing."))
        
        parent_doc = frappe.get_doc(self.doctype, self.name)
        args = parent_doc.as_dict()
        
        try:
            email_template = frappe.get_doc("Email Template", "Internal Audit Clearance Notification to Auditor")
            message = frappe.render_template(email_template.response, args)
            subject = email_template.subject
            self.send_mail(audit_list,message,subject)
        except :
            frappe.msgprint(_("Internal Audit Clearance notification is missing."))
        
    
    def notify_reviewers(self, recipients):
        parent_doc = frappe.get_doc(self.doctype, self.name)
        args = parent_doc.as_dict()
        
        try:
            email_template = frappe.get_doc("Email Template", 'Internal Audit Clearance notification')
            message = frappe.render_template(email_template.response, args)
            subject = email_template.subject
            self.send_mail(recipients,message,subject)
        except :
            frappe.msgprint(_("Internal Audit Clearance notification is missing."))
            
       
    
    def send_mail(self, recipients, message, subject):
        
        frappe.sendmail(
                recipients=recipients,
                subject=_(subject),
                message= _(message),
                
            )
            

    def setAprovers(self):
        
        subject_list=frappe.db.sql("select verifier_mail, verifier_type  from `tabInternal Audit Clearance Verifier List` where parent ='Audit Settings' and ( parentfield='verifier' or parentfield='approver' )", as_dict=True)
        for subject in subject_list:
            if subject.verifier_type=="CEO":
                self.ceo= subject.verifier_mail  
            if subject.verifier_type=="HR":
                self.icthr= subject.verifier_mail  
            if subject.verifier_type=="Credit":
                self.ictcr= subject.verifier_mail  
            if subject.verifier_type=="Finance":
                self.afd= subject.verifier_mail  
            if subject.verifier_type=="Audit":
                self.iad= subject.verifier_mail  
        if not self.ceo and not self.icthr and not self.ictcr and not self.afd and not self.iad:
            frappe.msgprint(_("Please set Verifier and Approver in Audit Settings."))
            
  
@frappe.whitelist()
def sendemail(emails,  uname, designation, purpose, branch):
    arr=json.loads(emails)
    #frappe.throw(str(list(arr.values())))
    try:
        frappe.sendmail(
            recipients=list(arr.values()),
            subject='Waiting for Approval for Internal Audit Clearance',
            message='Dear Sir or Madam\nThere is a waiting approval for Internal Audit Clearance For Name: {uname} Designation: {designation} of Branch: {branch} for the purpose {purpose}\n\n Thank you\nPlease Do not reply to the email'.format(uname=uname, designation=designation, purpose=purpose, branch=branch),
            
        )
          
    except Exception:
        frappe.throw(str(Exception))
    
 
@frappe.whitelist()
def setemailcheck(docid):
    frappe.db.set_value('Internal Clearance', docid, 'mail_sent', 1)

def get_permission_query_conditions(user):
    permission_list=frappe.db.sql("select verifier_mail from `tabInternal Audit Clearance Verifier List` where parent ='Audit Settings'", as_dict=True)
    
    if not user: user = frappe.session.user
    user_roles = frappe.get_roles(user)
    
    for subject in permission_list:
        if user==subject.verifier_mail:
            return

    if user == "Administrator":
        return
    
    if "HR User" in user_roles or "HR Manager" in user_roles or  "Audit User" in user_roles or "Auditor Manager" in user_roles :
        return

    return """(
        `tabInternal Clearance`.owner = '{user}' 
    )""".format(user=user)
            

        


        

        
