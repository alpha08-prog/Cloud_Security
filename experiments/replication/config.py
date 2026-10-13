"""Fixed parameters of the replication (pre-registered in docs/replication.md).

Changing anything here after the corresponding step has run must be logged in the
protocol changelog first.
"""

from __future__ import annotations

from isolab import util

ROOT = util.REPO / "replication"
CORPUS = ROOT / "corpus"
NVD = ROOT / "nvd"
SAMPLES = ROOT / "samples"
LABELS = ROOT / "labels"
CACHE = ROOT / "cache"            # raw API pages, git-ignored, makes fetches resumable
FREEZE = ROOT / "freeze.json"
RUNS = util.RUNS / "replication"   # generated outputs (git-ignored)

# ---------------------------------------------------------------- corpus (OpenAlex)
OPENALEX = "https://api.openalex.org/works"
EXCLUDED_PHRASES = [
    "point cloud", "point clouds", "cloud cover", "cloud seeding", "cloud droplet", "cloud microphysics",
    "molecular cloud", "electron cloud", "word cloud", "tag cloud", "cloud forest", "food security",
    "energy security", "water security", "social security", "job security",
]
SEARCH = "cloud AND (security OR privacy) NOT (" + " OR ".join(f'"{p}"' for p in EXCLUDED_PHRASES) + ")"
TYPES = ["article", "conference-paper", "review", "book-chapter", "preprint", "report"]
PEER_REVIEWED = {"article", "conference-paper", "review"}
ERAS = {"2013-2017": 2013, "2018-2022": 2018, "2023-2026": 2023}   # era -> seed
SAMPLE_PER_ERA = 2500
PAGE_SIZE = 200
SELECT = ["id", "doi", "title", "publication_year", "type", "language", "primary_location", "abstract_inverted_index"]

MIN_WORDS, MAX_WORDS = 50, 600

# ---------------------------------------------------------------- samples
DEV_PER_ERA, DEV_SEED = 50, 7
TEST_SEED = 11
TEST_STRATA = {  # era -> (A: in scope + virtualization, B: in scope other, C: gate failed)
    "2013-2017": (9, 19, 6),
    "2018-2022": (9, 18, 6),
    "2023-2026": (9, 18, 6),
}
TEST_REPEATS = 10

# ---------------------------------------------------------------- analysis
BOOTSTRAP_B = 2000
BOOTSTRAP_SEED = 2012
GATE = {"macro_f1": 0.70, "virtualization_f1": 0.70, "mean_kappa": 0.60, "type_kappa": 0.60}

# ---------------------------------------------------------------- CVE supplement (NVD)
NVD_API = "https://services.nvd.nist.gov/rest/json/cves/2.0"
NVD_SLEEP_S = 6.5
NVD_PRODUCT_TERMS = ["hypervisor", "hypervisors", "Xen", "KVM", "QEMU", "ESXi", "Hyper-V", "VirtualBox", "bhyve",
                     "Firecracker", "runc", "containerd", "CRI-O", "LXC", "gVisor", "Kata Containers", "Docker"]
NVD_PHRASES = ["virtual machine escape", "VM escape", "guest-to-host", "container escape", "guest OS", "guest kernel",
               "side channel", "side-channel", "speculative execution", "transient execution", "cross-tenant",
               "co-resident", "another guest"]
NVD_FIRST_YEAR = 2008
