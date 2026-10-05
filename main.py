from orchestration.graph import build_graph


def main():

    graph = build_graph()

    initial_state = {
        "request_id": "fyp_replay_001",
        "timestamp": "2026-10-03T12:00:00",
        "location": "Gujarat",

        "horizon_name": "1d",
        "horizon_hours": 24,

        # Historical replay origin.
        # Solar/Wind will forecast the following 24 hours.
        "forecast_origin": "2026-07-30T23:00:00",

        "solar_source": (
            "data/wind/raw/"
            "gujarat_hourly_weather_generation_final.csv"
        ),

        "wind_source": (
            "data/wind/raw/"
            "gujarat_hourly_weather_generation_final.csv"
        ),

        "demand_source": (
            "data/demand/raw/"
            "gujarat_hourly_demand_estimated.csv"
        ),

        "status": "starting",
        "errors": [],
    }

    print("\n================================")
    print("FYP MULTI-AGENT LANGGRAPH")
    print("================================")

    result = graph.invoke(initial_state)

    

    print("\nWorkflow status:")
    print(result.get("status"))

    if result.get("status") == "completed":

        print("\nAgents executed:")
        print("  Solar        : SUCCESS")
        print("  Wind         : SUCCESS")
        print("  Demand       : SUCCESS")
        print("  Optimization : SUCCESS")

        optimization = result["optimization_result"]

        metrics = (
            optimization
            .get("result", {})
            .get("summary_metrics", {})
        )

        print("\nOptimization Summary")
        print("--------------------")

        for key, value in metrics.items():
            print(f"{key}: {value}")

    else:

        print("\nWorkflow failed.")

        for error in result.get("errors", []):
            print(
                f"[{error['agent']}] "
                f"{error['message']}"
            )


if __name__ == "__main__":
    main()