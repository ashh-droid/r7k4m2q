export type Auction = { id: string; label: string; cutoff: string };

export type Meta = {
  dataReady: boolean;
  source: string;
  retrievedAtUTC: string | null;
  actualRows: number | null;
  forecastRows: number | null;
  deliveryRange: [string, string];
  defaultDelivery: string;
  publicationLagMinutes: number;
  auctions: Auction[];
  defaultAuction: string;
};

export type Hour = {
  startTime: string;
  hour: string;
  windfor: number | null;
  plan: number | null;
  low: number | null;
  high: number | null;
  actual: number | null;
  publishTime: string | null;
  leadHours: number | null;
};

export type Day = {
  deliveryDate: string;
  auction: Auction;
  gateClosure: string;
  forecastRun: string | null;
  forecastRunCount: number;
  calibration: {
    available: boolean;
    trainingDays: number;
    method: string;
    note: string;
  };
  headline: {
    windforMW: number | null;
    planMW: number | null;
    floorMW: number | null;
    correctionMW: number | null;
    actualMW: number | null;
    level: string | null;
    hoursCompared: number;
    hoursInRange: number;
    hoursBelow: string[];
    hoursAbove: string[];
  };
  energy: { windforGWh: number | null; planGWh: number | null; floorGWh: number | null; actualGWh: number | null };
  hours: Hour[];
  halfHourActuals: { startTime: string; actual: number | null }[];
};

export type Month = {
  auction: Auction;
  summary: { n: number; biasMW: number; maeMW: number; rmseMW: number; overPct: number };
  validation: {
    n: number;
    method: string;
    evaluatedDays: number;
    minTrainingDays: number;
    rawMaeMW: number | null;
    flatMaeMW: number | null;
    levelMaeMW: number | null;
    insideRangePct: number | null;
    aboveFloorPct: number | null;
  };
  levels: { label: string; n: number; biasMW: number; maeMW: number }[];
  days: { deliveryDate: string; biasMW: number | null; maeMW: number | null }[];
  horizons: { hours: number; maeMW: number; n: number }[];
  auctionLeads: (Auction & { medianLeadHours: number })[];
  byHour: { hour: string; maeMW: number; biasMW: number }[];
  scatter: [number, number][];
};

export type Revisions = {
  startTime: string;
  hour: string;
  gateClosure: string;
  actual: number | null;
  versions: {
    publishTime: string;
    mw: number;
    status: 'before_gate' | 'after_gate' | 'after_delivery';
    selected: boolean;
  }[];
};
