from fastapi import FastAPI
from backend.schemas import FYPRequest
from orchestration.graph import build_graph
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="FYP Renewable Energy Multi-Agent API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "success",
        "message": "FYP Multi-Agent API is running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


@app.post("/api/run")
def run_workflow(request: FYPRequest):
    graph = build_graph()

    state = {
        "request_id": request.request_id,
        "timestamp": "2026-10-03T00:00:00",
        "location": request.location,
        "horizon_name": request.horizon.name,
        "horizon_hours": request.horizon.hours,

        # Use the same sources that your current main.py test uses.
        "solar_source": "data/wind/raw/gujarat_hourly_weather_generation_final.csv",
        "wind_source": "data/wind/raw/gujarat_hourly_weather_generation_final.csv",
        "demand_source": "data/demand/raw/gujarat_hourly_demand_estimated.csv",

        "forecast_origin": "2026-07-30T23:00:00",

        "status": "starting",
        "errors": [],
    }

    result = graph.invoke(state)

    return result