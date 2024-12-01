import asyncio
from datetime import datetime, timedelta
import random
import logging
from .vpp import VPPSystem, EventPriority, Event

class TestScenarioGenerator:
    def __init__(self, vpp_system: VPPSystem):
        self.vpp = vpp_system
        self.event_sequence = 0

    def _get_next_sequence(self):
        self.event_sequence += 1
        return self.event_sequence

    def _create_event(self, event_type: str, priority: EventPriority, resource_req: float, duration: int) -> Event:
        """Helper function to create events with consistent parameters."""
        sequence = self._get_next_sequence()
        return Event(
            priority=priority.value,
            id=f"{event_type}_{sequence}_{datetime.now().timestamp()}",
            timestamp=datetime.now(),
            deadline=datetime.now() + timedelta(seconds=duration),
            resource_requirement=resource_req,
            duration=duration,
            event_type=event_type
        )

    async def run_feasibility_check(self, scenario_name: str, duration_seconds: int = 30):
        """Run a specific scenario with feasibility checks based on fleet capacity."""
        logging.info(f"Starting {scenario_name} scenario with feasibility checks.")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        events = []

        while datetime.now() < end_time:
            # Check fleet-level availability before generating events
            total_available_capacity = self.vpp.calculate_total_capacity()
            if scenario_name == "emergency_response":
                resource_req = random.uniform(8.0, 13.5)  # High energy requirement
                if resource_req > total_available_capacity:
                    logging.warning("Skipping event generation due to insufficient fleet capacity.")
                    await asyncio.sleep(0.5)
                    continue
                event = self._create_event(
                    event_type="emergency_response",
                    priority=EventPriority.EMERGENCY,
                    resource_req=resource_req,
                    duration=random.randint(60, 120)
                )
            elif scenario_name == "peak_demand":
                resource_req = random.uniform(5.0, 10.0)  # Moderate energy requirement
                if resource_req > total_available_capacity:
                    logging.warning("Skipping event generation due to insufficient fleet capacity.")
                    await asyncio.sleep(0.5)
                    continue
                event = self._create_event(
                    event_type="peak_demand",
                    priority=EventPriority.PEAK_DEMAND,
                    resource_req=resource_req,
                    duration=random.randint(120, 240)
                )
            elif scenario_name == "grid_stability":
                resource_req = random.uniform(2.0, 5.0)  # Low energy requirement
                if resource_req > total_available_capacity:
                    logging.warning("Skipping event generation due to insufficient fleet capacity.")
                    await asyncio.sleep(0.5)
                    continue
                event = self._create_event(
                    event_type="grid_stability",
                    priority=EventPriority.GRID_SERVICES,
                    resource_req=resource_req,
                    duration=random.randint(300, 600)
                )
            else:
                logging.warning(f"Unknown scenario: {scenario_name}. Skipping.")
                break

            events.append(event)
            await self.vpp.add_event(event)
            await asyncio.sleep(random.uniform(0.1, 0.5))  # Simulate event arrival intervals

        logging.info(f"{scenario_name} scenario completed with {len(events)} events.")
        return events

    async def run_stress_test(self, scenario_name: str, duration_seconds: int = 30):
        """Run a specific stress test scenario by intentionally exceeding capacity."""
        logging.info(f"Starting {scenario_name} stress test scenario.")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)
        events = []

        while datetime.now() < end_time:
            total_available_capacity = self.vpp.calculate_total_capacity()

            if scenario_name == "emergency_response":
                # Intentionally exceed capacity for critical events
                resource_req = total_available_capacity + random.uniform(5.0, 10.0)
                event = self._create_event(
                    event_type="emergency_response",
                    priority=EventPriority.EMERGENCY,
                    resource_req=resource_req,
                    duration=random.randint(60, 120)
                )
            elif scenario_name == "peak_demand":
                # Generate overlapping medium-priority events
                resource_req = random.uniform(8.0, 12.0)
                event = self._create_event(
                    event_type="peak_demand",
                    priority=EventPriority.PEAK_DEMAND,
                    resource_req=resource_req,
                    duration=random.randint(120, 240)
                )
            elif scenario_name == "grid_stability":
                # Generate a high volume of low-priority events
                resource_req = random.uniform(2.0, 4.0)
                event = self._create_event(
                    event_type="grid_stability",
                    priority=EventPriority.GRID_SERVICES,
                    resource_req=resource_req,
                    duration=random.randint(300, 600)
                )
            else:
                logging.warning(f"Unknown scenario: {scenario_name}. Skipping.")
                break

            events.append(event)
            await self.vpp.add_event(event)
            logging.info(f"Generated {scenario_name} event {event.id} requiring {resource_req:.2f} capacity.")

            # Shorter intervals for stress test
            await asyncio.sleep(random.uniform(0.05, 0.2))

        logging.info(f"{scenario_name} stress test scenario completed with {len(events)} events.")
        return events
