import asyncio
from datetime import datetime
import logging
import pandas as pd
from src.vpp import VPPSystem
from src.vpp_scenarios_extended import ExtendedScenarioGenerator
from src.metrics import VPPMetricsCollector

# Configure logging#
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("results/logs/extended_experiment.log"),
        logging.StreamHandler()
    ]
)

async def run_extended_scenarios(vpp: VPPSystem, generator: ExtendedScenarioGenerator, metrics_collector: VPPMetricsCollector, duration: int = 30):
    results = []
    scenarios = ["emergency_response", "peak_demand", "grid_stability"]

    for scenario_name in scenarios:
        # Extended Feasibility Phase
        logging.info(f"Running {scenario_name} extended feasibility scenario.")
        feasible_events = await generator.run_extended_feasibility(scenario_name, duration_seconds=duration)
        feasible_event_metrics = metrics_collector.collect_event_metrics(feasible_events, vpp.completed_event_ids)
        feasible_fleet_metrics = metrics_collector.collect_fleet_metrics()

        results.append({
            "scenario": f"{scenario_name}_extended_feasibility",
            **feasible_event_metrics,
            **feasible_fleet_metrics
        })

        # Extended Stress Test Phase
        logging.info(f"Running {scenario_name} extended stress test.")
        stress_events = await generator.run_extended_stress(scenario_name, duration_seconds=duration)
        stress_event_metrics = metrics_collector.collect_event_metrics(stress_events, vpp.completed_event_ids)
        stress_fleet_metrics = metrics_collector.collect_fleet_metrics()

        results.append({
            "scenario": f"{scenario_name}_extended_stress_test",
            **stress_event_metrics,
            **stress_fleet_metrics
        })

    return results

async def main():
    scaling_factors = [1, 10, 20, 50]  # Extended scaling factors
    all_results = []

    for scale in scaling_factors:
        logging.info(f"Initializing extended VPP System with scaling factor: {scale}.")
        vpp = VPPSystem(scaling_factor=scale)
        metrics_collector = VPPMetricsCollector(vpp.ders)
        generator = ExtendedScenarioGenerator(vpp)

        asyncio.create_task(vpp.process_events_loop())

        scenario_results = await run_extended_scenarios(vpp, generator, metrics_collector, duration=30)
        all_results.extend(scenario_results)

    results_df = pd.DataFrame(all_results)
    results_df.to_csv("results/metrics/extended_summary.csv", index=False)
    logging.info("Extended results saved successfully!")

if __name__ == "__main__":
    asyncio.run(main())
