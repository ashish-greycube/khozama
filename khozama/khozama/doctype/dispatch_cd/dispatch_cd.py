# Copyright (c) 2023, GreyCube Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.stock.get_item_details import get_conversion_factor

class DispatchCD(Document):
	pass

@frappe.whitelist()
def make_material_receipt(serial_no,item_code,target_warehouse,posting_date,submit=False):
	details = frappe.db.get_value("Item", item_code, ["stock_uom", "name"], as_dict=1)
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.stock_entry_type = "Material Receipt"
	stock_entry.purpose="Material Receipt"
	stock_entry.to_warehouse = target_warehouse
	stock_entry.company =  frappe.db.get_value('Warehouse', target_warehouse, 'company')

	se_child = stock_entry.append("items")
	se_child.item_code = item_code
	se_child.stock_uom = details.stock_uom
	se_child.qty = flt(1.0)
	se_child.t_warehouse = target_warehouse
	se_child.serial_no=serial_no
	se_child.allow_zero_valuation_rate=1
	# in stock uom
	se_child.conversion_factor = flt(get_conversion_factor(item_code, details.stock_uom).get("conversion_factor") or 1.0)
	stock_entry.set_missing_values()
	stock_entry.flags.ignore_permissions = True
	stock_entry.save()
	stock_entry.submit()
	return stock_entry.name	

@frappe.whitelist()
def search_for_serial(search_value):
	# # search barcode no
	# barcode_data = frappe.db.get_value(
	# 	"Item Barcode", {"barcode": search_value}, ["barcode", "parent as item_code"], as_dict=True
	# )
	# if barcode_data:
	# 	return barcode_data

	# search serial no
	serial_no_data = frappe.db.get_value(
		"Serial No", search_value, ["name as serial_no", "item_code","status"], as_dict=True
	)
	if serial_no_data:
		return serial_no_data

	# # search batch no
	# batch_no_data = frappe.db.get_value(
	# 	"Batch", search_value, ["name as batch_no", "item as item_code"], as_dict=True
	# )
	# if batch_no_data:
	# 	return batch_no_data

	return {}