import numpy as np
from typing import List, Dict
from .vpp import Event, DER, DERState

class VPPMetricsCollector:
    def __init__(self, ders: Dict[str, DER]):
        self.ders = ders
        self.metrics_store = {
            "response_times": [],
            "resource_utilization": [],
            "failed_events": 0,  # Total count of failed events
            "successful_events": [],  # List of successful event IDs
            "depleted_ders": [],
            "offline_ders": [],
            "priority_success_rates": {},
            "fleet_metrics": []
        }

    def collect_event_metrics(self, events: List[Event], completed_event_ids: List[str]):
        """Collect metrics based on event outcomes."""
        total_events = len(events)
        successful_events = [e.id for e in events if e.id in completed_event_ids]
        failed_events = total_events - len(successful_events)

        # Increment failed events count
        self.metrics_store["failed_events"] += failed_events
        # Add successful event IDs
        self.metrics_store["successful_events"].extend(successful_events)

        # Success rate by priority
        priorities = set(e.priority for e in events)
        for priority in priorities:
            priority_events = [e for e in events if e.priority == priority]
            success_count = len([e for e in priority_events if e.id in completed_event_ids])
            self.metrics_store["priority_success_rates"][priority] = success_count / len(priority_events) if priority_events else 0

        return {
            "total_events": total_events,
            "successful_events": len(successful_events),
            "failed_events": failed_events,
            "priority_success_rates": self.metrics_store["priority_success_rates"]
        }

    def collect_der_metrics(self):
        """Collect metrics for DER states."""
        total_ders = len(self.ders)
        depleted_ders = len([d for d in self.ders.values() if d.state == DERState.DEPLETED])
        offline_ders = len([d for d in self.ders.values() if d.state == DERState.OFFLINE])
        available_ders = total_ders - depleted_ders - offline_ders

        utilization = np.mean(
            [d.capacity - d.available_capacity for d in self.ders.values() if d.state == DERState.AVAILABLE]
        ) / max(1, np.mean([d.capacity for d in self.ders.values()]))

        self.metrics_store["depleted_ders"].append(depleted_ders)
        self.metrics_store["offline_ders"].append(offline_ders)
        self.metrics_store["resource_utilization"].append(utilization)

        return {
            "total_ders": total_ders,
            "available_ders": available_ders,
            "depleted_ders": depleted_ders,
            "offline_ders": offline_ders,
            "resource_utilization": utilization
        }

    def collect_fleet_metrics(self):
        """Collect fleet-level metrics."""
        total_capacity = sum(der.capacity for der in self.ders.values())
        total_available = sum(der.available_capacity for der in self.ders.values() if der.state != DERState.OFFLINE)
        utilization = total_available / total_capacity if total_capacity > 0 else 0

        fleet_metrics = {
            "total_fleet_capacity": total_capacity,
            "total_available_capacity": total_available,
            "fleet_utilization": utilization,
        }

        self.metrics_store["fleet_metrics"].append(fleet_metrics)
        return fleet_metrics

    def generate_report(self) -> Dict:
        """Generate a comprehensive performance report."""
        return {
            "response_time_mean": np.mean(self.metrics_store["response_times"]) if self.metrics_store["response_times"] else 0,
            "resource_utilization_mean": np.mean(self.metrics_store["resource_utilization"]),
            "total_failed_events": self.metrics_store["failed_events"],
            "total_successful_events": len(self.metrics_store["successful_events"]),
            "average_depleted_ders": np.mean(self.metrics_store["depleted_ders"]) if self.metrics_store["depleted_ders"] else 0,
            "average_offline_ders": np.mean(self.metrics_store["offline_ders"]) if self.metrics_store["offline_ders"] else 0,
            "priority_success_rates": self.metrics_store["priority_success_rates"],
            "fleet_metrics_summary": {
                "fleet_utilization_mean": np.mean([f["fleet_utilization"] for f in self.metrics_store["fleet_metrics"]]) if self.metrics_store["fleet_metrics"] else 0,
                "total_fleet_capacity": self.metrics_store["fleet_metrics"][-1]["total_fleet_capacity"] if self.metrics_store["fleet_metrics"] else 0,
                "total_available_capacity": self.metrics_store["fleet_metrics"][-1]["total_available_capacity"] if self.metrics_store["fleet_metrics"] else 0,
            }
        }
