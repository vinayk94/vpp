# src/vpp.py
from dataclasses import dataclass, field
from enum import Enum
import logging
from typing import List, Dict, Tuple
import asyncio
from datetime import datetime
import random

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
            'resource_state_history': []  # New metric to track resource states
        }

    async def add_event(self, event: Event):
        await self.event_queues[event.priority].put((event.timestamp, event))
        logging.info(f"Added event {event.id} to {event.priority} queue")

    async def process_events_loop(self):
        logging.info("Event processing loop started.")
        processors = []
        for priority in EventPriority:
            processors.append(self.priority_processor(priority))
        await asyncio.gather(*processors)

    async def priority_processor(self, priority: EventPriority):
        while True:
            try:
                if self.event_queues[priority].empty():
                    await asyncio.sleep(0.1)
                    continue
                    
                logging.info(f"Processing {priority} priority queue")
                _, event = await self.event_queues[priority].get()
                logging.info(f"Dequeued event {event.id} from {priority} queue")
                
                process_task = asyncio.create_task(self.process_event(event))
                await process_task
                
                self.event_queues[priority].task_done()
                
            except Exception as e:
                logging.error(f"Error in {priority} processor: {e}")
                await asyncio.sleep(1)

    async def process_event(self, event: Event) -> bool:
        start_time = datetime.now()
        logging.info(f"Processing event {event.id} with priority {event.priority}")
        
        try:
            available_ders = self._find_available_resources(event.resource_requirement)
            if not available_ders:
                logging.info(f"Event {event.id} failed: Insufficient resources.")
                self._record_metrics(event, False, start_time)
                return False

            success, allocations = self._allocate_resources(event, available_ders)
            if not success:
                logging.info(f"Event {event.id} failed: Resource allocation failed.")
                self._record_metrics(event, False, start_time)
                return False

            # Execute event
            execution_success = await self._execute_event(event)
            
            # Release resources using actual allocations
            self._release_resources(allocations)
            
            # Record metrics
            self._record_metrics(event, execution_success, start_time)
            
            return execution_success

        except Exception as e:
            logging.error(f"Error processing event {event.id}: {e}")
            if 'allocations' in locals() and allocations:
                self._release_resources(allocations)
            self._record_metrics(event, False, start_time)
            return False

    def _find_available_resources(self, required_capacity: float) -> List[DER]:
        logging.info(f"Finding resources for capacity requirement: {required_capacity:.2f}")
        available_ders = []
        total_available = 0.0
        
        # Log current state of all DERs
        logging.info("Current DER states:")
        for der in self.ders.values():
            logging.info(f"DER {der.id}: {der.available_capacity:.2f}/{der.capacity:.2f}")
            if der.available_capacity > 0:
                available_ders.append(der)
                total_available += der.available_capacity
                
        if total_available >= required_capacity:
            logging.info(f"Found sufficient total resources: {total_available:.2f} >= {required_capacity:.2f}")
            # Sort by available capacity to distribute load better
            return sorted(available_ders, key=lambda x: x.available_capacity, reverse=True)
        
        logging.info(f"Insufficient total resources: {total_available:.2f} < {required_capacity:.2f}")
        return []

    def _allocate_resources(self, event: Event, ders: List[DER]) -> Tuple[bool, List[Tuple[DER, float]]]:
        logging.info(f"Allocating resources for event {event.id}")
        needed = event.resource_requirement
        allocations = []
        
        try:
            for der in ders:
                if needed <= 0:
                    break
                    
                allocation = min(der.available_capacity, needed)
                if allocation > 0:
                    original_capacity = der.available_capacity
                    der.available_capacity -= allocation
                    allocations.append((der, allocation))
                    needed -= allocation
                    logging.info(f"DER {der.id} allocated {allocation:.2f}, capacity changed: {original_capacity:.2f} -> {der.available_capacity:.2f}")
            
            if needed > 0:
                logging.info(f"Could not allocate full requirement. Remaining needed: {needed:.2f}")
                # Rollback allocations
                for der, amount in allocations:
                    der.available_capacity += amount
                    logging.info(f"Rolled back DER {der.id} allocation: restored {amount:.2f}")
                return False, []
                
            self._log_resource_state()
            return True, allocations
            
        except Exception as e:
            logging.error(f"Error during resource allocation: {e}")
            # Rollback on error
            for der, amount in allocations:
                der.available_capacity += amount
                logging.info(f"Error rollback: restored {amount:.2f} to DER {der.id}")
            return False, []

    def _release_resources(self, allocations: List[Tuple[DER, float]]):
        logging.info("Releasing allocated resources")
        
        # Log state before release
        logging.info("DER states before release:")
        for der in self.ders.values():
            logging.info(f"DER {der.id} before release: {der.available_capacity:.2f}/{der.capacity:.2f}")
        
        # Release only what was allocated to each DER
        for der, allocated_amount in allocations:
            original_capacity = der.available_capacity
            der.available_capacity += allocated_amount
            # Ensure we don't exceed maximum capacity
            der.available_capacity = min(der.available_capacity, der.capacity)
            logging.info(f"DER {der.id} released {allocated_amount:.2f}, capacity changed: {original_capacity:.2f} -> {der.available_capacity:.2f}")
        
        self._log_resource_state()

    def _log_resource_state(self):
        """Log and store the current state of all resources"""
        state = {}
        total_capacity = 0
        total_available = 0
        
        for der in self.ders.values():
            state[der.id] = {
                'capacity': der.capacity,
                'available': der.available_capacity,
                'utilized': der.capacity - der.available_capacity
            }
            total_capacity += der.capacity
            total_available += der.available_capacity
        
        utilization = (total_capacity - total_available) / total_capacity if total_capacity > 0 else 0
        state['total_utilization'] = utilization
        
        self.performance_metrics['resource_state_history'].append(state)
        logging.info(f"Current system utilization: {utilization:.2%}")

    async def _execute_event(self, event: Event) -> bool:
        try:
            logging.info(f"Executing event {event.id} with duration {event.duration}ms")
            await asyncio.sleep(event.duration / 1000)
            return True
        except Exception as e:
            logging.error(f"Error executing event {event.id}: {e}")
            return False

    def _record_metrics(self, event: Event, success: bool, start_time: datetime):
        response_time = (datetime.now() - start_time).total_seconds()
        self.performance_metrics['response_times'].append(response_time)
        self.performance_metrics['success_rates'][event.priority].append(success)
        
        # Calculate current utilization
        total_capacity = sum(der.capacity for der in self.ders.values())
        used_capacity = sum(der.capacity - der.available_capacity for der in self.ders.values())
        utilization = used_capacity / total_capacity if total_capacity > 0 else 0
        self.performance_metrics['resource_utilization'].append(utilization)
        
        self.performance_metrics['processing_times'].append(response_time)
        self.performance_metrics['total_events_processed'] += 1
        
        logging.info(f"Event {event.id} metrics:")
        logging.info(f"  Response time: {response_time:.3f}s")
        logging.info(f"  Success: {success}")
        logging.info(f"  Resource utilization: {utilization:.2%}")