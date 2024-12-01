# run_experiments.py 
import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

import asyncio
import logging
from datetime import datetime
import pandas as pd
import numpy as np

# Now import from src
from src.vpp import VPPSystem, DER, EventPriority
from src.vpp_scenarios import TestScenarioGenerator
from src.metrics import VPPMetricsCollector as MetricsCollector
#sys.exit()

import os
os.makedirs("results/logs", exist_ok=True)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("results/logs/experiment.log"),
        logging.StreamHandler()  # Optional: Keep printing to the terminal
    ]
)


async def run_experiments():
    # Configuration
    SCENARIO_DURATION = 20  # seconds per scenario
    SCALE_FACTORS = [1, 10]  # Test with 10 and 100 DERs
    
    logging.info(f"Starting experiments with {SCENARIO_DURATION}s per scenario")
    logging.info(f"Total expected duration: {SCENARIO_DURATION * 3 * len(SCALE_FACTORS)}s")
    
    results = {}
    
    for scale in SCALE_FACTORS:
        logging.info(f"Running experiments with scale factor {scale}")
        vpp = VPPSystem(scaling_factor=scale)
        der_count = 10 * scale
        
        # Initialize scaled DER fleet
        for i in range(der_count):
            vpp.ders[f"der_{i}"] = DER(
                id=f"der_{i}",
                capacity=1000.0,
                available_capacity=1000.0,
                status="online",
                location=f"location_{i}"
            )

        metrics_collector = MetricsCollector()
        scenario_gen = TestScenarioGenerator(vpp, metrics_collector)

        # Start event processor
        processor_task = asyncio.create_task(vpp.process_events_loop())

        try:
            # Run scenarios
            results[f"scale_{scale}"] = {
                'peak_demand': await scenario_gen.run_peak_demand_scenario(duration_seconds=SCENARIO_DURATION),
                'weather_event': await scenario_gen.run_weather_event_scenario(duration_seconds=SCENARIO_DURATION),
                'resource_constraint': await scenario_gen.run_resource_constraint_scenario(duration_seconds=SCENARIO_DURATION)
            }

            # Log results
            logging.info(f"Scale factor {scale} results:")
            logging.info(f"Total DERs: {der_count}")
            logging.info(f"Average response time: {np.mean(vpp.performance_metrics['response_times']):.3f}s")
            logging.info(f"Average utilization: {np.mean(vpp.performance_metrics['resource_utilization']):.2%}")
            
            for priority in EventPriority:
                success_rate = np.mean(vpp.performance_metrics['success_rates'][priority])
                logging.info(f"{priority} priority success rate: {success_rate:.2%}")

        except Exception as e:
            logging.error(f"Error in scale factor {scale}: {e}")
        finally:
            processor_task.cancel()

    return results

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler("results/logs/experiment.log"),
            logging.StreamHandler()
        ]
    )
    
    results = asyncio.run(run_experiments())