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
from erpnext.stock.doctype.item.item import get_item_defaults

class ProductionOrderCD(Document):
	def validate(self):
		self.validate_duplicate_and_set_remaining_qty()
		self.check_consumption_items_are_stock_items()
		self.check_finished_items_for_serial_no()


	def check_consumption_items_are_stock_items(self):
		# consumption logic
		for item in self.consumable_items:

			is_stock_item = frappe.db.get_value('Item',item.item_code, ['is_stock_item'])
			if is_stock_item==0:
				frappe.throw(_("Consumption Item {0}  should be a stock item. i.e. 'Maintain Stock' = 1.".format(item.item_code)))

	def check_finished_items_for_serial_no(self):
		# serial no for finished item logic
		for finished_item in self.get('finished_items'):
			#  check has_serial_no=1 and is_stock_item=1
			has_serial_no, is_stock_item = frappe.db.get_value('Item',finished_item.item_code, ['has_serial_no', 'is_stock_item'])
			if has_serial_no==0:
				frappe.throw(_("Finished Item {0} should be a serialzied item. 'Has Serial No' = 1.".format(finished_item.item_code)))
			if is_stock_item==0:
				frappe.throw(_("Finished Item {0}  should be a stock item. 'Maintain Stock' = 1.".format(finished_item.item_code)))
			#  serial_no creation logic
			if finished_item.serial_no:
				serial_nos=get_serial_nos(finished_item.serial_no)
				print('serial_nos',serial_nos)
				if len(serial_nos)>0:	
					for serial_no in serial_nos:
						serial_no_doc=frappe.db.exists('Serial No',serial_no, cache=True)
						print('serial_no_doc',serial_no_doc)
						if serial_no_doc:
							# serial no is already created
							pass
						else:
							self.create_serial_no(finished_item,serial_no)
			# remaining serial_nos to create
			finished_item.remaining_serial_no_count=finished_item.qty-len(get_serial_nos(finished_item.serial_no))

	def validate_duplicate_and_set_remaining_qty(self):
		# no duplicate finished items
		list_of_finished_items=[]
		for finished_item in self.get('finished_items'):
			if finished_item.item_code in list_of_finished_items:
				frappe.throw(_("Duplicate Finished Item {0}.").format(item.finished_item_code))
			else:
				list_of_finished_items.append(finished_item.item_code)

		unique_items = []
		# consumption logic
		for item in self.consumable_items:

			# consumption item for a finished item should be unique
			if [item.item_code] in unique_items:
				frappe.throw(_("Item {0} already exists in the consumption child table.").format(item.item_code,item.finished_item_code))
			else:
				unique_items.append([item.item_code])

			item.remaining_qty=item.planned_qty-item.issued_qty-item.scrapped_qty			



	def create_serial_no(self,finished_item,serial_no):
		serial_no_doc=frappe.new_doc('Serial No')	
		serial_no_doc.serial_no=serial_no
		serial_no_doc.item_code=finished_item.item_code
		serial_no_doc.production_order_cf=finished_item.name
		serial_no_doc.run_method("set_missing_values")
		
		# serial_no_doc.flags.ignore_validate = True					
		serial_no_doc.save(ignore_permissions=True)				
		frappe.msgprint(_("Serial No {0} is created."
		.format(get_link_to_form('Serial No', serial_no_doc.name))), alert=True)		




