import { useEffect, useMemo, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, LineChart,
  ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { Analysis, Row, SensPoint, fetchAnalysis, fetchSensitivity } from "./api";

const DEFAULT_CUTOFF = "09:20";
const nf = new Intl.NumberFormat("en-GB", { maximumFractionDigits: 0 });
const mw = (x?: number | null) => (x == null ? "–" : `${x > 0 ? "+" : ""}${nf.format(x)}`);
const mwAbs = (x?: number | null) => (x == null ? "–" : nf.format(x));
const hhmm = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
const dayOf = (iso: string) => iso.slice(0, 10); // January: UTC date == London date

function useDebounced<T>(value: T, ms = 400) {
  const [v, setV] = useState(value);
  useEffect(() => { const t = setTimeout(() => setV(value), ms); return () => clearTimeout(t); }, [value, ms]);
  return v;
}

export default function App() {
  const [tab, setTab] = useState<"day" | "acc">("day");
  const [cutoffInput, setCutoffInput] = useState(DEFAULT_CUTOFF);
  const cutoff = useDebounced(cutoffInput);
  const [data, setData] = useState<Analysis | null>(null);
  const [sens, setSens] = useState<SensPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [day, setDay] = useState("2026-01-15");

  useEffect(() => {
    if (!/^\d{2}:\d{2}$/.test(cutoff)) return;
    setError(null);
    fetchAnalysis(cutoff).then(setData).catch((e) => setError(String(e.message ?? e)));
  }, [cutoff]);
  useEffect(() => { fetchSensitivity().then(setSens).catch(() => setSens([])); }, []);

  return (
    <div className="wrap">
      <header className="top">
        <div>
          <h1>Wind forecast desk</h1>
          <p className="sub">What the day-ahead wind forecast said when you had to buy, and how far off it was. GB national wind, January 2026.</p>
        </div>
        <div className="cutoff">
          <label htmlFor="cutoff">Buying decision made at (day before delivery, London time)</label>
          <input id="cutoff" type="time" value={cutoffInput} onChange={(e) => setCutoffInput(e.target.value)} />
          <p className="hint">
            Default 09:20 is the EPEX GB day-ahead gate closure.{" "}
            {cutoffInput !== DEFAULT_CUTOFF && <button className="link" onClick={() => setCutoffInput(DEFAULT_CUTOFF)}>Reset to 09:20</button>}
          </p>
        </div>
      </header>

      <nav className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "day"} onClick={() => setTab("day")}>Delivery day</button>
        <button role="tab" aria-selected={tab === "acc"} onClick={() => setTab("acc")}>Forecast accuracy</button>
      </nav>

      {error && <p className="err" role="alert">Could not load the analysis: {error}. Check that the backend is running on port 8000 and that the data snapshot exists.</p>}
      {!data && !error && <p className="note">Loading…</p>}
      {data && tab === "day" && <DayView data={data} day={day} setDay={setDay} />}
      {data && tab === "acc" && <AccuracyView data={data} sens={sens} cutoff={cutoff} />}

      <Method />
    </div>
  );
}

