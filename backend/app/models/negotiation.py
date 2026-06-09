from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class NegotiationHistoryRecord(BaseModel):
    """Historical negotiation record from Supabase."""

    id: str
    vendor_id: str
    negotiation_date: Optional[date] = None
    discount_requested: Optional[float] = None
    discount_received: Optional[float] = None
    successful_tactics: Optional[str] = None
    failed_tactics: Optional[str] = None
    outcome: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None
    vendor_name: Optional[str] = None
    product_category: Optional[str] = None
    initial_quote_value: Optional[float] = None
    final_negotiated_value: Optional[float] = None
    strategy_used: Optional[str] = None
    negotiation_rounds: Optional[int] = None
    success_score: Optional[float] = None


class NegotiationRequest(BaseModel):
    """Request payload for negotiation retrieval and strategy generation."""

    vendor_name: str = Field(..., min_length=1, description="Vendor name")
    product_category: str = Field(..., min_length=1, description="Product category")
    quote_value: float = Field(..., gt=0, description="Current quote value")


class EmailRequest(BaseModel):
    """Request payload for procurement email generation."""

    vendor_name: str = Field(..., description="Vendor name")
    recommended_strategy: str = Field(..., description="Recommended negotiation strategy")
    expected_discount_range: str = Field(..., description="Expected discount range to use in email")


class NegotiationRetrievalResponse(BaseModel):
    """Response payload for negotiation retrieval."""

    similar_negotiations: List[NegotiationHistoryRecord] = Field(description="Top similar negotiation records")

    class Config:
        from_attributes = True


class NegotiationStrategy(BaseModel):
    """Recommended negotiation strategy output."""

    recommended_strategy: str = Field(description="Recommended procurement negotiation strategy")
    expected_discount_range: str = Field(description="Expected discount range")
    confidence_score: float = Field(description="Confidence score from 0 to 100")
    reasoning: str = Field(description="Reasoning behind the recommendation")
    risks: List[str] = Field(description="Negotiation risks")

    class Config:
        from_attributes = True


class NegotiationStrategyResult(BaseModel):
    """Internal service result for negotiation strategy generation."""

    status: str = Field(description="Status of the generation")
    strategy: NegotiationStrategy
    historical: List[NegotiationHistoryRecord]

    class Config:
        from_attributes = True


class NegotiationStrategyResponse(BaseModel):
    """Complete response for negotiation strategy analysis."""

    status: str = Field(description="Status of the analysis")
    strategy: NegotiationStrategy
    historical: List[NegotiationHistoryRecord]

    class Config:
        from_attributes = True


class NegotiationEmail(BaseModel):
    """Generated procurement negotiation email."""

    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body")

    class Config:
        from_attributes = True


class NegotiationEmailResponse(BaseModel):
    """Complete response for procurement email generation."""

    status: str = Field(description="Status of the generation")
    email: NegotiationEmail

    class Config:
        from_attributes = True
