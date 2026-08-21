from typing import Literal
from pydantic import BaseModel
from google.cloud import firestore

db = firestore.Client(project="recht-technisch", database="complaints")

class MonthlyVolume(BaseModel):
    period: str  # "YYYY-MM"
    value: int


class StatItem(BaseModel):
    id: str
    value: int
    percentage: float


class DescriptiveStatsResponse(BaseModel):
    updated_at: str
    total_complaints: int
    monthly_volume: list[MonthlyVolume]
    severity: list[StatItem]
    channels: list[StatItem]
    retailers: list[StatItem]


class ClusterResponse(BaseModel):
    id: str
    title: str
    text: str
    count: int


class RecommendationResponse(BaseModel):
    id: Literal["political", "focus", "user_warning"]
    text: str
    detail: str