@frappe.whitelist()
def make_production_order(source_name, target_doc=None, ignore_permissions=False):
	connected_so_count=frappe.db.count('Production Order CD', {'so_reference': 'source_name'})
	if connected_so_count>1:
		frappe.throw(_("Only single Production Order can be connected with a Sales Order"))
	target_consumable_items=[]
	def check_and_add_consumable_item(item_code=None,item_name=None,planned_qty=None,company=None):
		found=False
		print('-'*10)
		if len(target_consumable_items)>0:
			for ci in target_consumable_items:
				print(len(ci),'len(ci)',ci,ci['planned_qty'])
				if len(ci)!=0 and ci.get('item_code') is not None and  ci.get('item_code')==item_code:
					ci.update({'planned_qty': ci['planned_qty']+planned_qty})
					ci.update({'remaining_qty': ci['remaining_qty']+planned_qty})
					found=True
					break
		if found==False:
			target_consumable_items.append({
				'item_code':item_code,
				'item_name':item_name,
				'planned_qty':planned_qty,
				'remaining_qty':planned_qty,
				'issued_qty':0,
				'scrapped_qty':0,
				'warehouse':get_item_defaults(item_code,company).get('default_warehouse')

			})

	def set_missing_values(source, target):
		if source.get('items'):
			for item in source.get('items'):
				target.company=source.company
				target.production_date=getdate(nowdate())
				target.so_reference=source.name

				if item.consumable_item_code_1:
					check_and_add_consumable_item(item_code=item.consumable_item_code_1,item_name=item.consumable_item_name_1,planned_qty=item.consumable_planned_qty_1,company=source.company)
				
				if item.consumable_item_code_2:
					check_and_add_consumable_item(item_code=item.consumable_item_code_2,item_name=item.consumable_item_name_2,planned_qty=item.consumable_planned_qty_2,company=source.company)

				if item.consumable_item_code_3:
					check_and_add_consumable_item(item_code=item.consumable_item_code_3,item_name=item.consumable_item_name_3,planned_qty=item.consumable_planned_qty_3,company=source.company)

				if item.consumable_item_code_4:
					check_and_add_consumable_item(item_code=item.consumable_item_code_4,item_name=item.consumable_item_name_4,planned_qty=item.consumable_planned_qty_4,company=source.company)

			target.flags.ignore_permissions = ignore_permissions
		for ci in target_consumable_items:
			target.append('consumable_items',ci)
		target.run_method("set_missing_values")

	def update_item(obj, target, source_parent):
		pass

	doclist = get_mapped_doc(
		"Sales Order",
		source_name,
		{
			"Sales Order": {"doctype": "Production Order CD", "validation": {"docstatus": ["=", 1]}},
			"Sales Order Item": {
				"doctype": "Production Order Finished Item CT",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"height_cf": "height_cf",
					"width_cf":"width_cf",
					"area_cf":"area_cf",
					"area_for_calculation_cf":"area_for_calculation_cf",
					"no_of_pcs_cf":"no_of_pcs_cf",
					"qty":"qty",
					"qty":"remaining_serial_no_count"
				},
			"postprocess": update_item,
		},
		},
		target_doc,
		set_missing_values,
		ignore_permissions=ignore_permissions,
	)
	return doclist	


def make_material_issue_stock_entry(rm_item_data,production_order):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = 'Material Issue'
	stock_entry.stock_entry_type='Material Issue'
	stock_entry.company=frappe.db.get_value('Production Order CD', production_order, 'company')
	stock_entry.set_stock_entry_type()
	details = frappe.db.get_value("Item", rm_item_data.get("item_code"), ["stock_uom", "name"], as_dict=1)
	items_dict = {
			"item_code": rm_item_data.get("item_code"),
			"qty": rm_item_data["to_issue_qty"],
			"s_warehouse": rm_item_data.get("warehouse"),
			"stock_uom": details.stock_uom,
			"conversion_factor":get_conversion_factor(rm_item_data.get("item_code"), details.stock_uom).get("conversion_factor") or 1.0,
			"production_order_cf":production_order,
			"production_order_consumable_hex_cf":rm_item_data.get("item_hexcode")
	}
	stock_entry.append('items',items_dict)
	stock_entry.set_missing_values()
	stock_entry.flags.ignore_permissions = True
	stock_entry.save()
	return stock_entry.name

def make_material_transfer_stock_entry(rm_item_data,production_order):
	stock_entry = frappe.new_doc("Stock Entry")
	stock_entry.purpose = 'Material Transfer'
	stock_entry.stock_entry_type='Material Transfer'
	stock_entry.company=frappe.db.get_value('Production Order CD', production_order, 'company')
	stock_entry.set_stock_entry_type()
	details = frappe.db.get_value("Item", rm_item_data.get("item_code"), ["stock_uom", "name"], as_dict=1)
	items_dict = {
			"item_code": rm_item_data.get("item_code"),
			"qty": rm_item_data["to_scrap_qty"],
			"s_warehouse": rm_item_data.get("warehouse"),
			"t_warehouse": frappe.db.get_single_value('Manufacturing Settings', 'default_scrap_warehouse'),
			"stock_uom": details.stock_uom,
			"conversion_factor":get_conversion_factor(rm_item_data.get("item_code"), details.stock_uom).get("conversion_factor") or 1.0,
			"production_order_cf":production_order,
			"production_order_consumable_hex_cf":rm_item_data.get("item_hexcode")
	}
	stock_entry.append('items',items_dict)
	stock_entry.set_missing_values()
	stock_entry.flags.ignore_permissions = True
	stock_entry.save()
	return stock_entry.name

@frappe.whitelist()
def make_stock_entry_for_consumable_items(consumable_items,production_order):
	consumable_items_list = consumable_items

	if isinstance(consumable_items, str):
		consumable_items_list = json.loads(consumable_items)
	elif not consumable_items:
		frappe.throw(_("No Items available for transfer"))
	for rm_item_data in consumable_items_list:
		if (rm_item_data["to_issue_qty"]>0):
			material_issue_name=make_material_issue_stock_entry(rm_item_data,production_order)
			print('material_issue_name',material_issue_name)
			frappe.msgprint(_("Material Issue {0} is created for item {1} for issue qty {2}.").format(get_link_to_form('Stock Entry',material_issue_name), rm_item_data.get("item_code"),rm_item_data["to_issue_qty"]),alert=False)

		if (rm_item_data["to_scrap_qty"]>0):
			material_transfer_name=make_material_transfer_stock_entry(rm_item_data,production_order)
			frappe.msgprint(_("Material Transfer {0} is created for item {1} for scrapped qty {2}.").format(get_link_to_form('Stock Entry',material_transfer_name), rm_item_data.get("item_code"),rm_item_data["to_scrap_qty"]),alert=False)




