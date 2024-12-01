from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import List, Dict, Tuple
import asyncio
from datetime import datetime

class DERState(Enum):
    AVAILABLE = "available"     # Ready for dispatch
    DISPATCHED = "dispatched"   # Actively providing grid services
    DEPLETED = "depleted"       # No available capacity
    OFFLINE = "offline"         # Maintenance or communication failure

class EventPriority(Enum):
    EMERGENCY = 1
    PEAK_DEMAND = 2
    GRID_SERVICES = 3


@dataclass(order=True)
class Event:
    priority: int
    id: str = field(compare=False)
    timestamp: datetime = field(compare=False)
    deadline: datetime = field(compare=False)
    resource_requirement: float = field(compare=False)
    duration: int = field(compare=False)
    event_type: str = field(compare=False)

@dataclass
class DER:
    id: str
    capacity: float  # Maximum capacity in kWh
    available_capacity: float  # Current available capacity in kWh
    state: DERState = DERState.AVAILABLE
    location: str = "unknown"
    
    def allocate(self, requested_amount: float) -> bool:
        """Attempt to allocate the requested amount of energy."""
        if self.state == DERState.AVAILABLE and self.available_capacity >= requested_amount:
            self.available_capacity -= requested_amount
            self.state = DERState.DISPATCHED
            if self.available_capacity <= 0:
                self.state = DERState.DEPLETED
            return True
        return False

    def release(self):
        """Release DER from dispatched state."""
        if self.state == DERState.DISPATCHED:
            self.state = DERState.AVAILABLE if self.available_capacity > 0 else DERState.DEPLETED

    def replenish(self, amount: float):
        """Replenish the DER's available capacity."""
        if self.state != DERState.OFFLINE:
            self.available_capacity = min(self.capacity, self.available_capacity + amount)
            if self.available_capacity > 0:
                self.state = DERState.AVAILABLE

class VPPSystem:
    def __init__(self, scaling_factor: int = 1, recovery_interval: int = 30):
        self.ders: Dict[str, DER] = {}
        self.event_queues = asyncio.PriorityQueue()
        self.scaling_factor = scaling_factor
        self.recovery_interval = recovery_interval  # Seconds between replenishment cycles
        self.performance_metrics = {
            "response_times": [],
            "resource_utilization": [],
            "failed_events": [],
            "successful_events": [],
            "resource_availability": []
        }
        self.completed_event_ids: List[str] = []
        self._initialize_ders()

    def _initialize_ders(self):
        """Initialize DERs with realistic capacities."""
        for i in range(10 * self.scaling_factor):
            der = DER(
                id=f"der_{i}",
                capacity=13.5,  # Tesla Powerwall-like capacity in kWh
                available_capacity=13.5,
                location=f"location_{i}"
            )
            self.ders[der.id] = der

    def calculate_total_capacity(self):
        """Calculate total fleet capacity."""
        return sum(der.available_capacity for der in self.ders.values() if der.state != DERState.OFFLINE)

    async def add_event(self, event: Event):
        """Add an event to the priority queue."""
        await self.event_queues.put((event.priority, event))
        logging.info(f"Added event {event.id} to queue with priority {event.priority}.")

    async def process_events_loop(self):
        """Continuously process events from the priority queue."""
        logging.info("Started processing events loop.")
        asyncio.create_task(self._replenish_ders_loop())  # Start replenishment loop
        while True:
            try:
                if self.event_queues.empty():
                    await asyncio.sleep(0.1)
                    continue

                _, event = await self.event_queues.get()
                logging.info(f"Processing event {event.id} with priority {event.priority}.")
                success = await self.process_event(event)
                if success:
                    self.completed_event_ids.append(event.id)
                self.event_queues.task_done()
            except Exception as e:
                logging.error(f"Error processing event: {e}")

    async def _replenish_ders_loop(self):
        """Replenish DERs periodically based on priority context."""
        while True:
            await asyncio.sleep(self.recovery_interval)
            total_capacity_before = self.calculate_total_capacity()
            logging.info(f"Before Replenishment: Total Available Capacity = {total_capacity_before:.2f} kWh.")

            for der in self.ders.values():
                replenish_amount = 7.0 if der.state != DERState.OFFLINE else 0
                der.replenish(amount=replenish_amount)
                logging.info(
                    f"Replenished DER {der.id}: {der.available_capacity:.2f}/{der.capacity:.2f} kWh."
                )

            total_capacity_after = self.calculate_total_capacity()
            logging.info(f"After Replenishment: Total Available Capacity = {total_capacity_after:.2f} kWh.")


    async def process_event(self, event: Event) -> bool:
        """Process a single event using fleet-level aggregation."""
        
        # Feasibility Check
        available_capacity = self.calculate_total_capacity()
        if event.resource_requirement > available_capacity:
            logging.warning(
                f"Event {event.id} failed: Aggregate capacity ({available_capacity:.2f} kWh) "
                f"is less than required ({event.resource_requirement:.2f} kWh)."
            )
            self.performance_metrics['failed_events'].append(event)
            return False

        # Proceed with individual DER allocation
        required_capacity = event.resource_requirement
        allocated_ders = []

        for der in self.ders.values():
            if der.state == DERState.AVAILABLE:
                allocation = min(required_capacity, der.available_capacity)
                if allocation > 0:
                    if der.allocate(allocation):
                        allocated_ders.append((der, allocation))
                        required_capacity -= allocation
                        if required_capacity <= 0:
                            break

        if required_capacity > 0:
            logging.warning(
                f"Event {event.id} failed: Insufficient DER-level resources after partial allocation. "
                f"Remaining requirement: {required_capacity:.2f} kWh."
            )
            self.performance_metrics['failed_events'].append(event)
            for der, allocation in allocated_ders:
                der.replenish(allocation)  # Rollback partial allocations
            return False

        # Simulate event execution
        await asyncio.sleep(event.duration / 1000)

        # Release resources
        for der, _ in allocated_ders:
            der.release()

        self.performance_metrics['successful_events'].append(event)
        logging.info(f"Event {event.id} successfully completed.")
        return True

