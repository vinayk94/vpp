from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import List, Dict, Tuple
import asyncio
from datetime import datetime

class EventPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass(order=True)
class Event:
    priority: EventPriority
    id: str = field(compare=False)
    timestamp: datetime = field(compare=False)
    deadline: datetime = field(compare=False)
    resource_requirement: float = field(compare=False)
    duration: int = field(compare=False)
    event_type: str = field(compare=False)

@dataclass
class DER:
    id: str
    capacity: float
    available_capacity: float
    status: str
    location: str
    
    def can_allocate(self, requested_amount: float) -> bool:
        return self.available_capacity >= requested_amount

class VPPSystem:
    def __init__(self, scaling_factor: int = 1):
        self.ders: Dict[str, DER] = {}
        self.event_queues = {
            EventPriority.CRITICAL: asyncio.PriorityQueue(),
            EventPriority.HIGH: asyncio.PriorityQueue(),
            EventPriority.MEDIUM: asyncio.PriorityQueue(),
            EventPriority.LOW: asyncio.PriorityQueue(),
        }
        self.scaling_factor = scaling_factor
        self.performance_metrics = {
            'response_times': [],
            'resource_utilization': [],
            'success_rates': {p: [] for p in EventPriority},
            'processing_times': [],
            'total_events_processed': 0,
            'resource_state_history': []
        }
        self.completed_event_ids: List[str] = []

        # Log initial DER state
        logging.info(f"Initializing VPP system with scaling factor {scaling_factor}")
        for i in range(10 * scaling_factor):
            der = DER(
                id=f"der_{i}",
                capacity=1000.0,
                available_capacity=1000.0,
                status="online",
                location=f"location_{i}"
            )
            self.ders[der.id] = der
        logging.info(f"Initial DER state: {self.ders}")

    async def add_event(self, event: Event):
        """Add an event to the appropriate priority queue."""
        await self.event_queues[event.priority].put((event.timestamp, event))
        logging.info(f"Added event {event.id} to {event.priority.name} queue")

    async def process_events_loop(self):
        """Continuously process events from all priority queues."""
        logging.info("Started processing events loop.")
        processors = [self.priority_processor(priority) for priority in EventPriority]
        await asyncio.gather(*processors)

    async def priority_processor(self, priority: EventPriority):
        """Process events from a specific priority queue."""
        logging.debug(f"Started processor for {priority.name} queue.")
        while True:
            try:
                if self.event_queues[priority].empty():
                    logging.debug(f"No events in {priority.name} queue.")
                    await asyncio.sleep(0.1)
                    continue
                
                logging.debug(f"Checking {priority.name} queue for events.")
                _, event = await self.event_queues[priority].get()
                logging.info(f"Dequeued event {event.id} from {priority.name} queue.")
                
                await self.process_event(event)
                self.event_queues[priority].task_done()
            except Exception as e:
                logging.error(f"Error in {priority.name} processor: {e}")
                await asyncio.sleep(1)

    async def process_event(self, event: Event) -> bool:
        """Process a single event."""
        start_time = datetime.now()
        logging.info(f"Processing event {event.id} with priority {event.priority.name}.")

        try:
            available_ders = self._find_available_resources(event.resource_requirement)
            if not available_ders:
                logging.warning(f"Event {event.id} failed: Insufficient resources.")
                self._record_metrics(event, False, start_time)
                return False

            success, allocations = self._allocate_resources(event, available_ders)
            if not success:
                logging.warning(f"Event {event.id} failed: Resource allocation failed.")
                self._record_metrics(event, False, start_time)
                return False

            # Execute event
            execution_success = await self._execute_event(event)
            
            # Release resources
            self._release_resources(allocations)

            # Record metrics
            self._record_metrics(event, execution_success, start_time)

            if execution_success:
                logging.info(f"Event {event.id} successfully completed.")
                self.completed_event_ids.append(event.id)

            return execution_success
        except Exception as e:
            logging.error(f"Error processing event {event.id}: {e}")
            self._record_metrics(event, False, start_time)
            return False

    def _find_available_resources(self, required_capacity: float) -> List[DER]:
        """Find resources that can meet the event's requirements."""
        logging.info(f"Finding resources for capacity requirement: {required_capacity:.2f}.")
        available_ders = []
        total_available = 0.0

        for der in self.ders.values():
            logging.debug(f"DER {der.id}: Available {der.available_capacity:.2f}, Total {der.capacity:.2f}.")
            if der.available_capacity > 0:
                available_ders.append(der)
                total_available += der.available_capacity

        if total_available >= required_capacity:
            logging.info(f"Sufficient resources found: {total_available:.2f} >= {required_capacity:.2f}.")
            return sorted(available_ders, key=lambda x: x.available_capacity, reverse=True)

        logging.warning(f"Insufficient resources: {total_available:.2f} < {required_capacity:.2f}.")
        return []

    def _allocate_resources(self, event: Event, ders: List[DER]) -> Tuple[bool, List[Tuple[DER, float]]]:
        """Allocate resources to meet the event's requirements."""
        logging.info(f"Allocating resources for event {event.id}.")
        needed = event.resource_requirement
        allocations = []

        for der in ders:
            logging.debug(f"Attempting to allocate {needed:.2f} from DER {der.id} with available {der.available_capacity:.2f}")
            if needed <= 0:
                break
            allocation = min(der.available_capacity, needed)
            if allocation > 0:
                der.available_capacity -= allocation
                allocations.append((der, allocation))
                needed -= allocation

        if needed > 0:
            logging.warning(f"Could not allocate full resources for event {event.id}. Rolling back allocations.")
            for der, allocation in allocations:
                der.available_capacity += allocation
            return False, []

        return True, allocations

    def _release_resources(self, allocations: List[Tuple[DER, float]]):
        """Release allocated resources."""
        logging.info("Releasing resources.")
        for der, allocated_amount in allocations:
            logging.debug(f"Releasing {allocated_amount:.2f} to DER {der.id}.")
            der.available_capacity += allocated_amount

    async def _execute_event(self, event: Event) -> bool:
        """Simulate the execution of an event."""
        try:
            logging.info(f"Executing event {event.id} with duration {event.duration}ms.")
            await asyncio.sleep(event.duration / 1000)  # Simulate execution
            return True
        except Exception as e:
            logging.error(f"Error executing event {event.id}: {e}.")
            return False

    def _record_metrics(self, event: Event, success: bool, start_time: datetime):
        """Record performance metrics for an event."""
        response_time = (datetime.now() - start_time).total_seconds()
        self.performance_metrics['response_times'].append(response_time)
        self.performance_metrics['success_rates'][event.priority].append(success)

        total_capacity = sum(der.capacity for der in self.ders.values())
        used_capacity = sum(der.capacity - der.available_capacity for der in self.ders.values())
        utilization = used_capacity / total_capacity if total_capacity > 0 else 0
        self.performance_metrics['resource_utilization'].append(utilization)

        logging.info(f"Metrics recorded for event {event.id}: "
                     f"Response time {response_time:.3f}s, Success {success}, Utilization {utilization:.2%}.")
