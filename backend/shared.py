import json
import logging
import sys

from google import genai
from typing import Literal
from pydantic import BaseModel
from google.cloud import firestore


class CloudRunFormatter(logging.Formatter):
    _SEVERITY = {"DEBUG": "DEBUG", "INFO": "INFO", "WARNING": "WARNING",
                 "ERROR": "ERROR", "CRITICAL": "CRITICAL"}

    def format(self, record):
        payload = {
            "severity": self._SEVERITY.get(record.levelname, "DEFAULT"),
            "message": super().format(record),
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S") + "Z",
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level=logging.INFO):
    root = logging.getLogger()
    if root.handlers:
        return
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(CloudRunFormatter())
    root.addHandler(h)
    root.setLevel(level)
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


setup_logging()

db = firestore.Client(project="recht-technisch", database="complaints")
genai_client = genai.Client(vertexai=True, project="recht-technisch", location="europe-west1")


class MonthlyVolume(BaseModel):
    period: str  # "YYYY-MM"
    value: int


class StatItem(BaseModel):
    id: str
    value: int
    percentage: float


class MonthlyVolumeResponse(BaseModel):
    updated_at: str
    total_complaints: int
    monthly_volume: list[MonthlyVolume]


class ChartsStatsResponse(BaseModel):
    updated_at: str
    severity: list[StatItem]
    channels: list[StatItem]
    retailers: list[StatItem]


class ClusterResponse(BaseModel):
    id: str
    title: str
    text: str
    count: int


class ComplaintResponse(BaseModel):
    """A complaint shown in the detail view for a single cluster.

    ``date_created`` is always date-only, including when its source CSV
    supplied a timestamp.
    """

    id: str
    date_created: str  # "YYYY-MM-DD"
    body: str


class RecommendationResponse(BaseModel):
    id: Literal["political", "focus", "user_warning"]
    text: str
    detail: str


class IngestionResponse(BaseModel):
    inserted: int
