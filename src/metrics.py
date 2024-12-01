# src/metrics.py

import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from .vpp import Event, EventPriority

class VPPMetricsCollector:
    def __init__(self):
        self.metrics_store = {
            'response_times': [],            # List of response times for each event
            'success_rates': {},             # Success rate by priority
            'resource_utilization': [],      # Resource utilization over time
            'priority_satisfaction': {},      # How well priorities were respected
            'event_latency': {},             # Event processing latency by type
            'resource_contention': [],       # Times when resources were contested
            'failed_events': [],             # Events that couldn't be processed
            'completed_events': []           # Successfully processed events
        }

    async def collect_scenario_metrics(self, events: List[Event]) -> Dict:
        """Collect comprehensive metrics for a test scenario"""
        metrics = {
            'event_processing': self._calculate_event_metrics(events),
            'resource_usage': self._calculate_resource_metrics(),
            'system_performance': self._calculate_system_metrics(events)
        }
        
        self._update_metrics_store(metrics)
        return metrics

    def _calculate_response_time(self, event: Event) -> float:
        """Calculate response time for a single event"""
        processing_time = (datetime.now() - event.timestamp).total_seconds()
        self.metrics_store['response_times'].append(processing_time)
        return processing_time

    def _calculate_success_rate(self, events: List[Event]) -> float:
        """Calculate success rate for a set of events"""
        completed = len([e for e in events if e.id in [ce.id for ce in self.metrics_store['completed_events']]])
        total = len(events)
        success_rate = completed / max(1, total)
        
        # Store by priority
        if events and events[0].priority:
            self.metrics_store['success_rates'][events[0].priority.name] = success_rate
        
        return success_rate

    def _calculate_contention_rate(self) -> float:
        """Calculate resource contention rate"""
        if not self.metrics_store['resource_utilization']:
            return 0.0
            
        # Consider contention when utilization is above 80%
        contention_points = len([u for u in self.metrics_store['resource_utilization'] if u > 0.8])
        return contention_points / len(self.metrics_store['resource_utilization'])

    def _calculate_resource_efficiency(self) -> float:
        """Calculate resource utilization efficiency"""
        if not self.metrics_store['resource_utilization']:
            return 0.0
            
        # Calculate weighted average giving more weight to recent utilization
        weights = np.linspace(0.5, 1.0, len(self.metrics_store['resource_utilization']))
        weighted_util = np.average(
            self.metrics_store['resource_utilization'],
            weights=weights
        )
        return weighted_util

    def _calculate_priority_satisfaction(self, events: List[Event]) -> Dict:
        """Calculate how well priority order was maintained"""
        priority_metrics = {}
        for priority in EventPriority:
            priority_events = [e for e in events if e.priority == priority]
            if priority_events:
                # Calculate average response time relative to deadline
                avg_deadline_ratio = np.mean([
                    self._calculate_response_time(e) / max(1, (e.deadline - e.timestamp).total_seconds())
                    for e in priority_events
                ])
                priority_metrics[priority.name] = min(1.0, 1.0 / max(0.001, avg_deadline_ratio))
                
        self.metrics_store['priority_satisfaction'].update(priority_metrics)
        return priority_metrics

    def _calculate_stability_score(self) -> float:
        """Calculate overall system stability score"""
        if not self.metrics_store['response_times']:
            return 1.0
            
        # Factors affecting stability
        response_time_consistency = 1.0 - np.std(self.metrics_store['response_times']) / max(1, np.mean(self.metrics_store['response_times']))
        resource_stability = 1.0 - np.std(self.metrics_store['resource_utilization']) if self.metrics_store['resource_utilization'] else 1.0
        success_rate = np.mean(list(self.metrics_store['success_rates'].values())) if self.metrics_store['success_rates'] else 1.0
        
        # Weighted stability score
        stability = (
            0.4 * response_time_consistency +
            0.3 * resource_stability +
            0.3 * success_rate
        )
        
        return max(0.0, min(1.0, stability))

    def _calculate_event_metrics(self, events: List[Event]) -> Dict:
        """Calculate event-specific metrics"""
        metrics = {
            'total_events': len(events),
            'events_by_priority': {},
            'avg_response_time': {},
            'success_rate': {},
        }
        
        for priority in EventPriority:
            priority_events = [e for e in events if e.priority == priority]
            if priority_events:
                metrics['events_by_priority'][priority.name] = len(priority_events)
                metrics['avg_response_time'][priority.name] = np.mean(
                    [self._calculate_response_time(e) for e in priority_events]
                )
                metrics['success_rate'][priority.name] = self._calculate_success_rate(priority_events)
        
        return metrics

    def _calculate_resource_metrics(self) -> Dict:
        """Calculate resource utilization metrics"""
        return {
            'avg_utilization': np.mean(self.metrics_store['resource_utilization']) if self.metrics_store['resource_utilization'] else 0.0,
            'peak_utilization': np.max(self.metrics_store['resource_utilization']) if self.metrics_store['resource_utilization'] else 0.0,
            'contention_rate': self._calculate_contention_rate(),
            'resource_efficiency': self._calculate_resource_efficiency()
        }

    def _calculate_system_metrics(self, events: List[Event]) -> Dict:
        """Calculate overall system performance metrics"""
        if not events:
            return {
                'throughput': 0.0,
                'avg_latency': 0.0,
                'priority_satisfaction': {},
                'system_stability': 1.0
            }
            
        return {
            'throughput': len(events) / max(1, (max(e.timestamp for e in events) - 
                                              min(e.timestamp for e in events)).total_seconds()),
            'avg_latency': np.mean(list(self.metrics_store['event_latency'].values())) if self.metrics_store['event_latency'] else 0.0,
            'priority_satisfaction': self._calculate_priority_satisfaction(events),
            'system_stability': self._calculate_stability_score()
        }

    def _update_metrics_store(self, metrics: Dict):
        """Update internal metrics store with new metrics"""
        for category, values in metrics.items():
            if isinstance(values, dict):
                for metric, value in values.items():
                    if metric not in self.metrics_store:
                        self.metrics_store[metric] = []
                    if isinstance(value, (int, float)):
                        self.metrics_store[metric].append(value)
            elif isinstance(values, (int, float)):
                if category not in self.metrics_store:
                    self.metrics_store[category] = []
                self.metrics_store[category].append(values)

    def generate_report(self) -> pd.DataFrame:
        """Generate a comprehensive performance report"""
        report_data = {
            'metric': [],
            'value': [],
            'std_dev': []
        }
        
        for metric, values in self.metrics_store.items():
            if isinstance(values, list) and values:
                report_data['metric'].append(metric)
                report_data['value'].append(np.mean(values))
                report_data['std_dev'].append(np.std(values))
            elif isinstance(values, dict) and values:
                for sub_metric, sub_values in values.items():
                    report_data['metric'].append(f"{metric}_{sub_metric}")
                    report_data['value'].append(np.mean(sub_values) if isinstance(sub_values, list) else sub_values)
                    report_data['std_dev'].append(np.std(sub_values) if isinstance(sub_values, list) else 0)
                    
        return pd.DataFrame(report_data)