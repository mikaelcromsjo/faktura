# invoices.py
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi import APIRouter, Depends, Form, Request, HTTPException, Query
from pathlib import Path
from fastapi.responses import FileResponse

from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import Column, Integer, String, DateTime, JSON, select
from sqlalchemy.orm import Session, declarative_base
from typing import Optional
from datetime import datetime
import os
from core.auth import get_current_user


from typing import List, Optional
from core.models.base import Base
from pydantic import BaseModel
from pydantic import BaseModel, Field

from datetime import datetime

from core.database import get_db   
from templates import templates
from core.database import engine
from core.models.base import Base
from models.models import Invoice, InvoiceUpdate, InvoiceNumber
from models.models import Update, Company, Caller
from core.functions.helpers import populate
from core.auth import get_current_user
from datetime import date

from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from weasyprint import HTML, CSS

router = APIRouter(prefix="/invoices", tags=["invoices"])

PDF_DIR = Path("pdfs")  # or Path("/var/www/pdfs") for production
PDF_DIR.mkdir(exist_ok=True)


# -----------------------------
# Helpers
# -----------------------------

def get_invoice_data(caller: Caller) -> dict:
    """Build invoice sender data from caller's extra fields."""
    extra = caller.extra or {}
    return {
        "name":           caller.name,
        "address_line1":  extra.get("address_line1", ""),
        "address_line2":  extra.get("address_line2", ""),
        "postal_code":    extra.get("postal_code", ""),
        "postal_address": extra.get("postal_address", ""),
        "country":        extra.get("country", ""),
        "vat_number":     extra.get("vat_number", ""),
        "bank_name":      extra.get("bank_name", ""),
        "iban":           extra.get("iban", ""),
        "bic":            extra.get("bic", ""),
        "bankgiro":       extra.get("bankgiro", ""),
        "plusgiro":       extra.get("plusgiro", ""),
        "note":           extra.get("note", ""),
        "footer":         "Reverse Charge"
    }


def get_invoice_css() -> CSS:
    """Build WeasyPrint CSS for invoice PDF."""
    bg_path = os.path.join(os.getcwd(), "core/static/images/invoice.png")
    return CSS(string=f"""
        @page {{
            size: A4;
            margin: 0cm;
            @bottom-center {{ content: element(footer); }}
            background: url('file://{bg_path}') no-repeat center center;
            background-size: cover;
        }}
        body {{ font-family: sans-serif; font-size: 12px; }}
        .footer {{
            position: running(footer);
            width: 600px;
            font-size: 11px;
            color: #444;
            text-align: left;
            padding-bottom: 100px;
        }}
        .content {{ padding: 1cm; padding-bottom: 5cm; }}
        table {{ width: 100%; border-collapse: collapse; }}
        table, th, td {{ border: 1px solid #ccc; }}
        th, td {{ padding: 5px; }}
    """)


def create_pdf(invoice_id: int, db: Session) -> Path:
    """Self-contained PDF generation. Call from anywhere with a db session."""
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    caller = db.get(Caller, invoice.caller_id)  # fetch directly from invoice
    if not caller:
        raise ValueError(f"Caller not found for invoice {invoice_id}")

    invoice_data = get_invoice_data(caller)

    template = templates.get_template("invoices/invoice.html")
    html_content = template.render(
        invoice=invoice,
        invoice_data=invoice_data,
    )

    pdf_path = PDF_DIR / f"invoice_{invoice_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    HTML(string=html_content).write_pdf(pdf_path, stylesheets=[get_invoice_css()])
    return pdf_path

