# src/vpp_scenarios.py

import asyncio
from datetime import datetime, timedelta
import random
import logging
from typing import List, Dict
from .vpp import VPPSystem, Event, EventPriority
from src.metrics import VPPMetricsCollector as MetricsCollector
import numpy as np


class TestScenarioGenerator:
    def __init__(self, vpp_system: VPPSystem, metrics_collector: MetricsCollector):
        self.vpp = vpp_system
        self.metrics_collector = metrics_collector
        self.event_sequence = 0  # Add sequence counter

    def _get_next_sequence(self):
        self.event_sequence += 1
        return self.event_sequence

    def _create_grid_event(self, priority: EventPriority) -> Event:
        sequence = self._get_next_sequence()
        resource_req = random.uniform(50, 200) / self.vpp.scaling_factor
        return Event(
            id=f"grid_{datetime.now().timestamp()}_{sequence}",
            priority=priority,
            timestamp=datetime.now(),
            deadline=datetime.now() + timedelta(seconds=5),
            resource_requirement=resource_req,
            duration=random.randint(5, 15),
            event_type="grid_stability"
        )

    def _create_weather_event(self) -> Event:
        sequence = self._get_next_sequence()
        resource_req = random.uniform(50, 200) / self.vpp.scaling_factor
        return Event(
            id=f"weather_{datetime.now().timestamp()}_{sequence}",
            priority=EventPriority.HIGH,
            timestamp=datetime.now(),
            deadline=datetime.now() + timedelta(minutes=1),
            resource_requirement=resource_req,
            duration=random.randint(300, 900),
            event_type="weather_response"
        )

    def _create_routine_event(self) -> Event:
        sequence = self._get_next_sequence()
        resource_req = random.uniform(20, 100) / self.vpp.scaling_factor
        return Event(
            id=f"routine_{datetime.now().timestamp()}_{sequence}",
            priority=EventPriority.LOW,
            timestamp=datetime.now(),
            deadline=datetime.now() + timedelta(minutes=5),
            resource_requirement=resource_req,
            duration=random.randint(120, 600),
            event_type="routine"
        )

    def _create_mixed_event(self) -> Event:
        sequence = self._get_next_sequence()
        priority = random.choice([EventPriority.CRITICAL, EventPriority.HIGH, 
                                EventPriority.MEDIUM, EventPriority.LOW])
        return self._create_grid_event(priority=priority)

    async def run_peak_demand_scenario(self, duration_seconds: int = 20):
        logging.info("Starting peak demand scenario")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        events = []
        while datetime.now() < end_time:
            if random.random() < 0.7:  # 70% chance of critical events
                event = self._create_grid_event(priority=EventPriority.CRITICAL)
            else:
                event = self._create_grid_event(priority=EventPriority.HIGH)

            events.append(event)
            await self.vpp.add_event(event)
            await asyncio.sleep(0.2)

        return await self._collect_and_log_metrics(events, "Peak Demand")

    async def run_weather_event_scenario(self, duration_seconds: int = 20):
        logging.info("Starting weather event scenario")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        events = []
        while datetime.now() < end_time:
            if random.random() < 0.4:  # 40% weather events
                event = self._create_weather_event()
            else:
                event = self._create_routine_event()
            events.append(event)
            await self.vpp.add_event(event)
            await asyncio.sleep(0.2)

        return await self._collect_and_log_metrics(events, "Weather Event")

    async def run_resource_constraint_scenario(self, duration_seconds: int = 20):
        logging.info("Starting resource constraint scenario")
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        events = []
        while datetime.now() < end_time:
            event = self._create_mixed_event()
            events.append(event)
            await self.vpp.add_event(event)
            await asyncio.sleep(0.3)

        return await self._collect_and_log_metrics(events, "Resource Constraint")

    async def _collect_and_log_metrics(self, events: List[Event], scenario_name: str):
        results = await self.metrics_collector.collect_scenario_metrics(events)
        logging.info(f"{scenario_name} Scenario Results:")
        logging.info(f"Total events: {len(events)}")
        logging.info(f"Resource utilization: {np.mean(self.vpp.performance_metrics['resource_utilization']):.2%}")
        return results