def update_production_order(self,method):
	if method=='on_submit':
		for item in self.items:
			if item.production_order_consumable_hex_cf:
				total_se_qty=0
				
				se_details=frappe.db.get_list('Stock Entry Detail',filters={'production_order_consumable_hex_cf': item.production_order_consumable_hex_cf,'docstatus':1},
				fields=['qty','production_order_cf','parent'],as_list=False)
				print('se_details',se_details)
				if self.stock_entry_type=='Material Issue':
					for se_detail in se_details:
						parent_se_type=frappe.db.get_value('Stock Entry',se_detail.parent, 'stock_entry_type')
						if se_detail.qty and parent_se_type=='Material Issue':
							total_se_qty=total_se_qty+se_detail.qty
				
				if self.stock_entry_type=='Material Transfer':
					for se_detail in se_details:
						parent_se_type=frappe.db.get_value('Stock Entry',se_detail.parent, 'stock_entry_type')
						if se_detail.qty and parent_se_type=='Material Transfer':
							total_se_qty=total_se_qty+se_detail.qty

				planned_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'planned_qty')
				remaining_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'remaining_qty')
				issued_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty')
				scrapped_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'scrapped_qty')

				if self.stock_entry_type=='Material Issue':
					frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty', total_se_qty)
					remaining_qty=planned_qty-scrapped_qty-total_se_qty
					frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'remaining_qty', remaining_qty)
					frappe.msgprint(_("Production Order {0} is updated for item {1} with issued qty {2}.")
					.format(get_link_to_form('Production Order CD',se_details[0].get("production_order_cf")), item.item_code,total_se_qty),alert=True)		
				if self.stock_entry_type=='Material Transfer':
					frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'scrapped_qty', total_se_qty)
					remaining_qty=planned_qty-issued_qty-total_se_qty
					frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'remaining_qty', remaining_qty)
					frappe.msgprint(_("Production Order {0} is updated for item {1} with scrapped qty {2}.")
					.format(get_link_to_form('Production Order CD',se_details[0].get("production_order_cf")), item.item_code,total_se_qty),alert=True)					

	if method=='on_cancel':
		for item in self.items:
			if item.production_order_consumable_hex_cf and self.stock_entry_type=='Material Issue':
				total_issued_qty=0
				issued_qty=frappe.db.get_value('Production Order Consumable Item CT', item.production_order_consumable_hex_cf, 'issued_qty')
				total_issued_qty=issued_qty-item.qty
				production_order_cf=item.production_order_cf
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty', total_issued_qty)
				
				planned_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'planned_qty')
				scrapped_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'scrapped_qty')

				remaining_qty=planned_qty-scrapped_qty-total_issued_qty
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'remaining_qty', remaining_qty)

				frappe.msgprint(_("Production Order {0} is updated for item {1} with issued qty {2}.")
			.format(get_link_to_form('Production Order CD',production_order_cf), item.item_code,total_issued_qty),alert=True)		
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_consumable_hex_cf', None)
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_cf', None)
				frappe.msgprint(_("Material issue {0} is unlinked from Production Ordrer {1}.")
			.format(self.name,production_order_cf),alert=True)				

			if item.production_order_consumable_hex_cf and self.stock_entry_type=='Material Transfer':
				total_scrapped_qty=0
				scrapped_qty=frappe.db.get_value('Production Order Consumable Item CT', item.production_order_consumable_hex_cf, 'scrapped_qty')
				total_scrapped_qty=scrapped_qty-item.qty
				production_order_cf=item.production_order_cf
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'scrapped_qty', total_scrapped_qty)
				
				planned_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'planned_qty')
				issued_qty=frappe.db.get_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'issued_qty')

				remaining_qty=planned_qty-issued_qty-total_scrapped_qty
				frappe.db.set_value('Production Order Consumable Item CT',item.production_order_consumable_hex_cf, 'remaining_qty', remaining_qty)

				frappe.msgprint(_("Production Order {0} is updated for item {1} with scrapped qty {2}.")
			.format(get_link_to_form('Production Order CD',production_order_cf), item.item_code,total_scrapped_qty),alert=True)		
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_consumable_hex_cf', None)
				frappe.db.set_value('Stock Entry Detail', item.name, 'production_order_cf', None)
				frappe.msgprint(_("Material transfer {0} is unlinked from Production Ordrer {1}.")
			.format(self.name,production_order_cf),alert=True)

		

@frappe.whitelist()
def get_item_default_warehouse(item_code,company):
	return get_item_defaults(item_code,company).get('default_warehouse')