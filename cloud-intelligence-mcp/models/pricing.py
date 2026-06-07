from pydantic import BaseModel


class AzureVmPricingRequest(BaseModel):
    region: str
    vm_sku: str


class PricingResponse(BaseModel):
    provider: str
    service: str
    sku: str
    region: str
    monthly_cost: float
    currency: str