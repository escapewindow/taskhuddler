"""Common utilities for understanding tasks."""
from collections import namedtuple
from contextlib import ExitStack, contextmanager

import s3fs


@contextmanager
def open_wrapper(filename, *args, **kwargs):
    """Allow use of local or s3 files."""
    with ExitStack() as stack:
        if filename.startswith('s3://'):
            fs = s3fs.S3FileSystem()
            f = stack.enter_context(fs.open(filename, *args, **kwargs))
        else:
            f = stack.enter_context(open(filename, *args, **kwargs))
        yield f


Range = namedtuple('Range', ['start', 'end'])


def allen_overlap(r1, r2):
    """Return True if the two datetimes overlap or are contained."""
    return (r1.start < r2.start) and ((r1.end > r2.start) and (r1.end < r2.end))
    # return max((min(r1.end, r2.end) - max(r1.start, r2.start)).days, -1) + 1


def allen_contains(r1, r2):
    """Is one date contained within the other."""
    return (r1.start < r2.start and r1.end > r2.end) or (r2.start < r1.start and r2.end > r1.end)


def should_merge(r1, r2):
    """Return True if these two datetimes be merged."""
    return allen_overlap(r1, r2) or allen_overlap(r2, r1) or allen_contains(r1, r2)


def merge_dates(r1, r2):
    """Merge two start/end tuples if they overlap."""
    if should_merge(r1, r2):
        return Range(start=min(r1.start, r2.start), end=max(r1.end, r2.end))
    else:
        raise ValueError('Dates do not overlap')


def merge_date_list(dt_list):
    """Merge two lists of datetime objects.

    Given date ranges like this:
       |------|
            |------|
    |---|
                         |------|

    Produce a list of date ranges:
    |--------------|     |------|
    """
    result = list()
    while(dt_list):
        current = dt_list.pop()
        overlaps = [dt for dt in dt_list if should_merge(current, dt)]
        if not overlaps:
            result.append(current)
            continue
        for dt in overlaps:
            current = merge_dates(current, dt)
            dt_list.remove(dt)
        dt_list.append(current)

    return sorted(result)
