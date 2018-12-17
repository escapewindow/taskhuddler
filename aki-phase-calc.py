#!/usr/bin/env python

import arrow
import asyncio
import json
import os
import pprint
import sys
from statistics import mean, median
from taskhuddler.aio import TaskGraph

def get_taskgraph():
    with open("/Users/asasaki/src/gecko/taskgraph-diff/json/x/mb-promote-firefox-partials.json") as fh:
        contents = json.load(fh)
    return contents

async def async_main():
    all_tasks = {
        'pre': {},
        'post': {},
    }
    status_str = ""
    os.environ['TC_CACHE_DIR'] = os.path.join(os.path.dirname(__file__), 'cache')
    graph = await TaskGraph(sys.argv[1])
    taskgraph = get_taskgraph()
    for task in graph.tasklist:
        started = arrow.get(task.started)
        resolved = arrow.get(task.resolved)
        phase = 'pre'
        if task.label in taskgraph:
            if 'mar-signing' in taskgraph[task.label].get("attributes", {}).get('required_signoffs', []):
                # print("{} requires signoffs".format(task.label))
                phase = 'post'
            else:
                # print("{} doesn't require signoffs".format(task.label))
                pass
        else:
            print("!!! {} not in taskgraph".format(task.label))
        all_tasks[phase].setdefault(task.kind, {})[task.taskid] = {
            'label': task.label,
            'started': started,
            'resolved': resolved,
            'duration': arrow.get(resolved.timestamp - started.timestamp),
        }
    for phase in ['pre', 'post']:
        print("\n\n*****\n*****phase {}\n*****".format(phase))
        phase_started = arrow.utcnow().timestamp
        phase_resolved = 0
        phase_durations = {}
        phase_ready = 0
        kind_order = {}
        for kind in sorted(all_tasks[phase].keys()):
            longest_duration = 0
            started = arrow.utcnow().timestamp
            resolved = 0
            durations = {}
            for taskid in all_tasks[phase][kind].keys():
                task = all_tasks[phase][kind][taskid]
                started = min(started, task['started'].timestamp)
                phase_started = min(started, phase_started)
                resolved = max(resolved, task['resolved'].timestamp)
                phase_resolved = max(resolved, phase_resolved)
                durations[task['label']] = task['duration'].timestamp
                phase_durations[task['label']] = task['duration'].timestamp
            if kind in ('partials', 'partials-signing', 'mar-signing'):
                phase_ready = max(phase_ready, resolved)
            kind_mean = mean(durations.values())
            kind_median = median(durations.values())
            kind_order["{}_{}".format(started, kind)] = {
                'kind': kind,
                'started': arrow.get(started).format(),
                'resolved': arrow.get(resolved).format(),
                'mean': kind_mean,
                'median': kind_median,
                'num_tasks': len(durations),
            }
        for i in sorted(kind_order.keys()):
            print("    Kind {} started {} resolved {} mean {} median {} num_tasks {}".format(
                kind_order[i]['kind'],
                kind_order[i]['started'],
                kind_order[i]['resolved'],
                kind_order[i]['mean'],
                kind_order[i]['median'],
                kind_order[i]['num_tasks'],
            ))
        phase_mean = mean(phase_durations.values())
        phase_median = median(phase_durations.values())
        phase_num = len(phase_durations)
        print("Phase {}: started {}, ready {}, resolved {}, ready time {}, overall {}, mean task time {}, median task time {}, num tasks {}".format(
            phase,
            arrow.get(phase_started).format(),
            arrow.get(phase_ready).format(),
            arrow.get(phase_resolved).format(),
            arrow.get(phase_ready - phase_started).format('HH:mm:ss'),
            arrow.get(phase_resolved - phase_started).format('HH:mm:ss'),
            phase_mean, phase_median, phase_num
        ))


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())

__name__ == '__main__' and main()
