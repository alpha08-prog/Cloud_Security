"""Keyword rules of the replication (docs/replication.md §3): term syntax, golden sentences per
sub-category and virtualization sub-issue, the type rules and the solution window.

Written before the freeze; a failing golden sentence after a lexicon edit means the edit changed
what the rules count, which the protocol changelog must then say.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from replication import classify, corpus, lexicon, taxonomy  # noqa: E402
from replication.classify import TermSet  # noqa: E402
from replication.classify import classify as run  # noqa: E402

# ------------------------------------------------------------------------------ term syntax


@pytest.mark.parametrize("term,text,hit", [
    ("API", "a REST API for tenants", True),
    ("API", "rapid provisioning", False),
    ("API", "the api is", False),                 # ALL-CAPS terms are case-sensitive
    ("audit*", "public auditing scheme", True),
    ("audit*", "an auditory signal", True),       # the stem matches; Audit masks "auditory" itself
    ("lock-in", "vendor lock in", True),
    ("lock-in", "lockin", True),
    ("data location", "data-location control", True),
    ("data location", "data locations", True),    # plural on the last word
    ("encrypt*", "re-encryption keys", True),
    ("TEE", "tee", False),
    ("re:\\bpods?\\b", "PODS", True),
])
def test_term_syntax(term, text, hit):
    assert TermSet([term]).search(text) is hit


def test_mask_keeps_offsets():
    ts = TermSet(["isolation forest"])
    text = "an isolation forest detector"
    masked = ts.mask(text)
    assert len(masked) == len(text) and "isolation" not in masked


def test_rebuild_abstract_orders_words_by_position():
    assert corpus.rebuild_abstract({"cloud": [1], "The": [0], "leaks": [2]}) == "The cloud leaks"
    assert corpus.rebuild_abstract(None) == ""


def test_sentence_split_handles_missing_space():
    s = classify.sentences("T", "First part (CCDC).The second part. Third e.g. lower")
    assert s == ["T", "First part (CCDC).", "The second part.", "Third e.g. lower"]


# ------------------------------------------------------------------------------ golden sentences

TITLE = "Cloud security"
LEAD = "Cloud computing raises security concerns for tenants. "


def subs(sentence: str) -> set[str]:
    return set(run("W0", TITLE, LEAD + sentence).concern)


def axes(sentence: str) -> set[str]:
    return set(run("W0", TITLE, LEAD + sentence).axes_concern)


GOLDEN_SUB = {
    "Legislation": "Compliance with the GDPR and other privacy laws is required.",
    "Data location": "The data residency of records across jurisdictions matters.",
    "e-Discovery": "Digital forensics in the cloud needs a chain of custody.",
    "Provider privilege": "A malicious insider at the provider can read the data.",
    "Service conformity": "We map controls to ISO 27001 certification.",
    "SLA": "The service level agreement defines penalties.",
    "Loss of service": "An outage of the provider stops business continuity.",
    "Audit": "A third party auditor checks the stored files.",
    "Data control": "Users lose control over their data once it is outsourced.",
    "Security control": "A risk assessment of the deployment is performed.",
    "Lock-in": "Vendor lock-in limits portability between providers.",
    "Cryptography": "Files are encrypted with attribute-based encryption.",
    "Redundancy": "Erasure coding keeps backups of the data.",
    "Disposal": "Assured deletion of the data is required at the end.",
    "Transfer security": "Data in transit is protected with TLS.",
    "Firewalling": "A firewall and an intrusion detection system filter packets.",
    "Security configuration": "Misconfiguration of storage buckets exposes data.",
    "API": "The provider exposes an insecure API to tenants.",
    "Administrative interface": "The management console of the provider is a target.",
    "User interface": "Phishing pages imitate the login web portal of the provider.",
    "Authentication": "Multi-factor authentication protects accounts.",
}


@pytest.mark.parametrize("sub,sentence", sorted(GOLDEN_SUB.items()))
def test_golden_subcategory(sub, sentence):
    assert sub in subs(sentence)


def test_every_lexicon_subcategory_has_a_golden_sentence():
    assert set(lexicon.SUBCATEGORIES) == set(GOLDEN_SUB)
    folded = set(taxonomy.FOLD.values())
    assert set(lexicon.SUBCATEGORIES) | folded == set(taxonomy.SUBCATEGORIES)


GOLDEN_AXIS = {
    "hypervisor-vulnerabilities": "A compromised hypervisor exposes every guest.",
    "isolation": "Weak tenant isolation lets one container escape to the host.",
    "cross-vm-attacks": "A cross-VM cache side channel recovers keys from a co-resident VM.",
    "data-leakage": "Memory deduplication leaks data between tenants.",
    "vm-identification": "Remote attestation of each virtual machine proves what runs.",
}


@pytest.mark.parametrize("axis,sentence", sorted(GOLDEN_AXIS.items()))
def test_golden_axis_and_fold(axis, sentence):
    r = run("W0", TITLE, LEAD + sentence)
    assert axis in r.axes_concern
    assert taxonomy.FOLD[axis] in r.concern
    assert "virtualization" in r.categories()


@pytest.mark.parametrize("sentence", [
    "We use an isolation forest to find anomalies in the logs.",             # false friend
    "The scheme runs on the Java virtual machine.",                         # JVM is not a VM
    "A memory leak in the parser was fixed.",                               # not data leakage
    "Our system is deployed on KVM virtual machines.",                      # platform, not a flaw
    "Side-channel attacks threaten smart-card implementations.",            # no VM context
    "The POD scheme trains the model privately.",                           # scheme name, not a pod
])
def test_no_virtualization_false_friends(sentence):
    assert not axes(sentence)


def test_hypervisor_needs_a_threat_word():
    assert "hypervisor-vulnerabilities" not in axes("The prototype runs on the Xen hypervisor.")
    assert "hypervisor-vulnerabilities" in axes("Vulnerabilities in the Xen hypervisor let guests attack it.")


# ------------------------------------------------------------------------------ relevance gate


def test_gate_needs_cloud_security_and_a_joint_sentence():
    ok = run("W0", "Encryption for cloud storage", "Users encrypt files before upload. Keys stay local.")
    assert ok.in_scope
    no_cloud = run("W0", "Encryption for disks", "Users encrypt files with keys. The scheme is secure.")
    assert not no_cloud.in_scope
    apart = run("W0", "A smart lock",
                "The lock uses encryption and protects the house. Data is sent to the cloud. "
                "A cloud dashboard shows the state.")
    assert not apart.gate_joint and not apart.in_scope


# ------------------------------------------------------------------------------ type rules


@pytest.mark.parametrize("abstract,kind", [
    ("Cloud data needs protection. In this paper, we propose a scheme that encrypts data.", "solution"),
    ("Cloud data needs protection. A novel encryption scheme is proposed for cloud storage.", "solution"),
    ("This survey reviews encryption schemes for cloud storage. We compare them.", "survey"),
    ("Cloud storage is used widely. A scheme was proposed by Yuan et al. for cloud audits. "
     "We show that the scheme is insecure against a malicious cloud.", "concern"),
    ("Cloud tenants share caches. We present a new attack that exploits the cache to recover keys.", "concern"),
    ("Cloud tenants share caches. We propose a defense that detects and mitigates cache attacks.", "solution"),
    ("Cloud providers store data. Our implementation of the encryption is measured.", "concern"),
    ("Cloud providers store data. The study shows the need for deploying stronger isolation techniques.",
     "concern"),
])
def test_type_rules(abstract, kind):
    assert run("W0", "Cloud storage security", abstract).kind == kind


def test_state_of_the_art_in_the_lead_is_not_a_survey():
    r = run("W0", "vTPM protection for cloud",
            "Current state-of-the-art vTPM implementations in the cloud are weak. "
            "In this paper, we propose a system that protects vTPMs with SGX enclaves.")
    assert r.kind == "solution"


# ------------------------------------------------------------------------------ solution window


def test_problem_statement_subissue_is_not_a_solution():
    r = run("W0", "A perimeter for IaaS",
            "IaaS suffers from hypervisor hijacking and account hijacking. "
            "To secure IaaS, this article proposes a software-defined perimeter as a solution. "
            "Only authenticated clients pass the firewall.")
    assert r.kind == "solution"
    assert "hypervisor-vulnerabilities" in r.axes_concern
    assert "hypervisor-vulnerabilities" not in r.axes_solution
    assert "Hypervisor vulnerabilities" not in r.solution
    assert {"Authentication", "Firewalling"} <= set(r.solution)
    assert "Hypervisor vulnerabilities" in r.broadcast_solution  # rule A, RB2


def test_window_falls_back_to_all_hits():
    r = run("W0", "A new approach",
            "Cloud storage leaks sensitive data through weak encryption. We propose a method to fix this.")
    assert r.kind == "solution" and r.solution == ["Cryptography"]


def test_classic_axes_skip_container_sentences():
    r = run("W0", "Isolation in the cloud",
            "Container escape breaks tenant isolation in the cloud. "
            "We propose a scheme that hardens Docker containers against escapes.")
    assert "isolation" in r.axes_concern and "isolation" not in r.classic_axes


# ------------------------------------------------------------------------------ CVE supplement


@pytest.mark.parametrize("description,expected", [
    ("An issue was discovered in Xen allowing guest OS users to gain host OS privileges.",
     ["isolation", "virtualization-layer"]),
    ("KSM does not prevent a write-timing side channel, which allows guest OS users to defeat ASLR on "
     "other guest OS instances.", ["cross-vm-attacks"]),
    ("Windows Hyper-V Information Disclosure Vulnerability", ["data-leakage", "virtualization-layer"]),
    ("manual.php in Marcus S. Xenakis Unix Manual allows remote code execution.", []),        # not Xen
    ("A timing side channel in the RSA code allows remote attackers to recover keys.", []),    # no VM context
    ("A memory leak in the guest user portal allows a denial of service.", []),                # masked
    ("A broken access control flaw allows any tenant to read another tenant's data.", []),     # SaaS, not VMs
])
def test_cve_axes(description, expected):
    assert classify.classify_cve(description) == expected