# -----------------------------
# List invoices (HTMX fragment)
# -----------------------------
@router.get("/", response_class=HTMLResponse, name="invoices_list")
def invoices_list(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    query = select(Invoice)

    query = db.query(Invoice)
    if(not user.admin):
        query = db.query(Invoice).filter(Invoice.caller_id == user.caller_id)
    invoices = query.all()


    return templates.TemplateResponse(
        "invoices/list.html", {"request": request, "invoices": invoices, "is_admin": getattr(user, "admin", False),}
    )



# -----------------------------
# Invoice Detail Modal (HTMX fragment)
# -----------------------------
@router.get("/new", name="new_invoice", response_class=HTMLResponse)
def new_invoice(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    invoice = Invoice.empty()

    query = db.query(Company)
    if(not user.admin):
        query = db.query(Company).filter(Company.caller_id == user.caller_id)
    companies = query.all()


    return templates.TemplateResponse(
        "invoices/edit.html", {"request": request, "invoice": invoice, "editable": True, "companies": companies}
    )               

# -----------------------------
# Invoice Detail Modal (HTMX fragment)
# -----------------------------

@router.get("/invoice/{invoice_id}", response_class=HTMLResponse)
def invoice_detail(
    request: Request,
    invoice_id: int,
    list: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    caller = db.get(Caller, user.caller_id)
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found for current user")

    company_query = db.query(Company)
    if not user.admin:
        company_query = company_query.filter(Company.caller_id == user.caller_id)
    companies = company_query.all()

    invoice_data = get_invoice_data(caller)
    ctx = {"request": request, "invoice": invoice, "invoice_data": invoice_data, "companies": companies}

    if list == "short":
        return templates.TemplateResponse("invoices/info.html", ctx)

    elif list == "pdf":
        pdf_path = create_pdf(invoice_id, db)
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"invoice_{invoice_id}.pdf",
            headers={"Content-Disposition": f"inline; filename=invoice_{invoice_id}.pdf"}
        )

    else:
        return templates.TemplateResponse(
            "invoices/edit.html",
            {**ctx, "editable": True, "is_admin": user.admin}
        )
         
def remove_zero_rows(extra: dict) -> dict:
    if not isinstance(extra, dict):
        return extra
    
    rows = {}
    keys_to_remove = []
    
    # Parse rows into dicts (reuse your logic)
    for key, value in extra.items():
        if key.startswith("row."):
            parts = key.split(".")
            if len(parts) == 3:
                _, rownum, field = parts
                rows.setdefault(rownum, {})[field] = value
                keys_to_remove.append(key)
    
    # Filter: keep row only if BOTH price AND qty are non-zero/non-empty
    filtered_rows = {}
    for rownum, rowdata in rows.items():
        price = rowdata.get('price', '')
        qty = rowdata.get('qty', '')
        p_zero = str(price).strip() in ('', '0')
        q_zero = str(qty).strip() in ('', '0')
        if not (p_zero or q_zero):  # Keep if neither is zero
            filtered_rows[rownum] = rowdata
    
    # Remove flat keys
    for key in keys_to_remove:
        extra.pop(key, None)
    
    # Put back filtered rows as flat keys (for normalize_extra_rows)
    for rownum, rowdata in filtered_rows.items():
        for field, value in rowdata.items():
            extra[f"row.{rownum}.{field}"] = value
    
    return extra

def normalize_extra_rows(extra: dict) -> dict:

    rows = {}
    keys_to_remove = []

    for key, value in extra.items():
        if key.startswith("row."):
            parts = key.split(".")  # ['row', '1', 'description']
            if len(parts) == 3:
                _, rownum, field = parts
                rows.setdefault(rownum, {})[field] = value
                keys_to_remove.append(key)

    # Remove flat row keys
    for key in keys_to_remove:
        extra.pop(key)

    # Add normalized rows
    extra["row"] = rows

    return extra

# -----------------------------
# Update Existing invoice
# -----------------------------

@router.post("/invoice", name="upsert_invoice", response_class=HTMLResponse)
async def upsert_invoice(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):

    # Determine if this is an update or create
    invoice_id = update_data.model_dump().get("id")

    if invoice_id:
        try:
            invoice_id_int = int(invoice_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid invoice ID")
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id_int).first()

        if not invoice:
            raise HTTPException(status_code=404, detail="invoice not found")
    else:
        invoice = Invoice()
        invoice.caller_id = user.caller_id


    data_dict = update_data.model_dump(exclude_unset=True)

    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}

    # Move any keys that start with "extra." into the extra dict
    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            field_name = key.split(".", 1)[1]  # remove "extra."
            data_dict['extra'][field_name] = value
            print("value", field_name, value)
            del data_dict[key]  # optionally clean up the flat key

    data_dict['extra'] = remove_zero_rows(data_dict['extra'])
    data_dict['extra'] = normalize_extra_rows(data_dict['extra'])

    # Populate DB model dynamically

    old_status = invoice.extra.get("status") if invoice.extra else None
    invoice = populate(data_dict, invoice, InvoiceUpdate)
        
    # Check status
    status = invoice.extra.get("status") if invoice.extra else None

    create_invoice = False

    if status == "2" and not invoice.number:
        # Get the next invoice number
        seq = InvoiceNumber()
        db.add(seq)
        db.commit()          # commit to get autoincrement ID
        db.refresh(seq)
        invoice.number = str(seq.id)  # assign as string if needed
        create_invoice = True;


    if (status == "3" and old_status != "3"):
        # Delete existing PDF if it exists
        pdf_path = PDF_DIR / f"invoice_{invoice.number}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()        
        create_invoice = True


    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    if (create_invoice):
        create_pdf(invoice.id, db)




    # Render updated list (HTMX swap)
    query = db.query(Invoice)
    if(not user.admin):
        query = db.query(Invoice).filter(Invoice.caller_id == user.caller_id)
    invoices = query.all()

    response = templates.TemplateResponse(
        "invoices/list.html",
        {"request": request, "invoices": invoices},
    )
    # Set the popup message in a custom header
    response.headers["HX-Popup-Message"] = "Saved"
    return response



# DELETE invoice
@router.post("/delete/{invoice_id}", name="delete_invoice")
def delete_invoice(invoice_id: str, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    db.delete(invoice)
    db.commit()
    return {"detail": f"Invoice deleted successfully"}

