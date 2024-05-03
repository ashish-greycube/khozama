# Copyright (c) 2024, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import msgprint, _
from frappe.utils import flt

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns, data = [], []

	columns = get_columns(filters)
	data = get_data(filters)

	if not data:
		msgprint(_("No records found"))
		return columns, data
	
	return columns, data

def get_columns(filters):
	columns = [
		{
			"fieldname": "transaction_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 95,
		},
		{
			"fieldname": "customer",
			'label': _('Customer'),
			"fieldtype": "Link",
			"options": "Customer",
			'width':170,
		},
		{
			"fieldname": "sales_order",
			'label': _('Sales Order'),
			"fieldtype": "Link",
			"options": "Sales Order",
			'width':160,
		},
		{
			"fieldname": "production_order_cd",
			'label': _('Production Order'),
			"fieldtype": "Link",
			"options": "Production Order CD",
			'width':135,
		},
		{
			"fieldname": "selling_amount",
			'label': _('Selling Amount'),
			"fieldtype": "Currency",
			'width':120,
		},
		{
			"fieldname": "issue_cost",
			'label': _('Issue Cost'),
			"fieldtype": "Currency",
			'width':100,
		},
		{
			"fieldname": "scrap_cost",
			'label': _('Scrap Cost'),
			"fieldtype": "Currency",
			'width':100,
		},
		{
			"fieldname": "gross_profit",
			'label': _('Gross Profit'),
			"fieldtype": "Currency",
			'width':100,
		},
		{
			"fieldname": "profit_percentage",
			'label': _('Profit %'),
			"fieldtype": "Data",
			'width':100,
		}
	]
	return columns	

def get_conditions(filters):
	conditions = {}

	if filters.sales_order:
		conditions["name"] = filters.sales_order
	
	if filters.customer:
		conditions["customer"] = filters.customer

	return conditions

def get_data(filters):

	data = []
	conditions = get_conditions(filters)

	so_values = frappe.db.get_list(
		"Sales Order", fields=["transaction_date", "customer", "name"], filters=conditions
	)

	for so in so_values:
		so_items = frappe.db.get_list(
			"Sales Order Item", fields=["parent", "sum(amount) as total"], filters={"parent":so.name}, group_by="parent"
		)

		so_amount = so_items[0].total
  
		po_value = frappe.db.get_list(
			"Production Order CD", fields=["name"], filters={"so_reference":so.name}
		)

		if(len(po_value) > 0):
			po_name = po_value[0].name

			se_detalis = frappe.db.get_list(
					"Stock Entry Detail", fields=["production_order_cf", "amount", "parent"], filters={"production_order_cf": po_name}
				)
	
			issue_cost = 0
			scrap_cost = 0

			for se_detail_row in se_detalis:
				se = frappe.db.get_list(
					"Stock Entry", fields=["name","stock_entry_type"],filters={"name":se_detail_row.parent}
				)

				if(se[0].stock_entry_type == "Material Issue"):
					issue_cost = issue_cost + se_detail_row.amount

				if(se[0].stock_entry_type == "Material Transfer"):
					scrap_cost = scrap_cost + se_detail_row.amount	

			gross_profit =	so_amount - issue_cost - scrap_cost
 
			profit_percentage=0
			if so_amount>0:
				profit_percentage = flt((( gross_profit / so_amount ) * 100),2)

		else:
			po_name =""
			issue_cost = ""
			scrap_cost =""
			gross_profit = ""
			profit_percentage = ""

		row = {
			"transaction_date": so.transaction_date, 
			"customer": so.customer, 
			"sales_order": so.name, 
			"production_order_cd":po_name, 
			"selling_amount": so_amount, 
			"issue_cost":issue_cost, 
			"scrap_cost":scrap_cost, 
			"gross_profit": gross_profit, 
			"profit_percentage": profit_percentage
   }
		data.append(row)

	return data