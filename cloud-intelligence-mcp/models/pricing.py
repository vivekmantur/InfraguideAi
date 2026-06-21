from pydantic import BaseModel

class AzureVmPricingRequest(BaseModel):
    """Request model for Azure VM pricing lookups.
    
    """
    region: str
    vm_sku: str

class PricingResponse(BaseModel):
    """Response model for pricing lookup results.
    
    """
    provider: str
    service: str
    sku: str
    region: str
    monthly_cost: float
    currency: str
