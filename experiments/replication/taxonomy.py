"""The paper's structure as the replication uses it (docs/paper-content.md §5).

- 23 Figure-5 sub-categories, each in one of 7 categories (paper text pp.2-4).
- 5 Figure-11 virtualization sub-issues, folded into Figure 5's two virtualization rows
  the way the paper's pies did (Isolation 7 + Hypervisor 5 = Figure 6's 12%).
- The 2012 values used for comparison: Figures 6 and 8 (exact), 5, 7 and 11 (approximate).
"""

from __future__ import annotations

CATEGORIES = ["legal-issues", "compliance", "governance", "virtualization", "data-security", "interfaces",
              "network-security"]

# sub-category -> (category, source)
SUBCATEGORIES: dict[str, tuple[str, str]] = {
    "Transfer security": ("network-security", "p.2, 1(a)"),
    "Firewalling": ("network-security", "p.2, 1(b)"),
    "Security configuration": ("network-security", "p.2, 1(c)"),
    "API": ("interfaces", "p.2, 2(a)"),
    "Administrative interface": ("interfaces", "p.2, 2(b)"),
    "User interface": ("interfaces", "p.2, 2(c)"),
    "Authentication": ("interfaces", "p.2, 2(d)"),
    "Cryptography": ("data-security", "p.3, 3(a)"),
    "Redundancy": ("data-security", "p.3, 3(b)"),
    "Disposal": ("data-security", "p.3, 3(c)"),
    "Isolation": ("virtualization", "p.3, 4(a) (+ 4(c)-(e) folded, see Fig 5)"),
    "Hypervisor vulnerabilities": ("virtualization", "p.3, 4(b)"),
    "Data control": ("governance", "p.3, 5(a)"),
    "Security control": ("governance", "p.3, 5(b)"),
    "Lock-in": ("governance", "p.3, 5(c)"),
    "SLA": ("compliance", "p.3, 6(a)"),
    "Loss of service": ("compliance", "p.3, 6(b)"),
    "Audit": ("compliance", "p.3, 6(c)"),
    "Service conformity": ("compliance", "pp.3-4, 6(d)"),
    "Data location": ("legal-issues", "p.4, 7(a)"),
    "e-Discovery": ("legal-issues", "p.4, 7(b)"),
    "Provider privilege": ("legal-issues", "p.4, 7(c)"),
    "Legislation": ("legal-issues", "p.4, 7(d)"),
}

AXES = ["hypervisor-vulnerabilities", "cross-vm-attacks", "isolation", "data-leakage", "vm-identification"]
FOLD = {  # Figure-11 sub-issue -> Figure-5 row
    "hypervisor-vulnerabilities": "Hypervisor vulnerabilities",
    "isolation": "Isolation",
    "cross-vm-attacks": "Isolation",
    "data-leakage": "Isolation",
    "vm-identification": "Isolation",
}

# Figures 6 & 8: exact, each sums to 100.
PAPER_2012_CATEGORIES = {
    "legal-issues": (24, 27), "compliance": (22, 29), "governance": (17, 14), "virtualization": (12, 3),
    "data-security": (10, 9), "interfaces": (8, 10), "network-security": (7, 8),
}
# Figures 5 & 7: approximate (read from the pies).
PAPER_2012_SUBCATEGORIES = {
    "Legislation": (10, 12), "Service conformity": (9, 12), "Data control": (9, 8), "Isolation": (7, 1),
    "Audit": (6, 8), "Provider privilege": (6, 7), "Cryptography": (6, 4), "Security control": (5, 3),
    "Transfer security": (5, 5), "SLA": (5, 7), "Data location": (5, 4), "Hypervisor vulnerabilities": (5, 2),
    "e-Discovery": (4, 4), "Lock-in": (3, 3), "Authentication": (3, 3), "Redundancy": (2, 3), "Disposal": (2, 2),
    "User interface": (2, 3), "Administrative interface": (2, 2), "API": (2, 2), "Firewalling": (2, 2),
    "Security configuration": (1, 1), "Loss of service": (1, 1),
}
# Figure 11: approximate citation counts (measured at 900 dpi).
PAPER_2012_AXES = {
    "hypervisor-vulnerabilities": (21, 8), "cross-vm-attacks": (21, 1), "isolation": (20, 3),
    "data-leakage": (16, 5), "vm-identification": (15, 2),
}


def category_of(subcategory: str) -> str:
    return SUBCATEGORIES[subcategory][0]
