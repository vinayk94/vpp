
import asyncio
from datetime import datetime
import logging
import pandas as pd
from src.vpp import VPPSystem
from src.vpp_scenarios import TestScenarioGenerator
from src.metrics import VPPMetricsCollector

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("results/logs/experiment.log"),
        logging.StreamHandler()
    ]
)

async def run_scenarios(vpp: VPPSystem, generator: TestScenarioGenerator, metrics_collector: VPPMetricsCollector, duration: int = 30):
    """Run both feasibility check and stress test scenarios."""
    results = []
    scenarios = ["emergency_response", "peak_demand", "grid_stability"]

    for scenario_name in scenarios:
        # Feasibility Check Phase
        logging.info(f"Running {scenario_name} scenario (Feasibility Check).")
        logging.info(f"Fleet utilization before feasibility check: {vpp.calculate_total_capacity() / sum(der.capacity for der in vpp.ders.values()):.2%}")
        feasible_events = await generator.run_feasibility_check(scenario_name, duration_seconds=duration)
        feasible_event_metrics = metrics_collector.collect_event_metrics(feasible_events, vpp.completed_event_ids)
        feasible_fleet_metrics = metrics_collector.collect_fleet_metrics()
        logging.info(f"Fleet utilization after feasibility check: {vpp.calculate_total_capacity() / sum(der.capacity for der in vpp.ders.values()):.2%}")

        results.append({
            "scenario": f"{scenario_name}_feasibility",
            **feasible_event_metrics,
            **feasible_fleet_metrics
        })

        # Stress Test Phase
        logging.info(f"Running {scenario_name} scenario (Stress Test).")
        logging.info(f"Fleet utilization before stress test: {vpp.calculate_total_capacity() / sum(der.capacity for der in vpp.ders.values()):.2%}")
        stress_events = await generator.run_stress_test(scenario_name, duration_seconds=duration)
        stress_event_metrics = metrics_collector.collect_event_metrics(stress_events, vpp.completed_event_ids)
        stress_fleet_metrics = metrics_collector.collect_fleet_metrics()
        logging.info(f"Fleet utilization after stress test: {vpp.calculate_total_capacity() / sum(der.capacity for der in vpp.ders.values()):.2%}")

        results.append({
            "scenario": f"{scenario_name}_stress_test",
            **stress_event_metrics,
            **stress_fleet_metrics
        })

    return results

async def main():
    scaling_factors = [1, 10]  # Test with different fleet sizes
    all_results = []

    for scale in scaling_factors:
        logging.info(f"Initializing VPP System with scaling factor: {scale}.")
        vpp = VPPSystem(scaling_factor=scale)
        metrics_collector = VPPMetricsCollector(vpp.ders)
        generator = TestScenarioGenerator(vpp)

        # Start processing loop
        asyncio.create_task(vpp.process_events_loop())

        # Run scenarios
        scenario_results = await run_scenarios(vpp, generator, metrics_collector, duration=30)
        all_results.extend(scenario_results)

    # Save results to CSV
    results_df = pd.DataFrame(all_results)
    results_df.to_csv("results/metrics/summary.csv", index=False)
    logging.info("Results saved successfully!")

if __name__ == "__main__":
    asyncio.run(main())

