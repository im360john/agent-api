#!/usr/bin/env python3
"""Fix the slack_treez_agent.py file by removing old code"""

with open('/home/john/repos/agent-api/agents/slack_treez_agent.py', 'r') as f:
    lines = f.readlines()

# Find the line with 'results["urls"].append(base_url)'
start_idx = None
for i, line in enumerate(lines):
    if 'results["urls"].append(base_url)' in line:
        start_idx = i
        break

# Find the line with 'except Exception as e:' after line 790
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if 'except Exception as e:' in lines[i] and 'Failed to crawl and update knowledge' in lines[i+1]:
        end_idx = i
        break

print(f'Found start at line {start_idx+1}: {lines[start_idx].strip()}')
print(f'Found end at line {end_idx+1}: {lines[end_idx].strip()}')

# Remove the old code
new_lines = lines[:start_idx+1] + ['\n'] + lines[end_idx:]

# Write back
with open('/home/john/repos/agent-api/agents/slack_treez_agent.py', 'w') as f:
    f.writelines(new_lines)

print(f'Removed {end_idx - start_idx - 1} lines of old code')