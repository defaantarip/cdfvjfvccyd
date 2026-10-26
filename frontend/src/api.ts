export type Row = {
  start_time: string; actual_mw: number | null; publish_time: string | null;
  forecast_mw: number | null; lead_time_h: number | null; error_mw: number | null;
};
export type Metrics = {
  n: number; mean_actual_mw?: number; mae_mw?: number; rmse_mw?: number; bias_mw?: number; nmae_pct?: number;
  error_p05_mw?: number; error_p50_mw?: number; error_p95_mw?: number; abs_error_p90_mw?: number; mean_lead_time_h?: number;
};
export type Analysis = {
  cutoff_london: string; source: string; metrics: Metrics;
  by_hour: { hour: number; mae_mw: number; bias_mw: number }[]; series: Row[];
};
export type SensPoint = { cutoff: string; n: number; mae_mw: number; rmse_mw: number; bias_mw: number; mean_lead_time_h: number };

async function get<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status}: ${(await r.json().catch(() => ({}))).detail ?? r.statusText}`);
  return r.json();
}
export const fetchAnalysis = (cutoff: string) => get<Analysis>(`/api/analysis?cutoff=${cutoff}`);
export const fetchSensitivity = () => get<{ points: SensPoint[] }>("/api/cutoff-sensitivity").then((d) => d.points);
