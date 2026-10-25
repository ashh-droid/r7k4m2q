"""Reviewable public API contracts; generated OpenAPI at /api/docs."""
from __future__ import annotations
from pydantic import BaseModel, Field

class Auction(BaseModel):
    id: str
    label: str
    cutoff: str

class Calibration(BaseModel):
    available: bool
    trainingDays: int
    method: str
    note: str

class Hour(BaseModel):
    startTime: str
    hour: str
    windfor: int | None
    plan: int | None
    low: int | None
    high: int | None
    actual: int | None
    publishTime: str | None
    leadHours: float | None

class HalfHourActual(BaseModel):
    startTime: str
    actual: float | None

class DayHeadline(BaseModel):
    windforMW: int | None
    planMW: int | None
    floorMW: int | None
    correctionMW: int | None
    actualMW: int | None
    level: str | None
    hoursCompared: int
    hoursInRange: int
    hoursBelow: list[str]
    hoursAbove: list[str]

class Energy(BaseModel):
    windforGWh: float | None
    planGWh: float | None
    floorGWh: float | None
    actualGWh: float | None

class DayResponse(BaseModel):
    deliveryDate: str
    auction: Auction
    gateClosure: str
    forecastRun: str | None
    forecastRunCount: int
    calibration: Calibration
    headline: DayHeadline
    energy: Energy
    hours: list[Hour]
    halfHourActuals: list[HalfHourActual]

class HealthResponse(BaseModel):
    status: str
    dataReady: bool
    source: str

class MetaResponse(BaseModel):
    dataReady: bool
    source: str
    retrievedAtUTC: str | None = None
    actualRows: int | None = None
    forecastRows: int | None = None
    deliveryRange: list[str]
    defaultDelivery: str
    publicationLagMinutes: int
    auctions: list[Auction]
    defaultAuction: str

class MonthSummary(BaseModel):
    n: int
    biasMW: int
    maeMW: int
    rmseMW: int
    overPct: int

class Validation(BaseModel):
    method: str
    evaluatedDays: int
    minTrainingDays: int
    n: int
    rawMaeMW: int | None
    flatMaeMW: int | None
    levelMaeMW: int | None
    insideRangePct: float | None
    aboveFloorPct: float | None

class LevelStat(BaseModel):
    label: str
    n: int
    biasMW: int | None
    maeMW: int | None

class DayStat(BaseModel):
    deliveryDate: str
    biasMW: int | None
    maeMW: int | None

class HorizonStat(BaseModel):
    hours: int
    maeMW: int | None
    n: int

class AuctionLead(Auction):
    medianLeadHours: float

class HourStat(BaseModel):
    hour: str
    maeMW: int | None
    biasMW: int | None

class MonthResponse(BaseModel):
    auction: Auction
    summary: MonthSummary
    validation: Validation
    levels: list[LevelStat]
    days: list[DayStat]
    horizons: list[HorizonStat]
    auctionLeads: list[AuctionLead]
    byHour: list[HourStat]
    scatter: list[tuple[float, float]]

class RevisionVersion(BaseModel):
    publishTime: str
    mw: float
    status: str
    selected: bool

class RevisionResponse(BaseModel):
    startTime: str
    hour: str
    gateClosure: str
    actual: float | None
    versions: list[RevisionVersion]
