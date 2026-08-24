#!/usr/bin/env python3
"""server.py - the launch alias for the room server.

    python server.py serve --port 7133      ==  python room.py serve --port 7133
    python server.py init | say | state | claim | status | selftest

WHY THIS FILE EXISTS, stated plainly rather than resolved by silent choice:

This builder's commission named the file `server.py`. `CONTRACT.md` - the frozen interface the
other three builders are coding against - names it `room.py`, in §1 (the directory layout),
§1.1 (the frozen import graph: `room.py -> roomlog, status`), §6.1 (the launch story), §6.3
(the CLI a model uses from its own session), §8 (`test_room.py` imports `room`), §9 (the
builder split, and the B<->C seam), and inside a dozen remedy sentences that tell an operator
exactly what to type.

The contract wins on the name, because a remedy sentence naming a file that does not exist is
worse than no remedy at all, and because tripwires T1 and T2 read `room.py`'s source. The
commission wins on having an entry point under the name it asked for. So the server lives in
`room.py` and this launcher carries the commissioned name.

This mirrors, deliberately, how the sibling builder resolved the identical collision for the
agent (`room_agent.py --as <Lane>` vs the contract's `catcher.py --lane <Lane>`): shim, do not
fork. Two resolutions of the same class of conflict should not disagree.

Nothing else is here. There is no second implementation, no second set of laws, no state of
its own - this file forwards argv and returns room.main's exit code.
"""

import sys

import room

if __name__ == "__main__":
    sys.exit(room.main())
