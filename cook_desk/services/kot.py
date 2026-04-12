import frappe
from datetime import datetime
from cook_desk.api.printer import enqueue_print


def process_pos_invoice(doc, method):
    items = extract_items(doc)
    mapping = get_item_kitchen_map()
    enriched = attach_kitchen(items, mapping)
    grouped = group_by_kitchen(enriched)
    create_kots(grouped, doc)


# ─── Item Extraction ──────────────────────────────────────────────────────────

def extract_items(doc):
    return [
        {"item_code": d.item_code, "qty": d.qty}
        for d in doc.items
    ]


# ─── Kitchen Mapping ──────────────────────────────────────────────────────────

def get_item_kitchen_map():
    mapping = {}
    docs = frappe.get_all("Item Kitchen Mapping", limit=1)
    if not docs:
        frappe.throw("Item Kitchen Mapping not found")
    mapping_doc = frappe.get_doc("Item Kitchen Mapping", docs[0].name)
    for row in mapping_doc.items:
        mapping[row.item_code] = row.kitchen
    return mapping


# ─── Attach & Group ───────────────────────────────────────────────────────────

def attach_kitchen(items, mapping):
    result = []
    for item in items:
        kitchen = mapping.get(item["item_code"])
        if not kitchen:
            frappe.throw(f"No kitchen assigned for item: {item['item_code']}")
        result.append({**item, "kitchen": kitchen})
    return result


def group_by_kitchen(items):
    grouped = {}
    for item in items:
        grouped.setdefault(item["kitchen"], []).append(item)
    return grouped


# ─── KOT Text Generator (Full Width Thermal) ─────────────────────────────────

WIDTH = 48  # Standard 80mm thermal printer character width

def _line(char="-"):
    return char * WIDTH + "\n"

def _center(text):
    return text.center(WIDTH) + "\n"

def _row(left, right, width=WIDTH):
    space = width - len(left) - len(right)
    return left + " " * max(space, 1) + right + "\n"

def generate_kot_text(kot):
    now = datetime.now()
    date_str = now.strftime("%d-%b-%Y")
    time_str = now.strftime("%I:%M:%S %p")

    lines = []
    lines.append("\n")
    lines.append(_line("="))
    lines.append(_center("KITCHEN ORDER TICKET"))   # semibold equivalent → plain text
    lines.append(_line("="))
    lines.append(_center("KOT"))                    # extra bold equivalent → all caps large
    lines.append(_line("-"))
    lines.append(_row("Invoice :", kot.pos_invoice))
    lines.append(_row("Kitchen :", kot.kitchen))
    lines.append(_row("Date    :", date_str))
    lines.append(_row("Time    :", time_str))
    lines.append(_line("-"))
    lines.append(_row("ITEM", "QTY"))
    lines.append(_line("-"))

    for item in kot.items:
        name = item.item_code[:WIDTH - 8]
        qty  = f"x {int(item.qty)}"
        lines.append(_row(name, qty))

    lines.append(_line("="))
    lines.append(_center("*** PREPARE NOW ***"))
    lines.append("\n\n\n")
    return "".join(lines)


# ─── KOT Creation ─────────────────────────────────────────────────────────────

def create_kots(grouped, invoice):
    for kitchen, items in grouped.items():

        if frappe.db.exists("KOT", {
            "pos_invoice": invoice.name,
            "kitchen": kitchen
        }):
            continue

        printer_name = frappe.db.get_value("Kitchen", kitchen, "printer")
        if not printer_name:
            frappe.throw(f"No printer configured for kitchen: {kitchen}")

        printer_doc = frappe.get_doc("Kitchen Printer", printer_name)

        kot = frappe.new_doc("KOT")
        kot.pos_invoice = invoice.name
        kot.kitchen     = kitchen
        kot.printer     = printer_name
        kot.status      = "Draft"

        for item in items:
            kot.append("items", {
                "item_code": item["item_code"],
                "qty":       item["qty"],
            })

        kot.insert(ignore_permissions=True)

        content = generate_kot_text(kot)
        enqueue_print(
            printer_doc.ip_address,
            printer_doc.port or 9100,
            content,
        )
