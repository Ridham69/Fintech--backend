from fastapi import APIRouter

router = APIRouter()

@router.get("/kyc/ping")
async def kyc_ping():
    """
    Health check endpoint for KYC service.
    """
    return {"msg": "KYC service is up"}
