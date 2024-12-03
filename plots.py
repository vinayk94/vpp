import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the summary data
summary_1 = pd.read_csv("summary_1.csv")
summary_2 = pd.read_csv("summary_2.csv")

# Convert stringified dictionaries in the CSVs to actual dictionaries
summary_1["avg_response_time_by_priority"] = summary_1["avg_response_time_by_priority"].apply(eval)
summary_2["priority_success_rates"] = summary_2["priority_success_rates"].apply(eval)

# Extract response times into separate columns for Version 1
for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
    summary_1[f"response_time_{priority.lower()}"] = summary_1["avg_response_time_by_priority"].apply(lambda x: x.get(priority, 0))

# Fleet Utilization for Version 1 and Version 2
utilization_v1 = summary_1.groupby('scenario')['utilization'].mean()
utilization_v2 = summary_2.groupby('scenario')['fleet_utilization'].mean()

# Align the scenarios by using an outer join
aligned_utilization = pd.concat([utilization_v1, utilization_v2], axis=1, keys=['Version 1', 'Version 2']).fillna(0)

# Fleet Utilization Chart
fig, ax = plt.subplots(figsize=(10, 6))
aligned_utilization.plot(kind='bar', alpha=0.8, ax=ax)
ax.set_ylabel('Fleet Utilization (%)')
ax.set_title('Fleet Utilization Comparison by Scenario')
ax.legend(title='Version')
ax.set_xticks(range(len(aligned_utilization.index)))
ax.set_xticklabels(aligned_utilization.index, rotation=45)
for i, val in enumerate(aligned_utilization['Version 1']):
    ax.text(i - 0.2, val + 0.02, f"{val:.2f}", ha='center', fontsize=8)
for i, val in enumerate(aligned_utilization['Version 2']):
    ax.text(i + 0.2, val + 0.02, f"{val:.2f}", ha='center', fontsize=8)
plt.tight_layout()
plt.savefig("fleet_utilization_comparison_enhanced.png")

# Success Rates for Version 2
summary_2['success_rate'] = summary_2['successful_events'] / summary_2['total_events']
fig, ax = plt.subplots(figsize=(10, 6))
success_rates = summary_2.groupby('scenario')['success_rate'].mean()
success_rates.plot(kind='bar', color='skyblue', alpha=0.8, ax=ax)
ax.axhline(success_rates.mean(), color='red', linestyle='--', label=f"Average: {success_rates.mean():.2%}")
ax.set_ylabel('Success Rate (%)')
ax.set_title('Event Success Rates in Version 2')
ax.legend()
ax.set_xticks(range(len(success_rates.index)))
ax.set_xticklabels(success_rates.index, rotation=45)
plt.tight_layout()
plt.savefig("event_success_rates_enhanced.png")

# Response Times by Priority (Version 1)
priority_columns = [f"response_time_{priority.lower()}" for priority in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]]
fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey=True)
axes = axes.flatten()
for idx, column in enumerate(priority_columns):
    summary_1[column].plot(kind='bar', ax=axes[idx], alpha=0.8, title=column.replace("response_time_", "").capitalize())
    axes[idx].set_ylabel('Average Response Time (s)')
    axes[idx].set_xticks(range(len(summary_1['scenario'])))
    axes[idx].set_xticklabels(summary_1['scenario'], rotation=45)
plt.suptitle('Response Time by Priority in Version 1')
plt.tight_layout()
plt.savefig("response_time_by_priority_v1_enhanced.png")

# Display key insights
print("Aligned Fleet Utilization:")
print(aligned_utilization)

print("\nSuccess Rates (Version 2):")
print(success_rates)

print("\nResponse Times by Priority (Version 1):")
print(summary_1[priority_columns].mean())
