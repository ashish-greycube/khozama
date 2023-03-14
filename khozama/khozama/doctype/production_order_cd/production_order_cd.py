# Copyright (c) 2023, GreyCube Technologies and contributors
# For license information, please see license.txt
import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt,getdate, nowdate
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos
from frappe.utils import get_link_to_form
from erpnext.stock.get_item_details import get_conversion_factor

class ProductionOrderCD(Document):
	def validate(self):
		#  check has_serial_no=1 and is_stock_item=1
		has_serial_no, is_stock_item = frappe.db.get_value('Item',self.item_code, ['has_serial_no', 'is_stock_item'])
		if has_serial_no==0:
			frappe.throw(_("Item should be a serialzied item. 'Has Serial No' = 1."))
		if is_stock_item==0:
			frappe.throw(_("Item should be a stock item. 'Maintain Stock' = 1."))
		#  serial_no creation logic
		if self.serial_no:
			serial_nos=get_serial_nos(self.serial_no)
			print('serial_nos',serial_nos)
			if len(serial_nos)>0:	
				for serial_no in serial_nos:
					serial_no_doc=frappe.db.exists('Serial No',serial_no, cache=True)
					print('serial_no_doc',serial_no_doc)
					if serial_no_doc:
						# serial no is already created
						pass
					else:
						self.create_serial_no(serial_no)
		# remaining serial_nos to create
		self.remaining_serial_no_count=self.qty-len(get_serial_nos(self.serial_no))

		self.validate_consumption_logic()

	def validate_consumption_logic(self):
		unique_items = set()
		# consumption logic
		for item in self.consumable_items:
			# consumption item should be unique
			if item.item_code in unique_items:
				frappe.throw(_("Item {0} already exists in the consumption child table.").format(item.item_code))
			else:
				unique_items.add(item.item_code)

			if item.planned_qty==0 and item.consumption_qty==0:
				frappe.throw(_("Item Code: {0} has consumption qty {1}, It should be greater than zero.".format(item.item_code,item.consumption_qty)))	
			if item.planned_qty==0:
				item.issued_qty=0
				item.to_consume_qty=item.consumption_qty
			if item.planned_qty and item.consumption_qty < item.planned_qty:
				frappe.throw(_("Item Code: {0} has consumption qty {1}, which is less than planned qty {2}.".format(item.item_code,item.consumption_qty,item.planned_qty)))
			if item.consumption_qty < item.issued_qty:
				frappe.throw(_("Item Code: {0} has consumption qty {1}, which is less than issued qty {2}.".format(item.item_code,item.consumption_qty,item.issued_qty)))	
			item.to_consume_qty=item.consumption_qty-item.issued_qty		



	def create_serial_no(self,serial_no):
		serial_no_doc=frappe.new_doc('Serial No')	
		serial_no_doc.serial_no=serial_no
		serial_no_doc.item_code=self.item_code
		serial_no_doc.production_order_cf=self.name
		serial_no_doc.run_method("set_missing_values")
		
		# serial_no_doc.flags.ignore_validate = True					
		serial_no_doc.save(ignore_permissions=True)				
		frappe.msgprint(_("Serial No {0} is created."
		.format(get_link_to_form('Serial No', serial_no_doc.name))), alert=True)		




@frappe.whitelist()
def make_production_order(source_name, target_doc=None, ignore_permissions=False):

	def set_missing_values(source, target):
		if source.get('items'):
			for item in source.get('items'):
				target.company=source.company
				target.production_date=getdate(nowdate())
				target.so_reference=source.name
				target.item_code=item.item_code
				target.item_name=item.item_name
				target.height_cf=item.height_cf
				target.width_cf=item.width_cf
				target.area_cf=item.area_cf
				target.area_for_calculation_cf=item.area_for_calculation_cf
				target.no_of_pcs_cf=item.no_of_pcs_cf
				target.qty=item.qty
				target.remaining_serial_no_count=item.qty

				if item.consumable_item_code_1:
					target.append('consumable_items',{
						'item_code':item.consumable_item_code_1,
						'item_name':item.consumable_item_name_1,
						'planned_qty':item.consumable_planned_qty_1,
						'consumption_qty':item.consumable_planned_qty_1,
						'issued_qty':0,
						'to_consume_qty':item.consumable_planned_qty_1

					})
				
				if item.consumable_item_code_2:
					target.append('consumable_items',{
						'item_code':item.consumable_item_code_2,
						'item_name':item.consumable_item_name_2,
						'planned_qty':item.consumable_planned_qty_2,
						'consumption_qty':item.consumable_planned_qty_2,
						'issued_qty':0,
						'to_consume_qty':item.consumable_planned_qty_2						
					})

				if item.consumable_item_code_3:
					target.append('consumable_items',{
						'item_code':item.consumable_item_code_3,
						'item_name':item.consumable_item_name_3,
						'planned_qty':item.consumable_planned_qty_3,
						'consumption_qty':item.consumable_planned_qty_3,
						'issued_qty':0,
						'to_consume_qty':item.consumable_planned_qty_3							
					})

				if item.consumable_item_code_4:
					target.append('consumable_items',{
						'item_code':item.consumable_item_code_4,
						'item_name':item.consumable_item_name_4,
						'planned_qty':item.consumable_planned_qty_4,
						'consumption_qty':item.consumable_planned_qty_4,
						'issued_qty':0,
						'to_consume_qty':item.consumable_planned_qty_4							
					})										


			target.flags.ignore_permissions = ignore_permissions
		target.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		pass

	doclist = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {"doctype": "Production Order CD", "validation": {"docstatus": ["=", 1]}},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)
	return doclist	

