from fastapi import APIRouter, Depends, Request, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional

from core.database import get_db
from core.functions.helpers import populate
from templates import templates
from core.models.models import User, UserUpdate  # User lives here
from models.models import Caller, Update         # Caller/Update live here
from core.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

# -------------------------------------------------
# List Users
# -------------------------------------------------
@router.get("/", response_class=HTMLResponse, name="users_list")
def users_list(
    request: Request,
    db: Session = Depends(get_db),
    user = Depends(get_current_user)
):
    if not user.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    users = db.query(User).all()
    callers = db.query(Caller).all()

    return templates.TemplateResponse(
        "users/list.html",
        {"request": request, "users": users, "callers": callers}
    )

# -------------------------------------------------
# User Detail / Edit
# -------------------------------------------------
@router.get("/{user_id}", response_class=HTMLResponse, name="user_detail")
def user_detail(
    request: Request,
    user_id: str,
    list: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    callers = db.query(Caller).all()

    if int(user_id) > 0:
        data_record = db.query(User).filter(User.id == int(user_id)).first()
        if not data_record:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        data_record = User()
        data_record.extra = {}

    if list == "short":
        return templates.TemplateResponse(
            "users/info.html",
            {"request": request, "user": data_record}
        )
    return templates.TemplateResponse(
        "users/edit.html",
        {"request": request, "user": data_record, "callers": callers}
    )

# -------------------------------------------------
# Create/Update
# -------------------------------------------------
@router.post("/user/upsert", name="upsert_user_admin", response_class=HTMLResponse)
async def upsert_user_admin(
    request: Request,
    update_data: Update,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    id = update_data.model_dump().get("id")
    if id:
        try:
            id_int = int(id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid User ID")
        data_record = db.query(User).filter(User.id == id_int).first()
        if not data_record:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        data_record = User()
        data_record.extra = {}

    data_dict = update_data.model_dump()

    if 'extra' not in data_dict or not isinstance(data_dict['extra'], dict):
        data_dict['extra'] = {}

    for key, value in list(data_dict.items()):
        if key.startswith("extra."):
            field_name = key.split(".", 1)[1]
            data_dict['extra'][field_name] = value
            del data_dict[key]

    # --- Handle password separately ---
    password = data_dict.pop("password", None)
    if not id and not password:                          # New user MUST have password
        raise HTTPException(status_code=400, detail="Password required for new user")
    
    # --- Handle caller relationship separately ---
    caller_id = data_dict.pop("caller_id", None)
    if caller_id:
        caller_id = int(caller_id)

    data_record = populate(data_dict, data_record, UserUpdate)

    # Set password (always on create, only if provided on edit)
    if password:
        data_record.set_password(password)

    if isinstance(caller_id, int):
        caller_instance = db.get(Caller, caller_id)
        if not caller_instance:
            raise HTTPException(status_code=404, detail="Caller not found")
        data_record.caller = caller_instance

    db.add(data_record)
    db.commit()
    db.refresh(data_record)

    users = db.query(User).all()
    callers = db.query(Caller).all()

    response = templates.TemplateResponse(
        "users/list.html",
        {"request": request, "users": users, "callers": callers, "detail": "Updated"}
    )
    response.headers["HX-Popup-Message"] = "Saved"
    return response


# -------------------------------------------------
# Delete
# -------------------------------------------------
@router.post("/delete/{user_id}", name="delete_user")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not current_user.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    data_record = db.query(User).filter(User.id == user_id).first()
    if not data_record:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(data_record)
    db.commit()
    return {"detail": f"User {user_id} deleted"}
