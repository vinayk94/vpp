import asyncio
import pandas as pd
import numpy as np
from src.vpp import VPPSystem, Event, EventPriority
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("results/logs/experiment.log"),
        logging.StreamHandler()
    ]
)

async def run_scenarios(vpp, scale_factor):
    results = []
    scenarios = ["peak_demand", "weather_event", "resource_constraint"]

    for scenario in scenarios:
        logging.info(f"Running {scenario} scenario for scale factor {scale_factor}")
        events = []

        # Simulate events
        for i in range(10):  # Reduced to 10 for quicker debugging
            priority = np.random.choice(list(EventPriority))
            event = Event(
                id=f"{scenario}_{i}",
                priority=priority,
                timestamp=datetime.now(),
                deadline=datetime.now() + timedelta(seconds=10),
                resource_requirement=np.random.uniform(50, 200),
                duration=np.random.randint(1, 10),
                event_type=scenario
            )
            events.append(event)
            await vpp.add_event(event)
            logging.debug(f"Event {event.id} added with priority {event.priority}, "
                          f"resource requirement: {event.resource_requirement:.2f}, duration: {event.duration}")

        # Allow processing to happen
        await asyncio.sleep(10)  # Allow enough time for processing

        # Check completed events
        completed_event_ids = [e.id for e in events if e.id in vpp.completed_event_ids]
        completed_count = len(completed_event_ids)
        logging.info(f"{completed_count}/{len(events)} events completed in {scenario} scenario.")

        # Calculate metrics
        utilization = (
            np.mean(vpp.performance_metrics['resource_utilization'])
            if vpp.performance_metrics['resource_utilization']
            else 0.0
        )
        avg_response_time = (
            np.mean(vpp.performance_metrics['response_times'])
            if vpp.performance_metrics['response_times']
            else 0.0
        )
        logging.info(f"Average resource utilization: {utilization:.2%}")
        logging.info(f"Average response time: {avg_response_time:.2f}s")

        # Append results
        results.append({
            "scale_factor": scale_factor,
            "scenario": scenario,
            "total_events": len(events),
            "completed_events": completed_count,
            "utilization": utilization,
            "avg_response_time": avg_response_time,
        })

    return results

async def main():
    results = []
    for scale_factor in [1, 10]:
        logging.info(f"Starting experiments with scale factor {scale_factor}")
        vpp = VPPSystem(scale_factor)

        # Start processing loop
        asyncio.create_task(vpp.process_events_loop())

        scenario_results = await run_scenarios(vpp, scale_factor)
        results.extend(scenario_results)

    # Save results to CSV
    df = pd.DataFrame(results)
    df.to_csv("results/metrics/summary.csv", index=False)
    logging.info("Results saved successfully!")

if __name__ == "__main__":
    asyncio.run(main())
