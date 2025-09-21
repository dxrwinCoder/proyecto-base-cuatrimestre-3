from fastapi import APIRouter, HTTPException
from controllers.rol_controller import *
from models.user_model import User

router = APIRouter()

nuevo_rol = RolController()

@router.get("/roles/")
async def get_roles():
    response = nuevo_rol.get_Roles()
    return response