@frappe.whitelist()
def make_material_issue_stock_entry(consumable_items,production_order):
	print('-'*10)
	print('consumable_items',consumable_items)

	consumable_items_list = consumable_items

	if isinstance(consumable_items, str):
		consumable_items_list = json.loads(consumable_items)
	elif not consumable_items:
		frappe.throw(_("No Items available for transfer"))

	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = 'Material Issue'
	stock_entry.stock_entry_type='Material Issue'
	stock_entry.company=frappe.db.get_value('Production Order CD', production_order, 'company')
	stock_entry.set_stock_entry_type()
	for rm_item_data in consumable_items_list:
		if rm_item_data["to_consume_qty"]>rm_item_data["original_consume_qty"]:
			frappe.db.set_value('Production Order Consumable Item CT',rm_item_data["production_order_consumable_hex_cf"], 'to_consume_qty', rm_item_data["to_consume_qty"])
			frappe.msgprint(_("Item {1} is updated with new to consume qty {1}")
			.format(rm_item_data.get("item_code"),rm_item_data["to_consume_qty"]))			
		details = frappe.db.get_value("Item", rm_item_data.get("item_code"), ["stock_uom", "name"], as_dict=1)
		items_dict = {
			"item_code": rm_item_data.get("item_code"),
			"qty": rm_item_data["to_consume_qty"],
			"s_warehouse": rm_item_data.get("warehouse"),
			"stock_uom": details.stock_uom,
			"conversion_factor":get_conversion_factor(rm_item_data.get("item_code"), details.stock_uom).get("conversion_factor") or 1.0,
			"production_order_cf":production_order,
			"production_order_consumable_hex_cf":rm_item_data.get("item_hexcode"),

		}
		print('items_dict',items_dict)
		stock_entry.append('items',items_dict)
	stock_entry.set_missing_values()
	stock_entry.flags.ignore_permissions = True
	stock_entry.save()
	return stock_entry.name

def update_production_order(self,method):
	if method=='on_submit':
		for item in self.items:
			if item.production_order_consumable_hex_cf:
				total_issued_qty=0
				se_details=frappe.db.get_list('Stock Entry Detail',filters={'production_order_consumable_hex_cf': item.production_order_consumable_hex_cf,'docstatus':1},
				fields=['qty','production_order_cf'],as_list=False)
				print('se_details',se_details)
				for se_detail in se_details:
					if se_detail.qty:
						total_issued_qty=total_issued_qty+se_detail.qty
				consumption_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'consumption_qty')
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty', total_issued_qty)
				to_consume_qty=consumption_qty-total_issued_qty
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'to_consume_qty', to_consume_qty)
				frappe.msgprint(_("Production Order {0} is updated for item {1} with issued qty {2}. Also, consumption and to consume qty are updated.")
			.format(get_link_to_form('Production Order CD',se_details[0].get("production_order_cf")), item.item_code,total_issued_qty),alert=True)		
				
	if method=='on_cancel':
		for item in self.items:
			if item.production_order_consumable_hex_cf:
				total_issued_qty=0
				issued_qty=frappe.db.get_value('Production Order Consumable Item CT', item.production_order_consumable_hex_cf, 'issued_qty')
				total_issued_qty=issued_qty-item.qty
				production_order_cf=item.production_order_cf
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty', total_issued_qty)
				consumption_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'consumption_qty')
				to_consume_qty=consumption_qty-total_issued_qty
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'to_consume_qty', to_consume_qty)
				frappe.msgprint(_("Production Order {0} is updated for item {1} with issued qty {2}. Also, consumption and to consume qty are updated.")
			.format(get_link_to_form('Production Order CD',production_order_cf), item.item_code,total_issued_qty),alert=True)		
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_consumable_hex_cf', None)
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_cf', None)
				frappe.msgprint(_("Material issue {0} is unlinked from Production Ordrer {1}.")
			.format(self.name,production_order_cf),alert=True)				


		

