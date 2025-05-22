from fastapi import APIRouter

router = APIRouter()

@router.get("/investment/ping")
async def investment_ping():
    """
    Health check endpoint for Investment service.
    """
    return {"msg": "Investment service is up"}
