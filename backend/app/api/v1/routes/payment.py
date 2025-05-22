from fastapi import APIRouter

router = APIRouter()

@router.get("/payment/ping")
async def payment_ping():
    """
    Health check endpoint for Payment service.
    """
    return {"msg": "Payment service is up"}
