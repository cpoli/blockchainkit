"""Partial synchrony (Dwork, Lynch and Stockmeyer 1988): progress after an unknown GST.

Real networks are neither synchronous (known delay bound) nor fully
asynchronous (FLP applies). Partial synchrony assumes a bound Delta holds
after some unknown Global Stabilization Time (GST). Protocols stay safe
always, and make progress once a leader's view lasts long enough: doubling
the timeout each view guarantees that eventually it exceeds Delta.
"""

from blockchainkit._validation import integer
from blockchainkit.consensus.core.base import ViewChangeRun


def view_changes(
    gst: int, delta: int, base_timeout: int, *, growth: int = 2, max_views: int = 64
) -> ViewChangeRun:
    """Simulate leader views with growing timeouts until one makes progress.

    Before GST the adversary delays the leader's message past every timeout;
    from GST on it arrives after ``delta`` ticks. View v lasts
    ``base_timeout * growth**v`` and succeeds when it starts at or after GST
    and its timeout is at least ``delta``.

    Raises
    ------
    TimeoutError
        No view succeeded within ``max_views`` (for example, timeouts that
        never grow past delta).

    Examples
    --------
    >>> from blockchainkit.consensus import view_changes
    >>> view_changes(gst=10, delta=5, base_timeout=1).decided_view
    4
    """
    integer(gst, "gst")
    integer(delta, "delta", 1)
    integer(base_timeout, "base_timeout", 1)
    integer(growth, "growth", 1)
    integer(max_views, "max_views", 1)
    starts, timeouts, time = [], [], 0
    for view in range(max_views):
        timeout = base_timeout * growth**view
        starts.append(time)
        timeouts.append(timeout)
        if time >= gst and delta <= timeout:
            return ViewChangeRun(tuple(starts), tuple(timeouts), view, time + delta)
        time += timeout
    raise TimeoutError(f"no view made progress in {max_views} views")