function DayView({ data, day, setDay }: { data: Analysis; day: string; setDay: (d: string) => void }) {
  const rows = useMemo(() => data.series.filter((r) => dayOf(r.start_time) === day), [data, day]);
  const withF = rows.filter((r) => r.error_mw != null);
  const mae = withF.length ? withF.reduce((s, r) => s + Math.abs(r.error_mw!), 0) / withF.length : null;
  const bias = withF.length ? withF.reduce((s, r) => s + r.error_mw!, 0) / withF.length : null;
  const runs = [...new Set(withF.map((r) => r.publish_time!))].sort();
  const lead = withF.length ? withF.reduce((s, r) => s + r.lead_time_h!, 0) / withF.length : null;
  const chart = rows.map((r) => ({ t: hhmm(r.start_time), Forecast: r.forecast_mw, Outturn: r.actual_mw }));

  return (
    <>
      <div className="charthead">
        <div>
          <h2>Forecast you would have seen, against what happened</h2>
          <p className="note">Outturn is only known after delivery; it is shown here to judge the forecast.</p>
        </div>
        <label>Delivery day <input type="date" value={day} min="2026-01-01" max="2026-01-31" onChange={(e) => e.target.value && setDay(e.target.value)} /></label>
      </div>
      <div className="strip">
        <div><div className="v">{runs.length ? runs.map(hhmm).join(", ") : "–"}</div><div className="l">Forecast run used (day before, London time)</div></div>
        <div><div className="v">{lead == null ? "–" : Math.round(lead)}<span className="u"> h</span></div><div className="l">Average time between forecast and delivery</div></div>
        <div><div className="v">{mwAbs(mae)}<span className="u"> MW</span></div><div className="l">Average miss on this day</div></div>
        <div><div className="v">{mw(bias)}<span className="u"> MW</span></div><div className="l">{bias == null ? "Bias" : bias > 0 ? "Forecast too high: risk of under-buying" : "Forecast too low: risk of over-buying"}</div></div>
      </div>
      <section className="chart" aria-label="Forecast versus outturn for the selected day">
        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart data={chart} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid stroke="var(--rule)" vertical={false} />
            <XAxis dataKey="t" interval={5} tick={{ fill: "var(--muted)", fontSize: 12 }} />
            <YAxis tickFormatter={(v) => nf.format(v)} tick={{ fill: "var(--muted)", fontSize: 12 }} label={{ value: "MW", angle: -90, position: "insideLeft", fill: "var(--muted)" }} />
            <Tooltip formatter={(v: number) => `${nf.format(v)} MW`} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)" }} />
            <Legend />
            <Line type="stepAfter" dataKey="Forecast" stroke="var(--forecast)" strokeWidth={2.5} dot={false} connectNulls />
            <Line type="monotone" dataKey="Outturn" stroke="var(--outturn)" strokeWidth={2} strokeDasharray="5 3" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </section>
    </>
  );
}

function bins(rows: Row[], width = 500) {
  const errs = rows.filter((r) => r.error_mw != null).map((r) => r.error_mw!);
  if (!errs.length) return [];
  const lo = Math.floor(Math.min(...errs) / width) * width, hi = Math.ceil(Math.max(...errs) / width) * width;
  const out = [];
  for (let b = lo; b < hi; b += width) out.push({ from: b, label: `${nf.format(b)}`, count: errs.filter((e) => e >= b && e < b + width).length });
  return out;
}

