"""A long-running tenant workload that does nothing, used by tenant-b and tenant-c.

It exits promptly on SIGTERM so `docker stop` doesn't wait for the kill timeout.
"""

import signal
import sys
import time

signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
print(f"{sys.argv[1] if len(sys.argv) > 1 else 'tenant'} idle", flush=True)
while True:
    time.sleep(3600)
