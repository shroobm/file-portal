#!/usr/bin/env python3
"""room_agent.py - the launch alias for the lane agent.

    python room_agent.py --as Fable      ==  python catcher.py --lane Fable
    python room_agent.py --as Codex --once

WHY THIS FILE EXISTS, stated plainly rather than resolved by silent choice:

The commission for this builder named the agent `room_agent.py --as <Lane>`. `CONTRACT.md`
- which is the frozen interface every other builder is coding against - names it
`catcher.py --lane <Lane>`, in §1 (the directory layout), §1.1 (the frozen import graph), §1.3
(the single-writer table: `state/status-<lane>.json` is written ONLY by `catcher.py --lane
<Lane>`), §4.8, §6.1 (the launch story), and inside a dozen remedy sentences that tell an
operator exactly what to type.

The contract wins on the name, because the remedy sentences and the other three builders'
code all say `catcher.py`, and a remedy that names a file which does not exist is worse than
no remedy at all. The commission wins on the entry point, because it asked for one. So the
agent lives in `catcher.py` and this two-line launcher carries the commissioned name and the
commissioned `--as` spelling (which `catcher.py` also accepts as an alias for `--lane`).

Nothing else is here. There is no second implementation, no second set of laws, and no state
of its own - this file forwards argv and returns catcher.main's exit code.
"""

import sys

import catcher

if __name__ == "__main__":
    sys.exit(catcher.main())
