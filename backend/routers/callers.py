from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from core.database import get_db
from core.functions.helpers import populate, build_filters
from core.auth import get_current_user
from templates import templates
from models.models import Caller, Update, CallerUpdate

# -------------------------------------------------
# Router Setup
# -------------------------------------------------
router = APIRouter(prefix="/callers", tags=["callers"])

# -------------------------------------------------
# List
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="callers_list")
def callers_list(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    callers = db.query(Caller).all()
    return templates.TemplateResponse(
        "callers/list.html",
        {"request": request, "callers": callers}
    )

# -------------------------------------------------
# Detail / New
# -------------------------------------------------
@router.get("/{caller_id}", response_class=HTMLResponse, name="caller_detail")
def caller_detail(
    request: Request,
    caller_id: str,
    list: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
):
    if int(caller_id) > 0:
        caller = db.query(Caller).filter(Caller.id == int(caller_id)).first()
        if not caller:
            raise HTTPException(status_code=404, detail="Caller not found")
    else:
        caller = Caller()

    if list == "short":
        return templates.TemplateResponse(
            "callers/info.html",
            {"request": request, "caller": caller}
        )
    return templates.TemplateResponse(
        "callers/edit.html",
        {"request": request, "caller": caller}  # Fixed: caller only
    )

# -------------------------------------------------
# Create/Update
# -------------------------------------------------
@router.post("/upsert", name="upsert_caller", response_class=HTMLResponse)
async def upsert_caller(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    # Parse ID safely
    id = update_data.model_dump().get("id")
    if id:
        try:
            id_int = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Caller ID")
        caller = db.query(Caller).filter(Caller.id == id_int).first()
        if not caller:
            raise HTTPException(status_code=404, detail="Caller not found")
    else:
        caller = Caller()

    data_dict = update_data.model_dump(exclude_unset=True)  # Only submitted fields

    # Extra dict handling (exact companies copy)
    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}
    
    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            data_dict['extra'][key.split(".", 1)[1]] = value
            del data_dict[key]

    # Populate (match EXACT companies.py signature/order)
    caller = populate(data_dict, caller, CallerUpdate)  # Check this order!
    
    db.add(caller)
    db.commit()
    db.refresh(caller)

    callers = db.query(Caller).all()
    
    response = templates.TemplateResponse(
        "callers/list.html",
        {"request": request, "callers": callers, "detail": "Updated"}
    )
    response.headers["HX-Popup-Message"] = "Saved"
    return response

# -------------------------------------------------
# Delete
# -------------------------------------------------
@router.post("/delete/{caller_id}", name="delete_caller")
def delete_caller(caller_id: str, db: Session = Depends(get_db)):
    caller = db.query(Caller).filter(Caller.id == caller_id).first()
    if not caller:
        raise HTTPException(status_code=404, detail="Caller not found")
    db.delete(caller)
    db.commit()
    return {"detail": "Deleted"}

# -------------------------------------------------
# Filters (stub)
# -------------------------------------------------
@router.get("/filter", response_class=HTMLResponse)
def caller_filter(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("callers/filter.html", {"request": request})

@router.post("/set_filter", response_class=HTMLResponse)
async def caller_set_filter(request: Request, db: Session = Depends(get_db)):
    callers = db.query(Caller).all()
    return templates.TemplateResponse(
        "callers/list.html", {"request": request, "callers": callers}
    )