function AccuracyView({ data, sens, cutoff }: { data: Analysis; sens: SensPoint[]; cutoff: string }) {
  const m = data.metrics;
  const hist = useMemo(() => bins(data.series), [data]);
  const over = useMemo(() => {
    const e = data.series.filter((r) => r.error_mw != null);
    return e.length ? Math.round((100 * e.filter((r) => r.error_mw! > 0).length) / e.length) : null;
  }, [data]);
  if (!m.n) return <p className="note">No forecasts were available at this cutoff.</p>;
  const dir = (m.bias_mw ?? 0) > 0 ? "above" : "below";

  return (
    <>
      <p className="headline">
        With a {cutoff} decision, the forecast averaged <strong>{mwAbs(Math.abs(m.bias_mw ?? 0))} MW {dir}</strong> outturn
        and was too high in {over}% of half-hours. Plan for a one-sided miss, not just a ± band.
      </p>
      <div className="strip">
        <div><div className="v">{mwAbs(m.mae_mw)}<span className="u"> MW</span></div><div className="l">Average miss (MAE), {m.nmae_pct}% of mean outturn</div></div>
        <div><div className="v">{mwAbs(m.rmse_mw)}<span className="u"> MW</span></div><div className="l">RMSE: penalises large misses</div></div>
        <div><div className="v">{mw(m.bias_mw)}<span className="u"> MW</span></div><div className="l">Bias (forecast − outturn)</div></div>
        <div><div className="v">{mw(m.error_p05_mw)} to {mw(m.error_p95_mw)}</div><div className="l">Range covering 90% of half-hours (MW)</div></div>
      </div>

      <section className="chart">
        <h2>How big and which way the misses were</h2>
        <p className="note">Each bar counts half-hours by forecast error in MW. Amber: forecast too high. Teal: too low.</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={hist} margin={{ left: 8, right: 16 }}>
            <CartesianGrid stroke="var(--rule)" vertical={false} />
            <XAxis dataKey="label" tick={{ fill: "var(--muted)", fontSize: 11 }} interval={1} />
            <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} />
            <Tooltip formatter={(v: number) => `${v} half-hours`} labelFormatter={(l) => `Error from ${l} MW (500 MW bins)`} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)" }} />
            <ReferenceLine x={hist.find((h) => h.from === 0)?.label} stroke="var(--ink)" />
            <Bar dataKey="count">{hist.map((h) => <Cell key={h.from} fill={h.from >= 0 ? "var(--over)" : "var(--under)"} />)}</Bar>
          </BarChart>
        </ResponsiveContainer>
      </section>

      <div className="grid2">
        <section className="chart">
          <h2>Does buying later help?</h2>
          <p className="note">Metrics for each possible decision time on the day before delivery.</p>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={sens} margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke="var(--rule)" vertical={false} />
              <XAxis dataKey="cutoff" interval={5} tick={{ fill: "var(--muted)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={(v) => nf.format(v)} />
              <Tooltip formatter={(v: number) => `${nf.format(v)} MW`} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)" }} />
              <Legend />
              <ReferenceLine x={sens.find((p) => p.cutoff >= cutoff)?.cutoff} stroke="var(--ink)" strokeDasharray="3 3" />
              <Line dataKey="mae_mw" name="Average miss" stroke="var(--forecast)" strokeWidth={2.5} dot={false} />
              <Line dataKey="bias_mw" name="Bias" stroke="var(--over)" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
        <section className="chart">
          <h2>When in the day the forecast misses most</h2>
          <p className="note">Delivery hour, London time.</p>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.by_hour} margin={{ left: 8, right: 16 }}>
              <CartesianGrid stroke="var(--rule)" vertical={false} />
              <XAxis dataKey="hour" tick={{ fill: "var(--muted)", fontSize: 12 }} />
              <YAxis tick={{ fill: "var(--muted)", fontSize: 12 }} tickFormatter={(v) => nf.format(v)} />
              <Tooltip formatter={(v: number) => `${nf.format(v)} MW`} contentStyle={{ background: "var(--surface)", border: "1px solid var(--rule)" }} />
              <Legend />
              <Bar dataKey="mae_mw" name="Average miss" fill="var(--forecast)" />
              <Bar dataKey="bias_mw" name="Bias" fill="var(--over)" />
            </BarChart>
          </ResponsiveContainer>
        </section>
      </div>
    </>
  );
}

function Method() {
  return (
    <details>
      <summary>How this is calculated, and what it cannot tell you</summary>
      <ul>
        <li>For each half-hour of delivery day D, we use the most recent forecast published at or before the chosen time on day D−1. Later forecasts are never used.</li>
        <li>Forecasts are hourly and actuals half-hourly, so each forecast value is held for the following half-hour.</li>
        <li>Error = forecast − outturn. Positive means the forecast was too high, so a buyer relying on it would under-buy.</li>
        <li>Data: Elexon WINDFOR (forecast) and FUELHH, fuel type WIND (outturn), national level, January 2026 only.</li>
        <li>Limit: with only these two datasets we cannot say why forecasts ran high. Differences in coverage between the datasets, curtailment, and genuine forecast error are all possible.</li>
      </ul>
    </details>
  );
}
