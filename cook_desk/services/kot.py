import frappe
from cook_desk.api.printer import enqueue_print


def process_pos_invoice(doc, method):

    items = extract_items(doc)
    mapping = get_item_kitchen_map()
    enriched = attach_kitchen(items, mapping)
    grouped = group_by_kitchen(enriched)

    create_kots(grouped, doc)


# -------------------------
def extract_items(doc):
    return [
        {"item_code": d.item_code, "qty": d.qty}
        for d in doc.items
    ]


# -------------------------
def get_item_kitchen_map():
    mapping = {}

    doc = frappe.get_all("Item Kitchen Mapping", limit=1)

    if not doc:
        frappe.throw("Item Kitchen Mapping not found")

    mapping_doc = frappe.get_doc("Item Kitchen Mapping", doc[0].name)

    for row in mapping_doc.items:
        mapping[row.item_code] = row.kitchen

    return mapping


# -------------------------
def attach_kitchen(items, mapping):
    result = []

    for item in items:
        kitchen = mapping.get(item["item_code"])

        if not kitchen:
            frappe.throw(f"No kitchen for item {item['item_code']}")

        result.append({
            "item_code": item["item_code"],
            "qty": item["qty"],
            "kitchen": kitchen
        })

    return result


# -------------------------
def group_by_kitchen(items):
    grouped = {}

    for item in items:
        kitchen = item["kitchen"]

        if kitchen not in grouped:
            grouped[kitchen] = []

        grouped[kitchen].append(item)

    return grouped


# -------------------------
def generate_kot_text(kot):
    text = ""

    text += "\n"
    text += "================================\n"
    text += "        KITCHEN ORDER\n"
    text += "================================\n"

    text += f"Invoice : {kot.pos_invoice}\n"
    text += f"Kitchen : {kot.kitchen}\n"

    text += "--------------------------------\n"

    for item in kot.items:
        text += f"{item.item_code[:20]:<20} x {item.qty}\n"

    text += "--------------------------------\n"
    text += "        *** THANK YOU ***\n\n\n"

    return text


# -------------------------
def create_kots(grouped, invoice):

    for kitchen, items in grouped.items():

        # avoid duplicate per invoice
        if frappe.db.exists("KOT", {
            "pos_invoice": invoice.name,
            "kitchen": kitchen
        }):
            continue

        printer = frappe.db.get_value("Kitchen", kitchen, "printer")

        if not printer:
            frappe.throw(f"No printer for kitchen {kitchen}")

        printer_doc = frappe.get_doc("Kitchen Printer", printer)

        kot = frappe.new_doc("KOT")
        kot.pos_invoice = invoice.name
        kot.kitchen = kitchen
        kot.printer = printer
        kot.status = "Draft"

        for item in items:
            kot.append("items", {
                "item_code": item["item_code"],
                "qty": item["qty"]
            })

        kot.insert(ignore_permissions=True)

        # 🔥 ASYNC PRINT (NO DELAY)
        content = generate_kot_text(kot)

        enqueue_print(
            printer_doc.ip_address,
            printer_doc.port or 9100,
            content
        )
