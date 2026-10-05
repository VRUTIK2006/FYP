import { useState } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import "./App.css";

function App() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  const runForecast = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.post(
        "/api/run",
        {
          request_id: `dashboard_${Date.now()}`,
          location: "Gujarat",
          horizon: {
            name: "1d",
            hours: 24,
          },
        }
      );
      console.log("API RESPONSE:", response.data);
      setData(response.data);
    } catch (err) {
      console.error(err);
      setError("Failed to run forecasting workflow. Make sure the backend is running at http://127.0.0.1:8000");
    } finally {
      setLoading(false);
    }
  };

  // ── Fix: The optimizer puts summary data under "summary_metrics", not "summary" ──
  const optimization =
    data?.optimization_result?.result?.summary_metrics ||
    data?.optimization_result?.summary_metrics ||
    data?.optimization_result?.result?.summary ||
    data?.optimization_result?.summary;

  const solarForecast =
    data?.solar_result?.result?.forecast ||
    data?.solar_result?.forecast ||
    [];

  const windForecast =
    data?.wind_result?.result?.predictions ||
    data?.wind_result?.predictions ||
    [];

  const demandForecast =
    data?.demand_result?.result?.predictions ||
    data?.demand_result?.predictions ||
    [];

  // Hourly schedule from optimizer (has combined solar+wind+demand per hour)
  const hourlySchedule =
    data?.optimization_result?.result?.hourly_schedule ||
    data?.optimization_result?.hourly_schedule ||
    [];

  /*
   * Combine the three agent outputs into one chart dataset.
   * Prefer the optimizer's hourly_schedule when available (already aligned).
   */
  const chartData =
    hourlySchedule.length > 0
      ? hourlySchedule.map((row) => ({
          hour: row.timestamp?.slice(11, 16) || "",
          solar: Number(row.solar_mu ?? 0),
          wind: Number(row.wind_mu ?? 0),
          demand: Number(row.demand_mu ?? 0),
          gridImport: Number(row.final_grid_import_mu ?? 0),
          renewable: Number(row.total_renewable_mu ?? 0),
        }))
      : Array.from({ length: 24 }, (_, index) => {
          const solar = solarForecast[index];
          const wind = windForecast[index];
          const demand = demandForecast[index];
          return {
            hour:
              solar?.timestamp?.slice(11, 16) ||
              wind?.datetime?.slice(11, 16) ||
              demand?.datetime?.slice(11, 16) ||
              `H${index + 1}`,
            solar: Number(solar?.forecast_mu ?? 0),
            wind: Number(wind?.predicted ?? 0),
            demand: Number(demand?.forecast ?? 0),
            gridImport: 0,
            renewable: 0,
          };
        });

  const hasResults = !!optimization;

  return (
    <div className="app">

      {/* HEADER */}
      <header className="header">
        <div className="header-text">
          <div className="header-logo">⚡</div>
          <div>
            <h1>Renewable Energy AI Dashboard</h1>
            <p className="header-subtitle">
              Multi-Agent Forecasting &amp; Smart Grid Management · Gujarat, India
            </p>
          </div>
        </div>

        <button
          className="run-btn"
          onClick={runForecast}
          disabled={loading}
        >
          {loading ? (
            <>
              <span className="spinner" /> Running…
            </>
          ) : (
            <>▶ Run Forecast</>
          )}
        </button>
      </header>

      {/* SUCCESS BANNER */}
      {data && !loading && (
        <div className="banner success-banner">
          ✓ Multi-agent workflow completed successfully &mdash; Solar · Wind · Demand · Optimization
        </div>
      )}

      {/* ERROR */}
      {error && (
        <div className="banner error-banner">
          ⚠ {error}
        </div>
      )}

      {/* INITIAL STATE */}
      {!data && !loading && !error && (
        <div className="welcome">
          <div className="welcome-icon">🌿</div>
          <h2>Ready to run the AI workflow</h2>
          <p>
            Click <b>▶ Run Forecast</b> to execute Solar, Wind, Demand and
            Optimization agents through the LangGraph orchestration pipeline.
          </p>
          <div className="agent-pills">
            <span className="pill solar-pill">☀️ Solar Agent</span>
            <span className="pill wind-pill">🌬️ Wind Agent</span>
            <span className="pill demand-pill">⚡ Demand Agent</span>
            <span className="pill opt-pill">🔧 Optimizer</span>
          </div>
        </div>
      )}

      {/* LOADING */}
      {loading && (
        <div className="loading-card">
          <div className="loading-spinner" />
          <div>
            <p className="loading-title">Running multi-agent forecasting workflow…</p>
            <p className="loading-sub">Solar → Wind → Demand → Optimization</p>
          </div>
        </div>
      )}

      {/* RESULTS */}
      {hasResults && (
        <>
          {/* SUMMARY KPI CARDS */}
          <section className="cards">

            <div className="card solar-card">
              <div className="card-icon">☀️</div>
              <span className="card-label">Solar Generation</span>
              <strong className="card-value">
                {optimization.total_solar_generation_mu?.toFixed(2)}
              </strong>
              <span className="card-unit">MU</span>
            </div>

            <div className="card wind-card">
              <div className="card-icon">🌬️</div>
              <span className="card-label">Wind Generation</span>
              <strong className="card-value">
                {optimization.total_wind_generation_mu?.toFixed(2)}
              </strong>
              <span className="card-unit">MU</span>
            </div>

            <div className="card demand-card">
              <div className="card-icon">⚡</div>
              <span className="card-label">Electricity Demand</span>
              <strong className="card-value">
                {optimization.total_electricity_demand_mu?.toFixed(2)}
              </strong>
              <span className="card-unit">MU</span>
            </div>

            <div className="card renew-card">
              <div className="card-icon">♻️</div>
              <span className="card-label">Renewable Penetration</span>
              <strong className="card-value">
                {optimization.renewable_penetration_pct?.toFixed(1)}
              </strong>
              <span className="card-unit">%</span>
            </div>

          </section>

          {/* 24-HOUR FORECAST CHART */}
          <section className="panel">
            <div className="panel-header">
              <div>
                <h2>24-Hour Energy Forecast</h2>
                <p className="subtitle">Solar, Wind and Electricity Demand (MU/hour)</p>
              </div>
            </div>

            <div className="chart-container">
              <ResponsiveContainer width="100%" height={380}>
                <AreaChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="windGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563eb" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#2563eb" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#dc2626" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} unit=" MU" />
                  <Tooltip
                    contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb" }}
                    formatter={(value, name) => [`${Number(value).toFixed(3)} MU`, name]}
                  />
                  <Legend />
                  <Area
                    type="monotone"
                    dataKey="solar"
                    name="Solar"
                    stroke="#f59e0b"
                    strokeWidth={2.5}
                    fill="url(#solarGrad)"
                    dot={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="wind"
                    name="Wind"
                    stroke="#2563eb"
                    strokeWidth={2.5}
                    fill="url(#windGrad)"
                    dot={false}
                  />
                  <Area
                    type="monotone"
                    dataKey="demand"
                    name="Demand"
                    stroke="#dc2626"
                    strokeWidth={2.5}
                    fill="url(#demandGrad)"
                    dot={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </section>

          {/* GRID IMPORT VS RENEWABLE CHART */}
          {hourlySchedule.length > 0 && (
            <section className="panel">
              <div className="panel-header">
                <div>
                  <h2>Grid Import vs Renewable Coverage</h2>
                  <p className="subtitle">Hourly grid import and total renewable generation (MU/hour)</p>
                </div>
              </div>

              <div className="chart-container">
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} unit=" MU" />
                    <Tooltip
                      contentStyle={{ borderRadius: "8px", border: "1px solid #e5e7eb" }}
                      formatter={(value, name) => [`${Number(value).toFixed(3)} MU`, name]}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="renewable"
                      name="Renewable"
                      stroke="#16a34a"
                      strokeWidth={2.5}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="gridImport"
                      name="Grid Import"
                      stroke="#7c3aed"
                      strokeWidth={2.5}
                      dot={false}
                      strokeDasharray="5 3"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}

          {/* OPTIMIZATION SUMMARY */}
          <section className="panel">
            <h2>Optimization Summary</h2>
            <p className="subtitle">Battery dispatch &amp; grid stability metrics</p>

            <div className="stats">

              <div className="stat-item">
                <span className="stat-label">Grid Import Required</span>
                <b className="stat-value">
                  {optimization.total_grid_import_required_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Battery Charged</span>
                <b className="stat-value">
                  {optimization.total_battery_charged_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Battery Discharged</span>
                <b className="stat-value">
                  {optimization.total_battery_discharged_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Grid Stability Index</span>
                <b className="stat-value stability">
                  {optimization.grid_stability_index?.toFixed(1)}
                  <span className="stat-unit"> / 100</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Total Renewable</span>
                <b className="stat-value green">
                  {optimization.total_renewable_generation_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Curtailed Renewable</span>
                <b className="stat-value">
                  {optimization.total_curtailed_renewable_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Effective RE Coverage</span>
                <b className="stat-value green">
                  {optimization.effective_renewable_coverage_pct?.toFixed(1)}
                  <span className="stat-unit"> %</span>
                </b>
              </div>

              <div className="stat-item">
                <span className="stat-label">Total Demand</span>
                <b className="stat-value">
                  {optimization.total_electricity_demand_mu?.toFixed(3)}
                  <span className="stat-unit"> MU</span>
                </b>
              </div>

            </div>
          </section>
        </>
      )}

    </div>
  );
}

export default App;