"""Keyword rules for the replication: data only (the logic is in classify.py).

Both files are hashed into replication/freeze.json before the test set is drawn
(docs/replication.md §3). Any later change must be logged in the protocol changelog.

Term syntax (compiled by classify.compile_term):
  "encrypt*"        word stem: encrypt, encrypted, encryption, ...
  "data location"   spaces match spaces or hyphens; a plural is allowed on the last word
  "lock-in"         hyphen optional: lock-in, lock in, lockin
  "SLA"             ALL-CAPS terms are case-sensitive (API, IDS, SLA, TEE, ...)
  "re:<regex>"      raw regular expression (case-insensitive)

Per sub-category / axis:
  terms   count anywhere in the title or abstract
  virt    count only if a virtualization-context term is in the same sentence
  net     count only if a network-context term is in the same sentence
  threat  count only if a threat term (vulnerability, attack, compromise, ...) is in the same sentence
  exclude spans masked before matching (false friends)
"""

# ---------------------------------------------------------------------------- global masks
GLOBAL_EXCLUDE = [
    "point cloud", "cloud cover", "cloud seeding", "cloud droplet", "word cloud", "tag cloud", "cloud forest",
    "food security", "energy security", "water security", "social security", "job security",
    "isolation forest", "isolation level", "java virtual machine", "JVM", "EVM", "ethereum virtual machine",
    "power law", "moore's law", "memory leak", "memory leaks", "memory leakage",
]

# ---------------------------------------------------------------------------- context terms
VIRT_CONTEXT = [
    "VM", "VMs", "virtual machine*", "hypervisor*", "VMM", "guest*", "host os", "host kernel", "tenant*",
    "multi-tenan*", "multitenan*", "container*", "Docker", "Kubernetes", "co-resid*", "co-locat*", "colocat*",
    "shared hardware",
    "shared cache*", "shared memory", "shared host*", "serverless", "virtuali*", "virtualis*", "cloud instance*",
    "IaaS", "enclave*", "TEE", "SGX",
]
NET_CONTEXT = ["network*", "traffic", "packet*", "flow*", "intrusion*", "DDoS", "DoS", "botnet*", "malware"]
# A hypervisor that is merely the platform is not a hypervisor *vulnerability*: these words must be near.
THREAT_CONTEXT = ["vulnerab*", "attack*", "exploit*", "flaw*", "bug*", "compromis*", "hijack*", "malicious", "threat*",
                  "escape*", "untrusted", "harden*", "TCB", "trusted computing base", "attack surface", "rootkit*",
                  "malware", "loophole*", "intrusion*", "risk*", "CVE*"]

# ---------------------------------------------------------------------------- relevance gate
CLOUD_TERMS = ["cloud*", "IaaS", "PaaS", "SaaS", "multi-cloud", "multicloud", "fog computing", "fog node*",
               "edge-cloud", "data cent*", "datacent*", "virtual machine*", "serverless"]
SECURITY_TERMS = ["secur*", "privacy", "private data", "confidential*", "attack*", "threat*", "vulnerab*",
                  "malicious", "adversar*", "complian*", "trust*", "intrusion*", "encrypt*", "authenticat*",
                  "access control", "forensic*", "integrity", "risk*", "audit*", "protect*", "GDPR", "HIPAA",
                  "regulat*", "legal", "law*", "jurisdiction*", "isolation", "leak*", "breach*", "DDoS",
                  "anomal*", "insider*", "sovereignty"]

# ---------------------------------------------------------------------------- 23 Figure-5 sub-categories
SUBCATEGORIES = {
    # ---- Legal issues
    "Legislation": {
        "terms": ["legislat*", "legal framework*", "legal issue*", "legal requirement*", "legal aspect*",
                  "legal challenge*", "regulation*", "regulatory", "GDPR", "HIPAA", "CCPA", "data protection law*",
                  "data protection act", "data protection regulation*", "privacy law*", "cloud act", "patriot act",
                  "law*", "statut*", "directive*"],
        "exclude": ["law enforcement", "lawful interception", "lawful access", "self-regulat*", "voltage regulation",
                    "traffic regulation", "regulation of traffic"],
    },
    "Data location": {
        "terms": ["data location*", "location of data", "location of the data", "data residency", "data sovereignty",
                  "digital sovereignty", "data locali*", "jurisdiction*", "cross-border", "transborder",
                  "geofenc*", "geographic location of data", "data placement across jurisdiction*"],
        "exclude": ["location privacy", "location-based", "location based service*"],
    },
    "e-Discovery": {
        "terms": ["e-discovery", "ediscovery", "electronic discovery", "forensic*", "digital evidence",
                  "chain of custody", "law enforcement", "subpoena*", "lawful interception", "lawful access",
                  "evidence collection", "evidence acquisition", "seizure"],
    },
    "Provider privilege": {
        "terms": ["malicious insider*", "insider threat*", "insider attack*", "insider*", "rogue administrator*",
                  "rogue employee*", "privilege escalation", "privileged user*", "privileged access",
                  "honest-but-curious", "honest but curious", "semi-honest", "semi-trusted", "curious cloud",
                  "curious server*", "untrusted cloud", "untrusted server*", "untrusted provider*",
                  "untrusted third part*", "malicious cloud provider*", "malicious provider*",
                  "malicious administrator*", "cloud provider* cannot", "even the cloud provider",
                  r"re:\b(?:untrusted|malicious|dishonest|compromised|corrupt(?:ed)?)\s+(?:cloud\s+)?"
                  r"(?:server|storage server|service provider|csp|pkg|cloud)s?\b",
                  "not fully trusted", "cannot be fully trusted", "may not be trusted"],
    },
    # ---- Compliance
    "Service conformity": {
        "terms": ["complian*", "conformity", "conformance", "certification*", "certified", "certifying",
                  "ISO 27001", "ISO/IEC 27001", "ISO 27017", "ISO 27018", "SOC 2", "FedRAMP", "PCI DSS", "PCI-DSS",
                  "CSA STAR", "cloud controls matrix", "security standard*", "assurance"],
        "exclude": ["certificate*", "certificateless"],
    },
    "SLA": {
        "terms": ["SLA", "SLAs", "service level agreement*", "service-level agreement*", "SLO", "SLOs",
                  "service level objective*", "terms of service", "cloud contract*", "security SLA*"],
    },
    "Loss of service": {
        "terms": ["outage*", "downtime", "service disruption*", "service interruption*", "service unavailab*",
                  "service availability", "business continuity", "disaster recovery", "cascading failure*"],
    },
    "Audit": {
        "terms": ["audit*", "auditab*", "accountab*", "audit trail*", "provenance", "public auditing",
                  "TPA", "third party auditor*", "third-party auditor*", "proof of retrievability",
                  "proofs of retrievability", "provable data possession", "integrity verification",
                  "integrity auditing", "security assessment*", "security monitoring", "logging", "log analysis"],
        "exclude": ["auditory"],
    },
    # ---- Governance
    "Data control": {
        "terms": ["data control", "control over data", "control over their data", "control over the data",
                  "control of data", "control of their data", "loss of control", "lose control", "data governance",
                  "data ownership", "data lifecycle", "data life cycle", "data placement", "user control*",
                  "owner control*", r"re:\b(?:no|little|lack of|limited|without)\s+(?:\w+\s+)?control\s+over\b"],
    },
    "Security control": {
        "terms": ["security control*", "security polic*", "security management", "security governance",
                  "security posture", "risk management", "risk assessment*", "risk analysis", "risk model*",
                  "policy enforcement", "CSPM", "penetration test*", "vulnerability assessment*",
                  "vulnerability scan*", "security risk*", "threat model*", "threat assessment*",
                  "cloud governance", "IT governance"],
        "exclude": ["data governance"],
    },
    "Lock-in": {
        "terms": ["lock-in", "vendor lock*", "portability", "interoperab*", "data migration", "cloud migration",
                  "migrat* to the cloud", "exit strategy", "service termination", "open standard*",
                  "standardi*"],
    },
    # ---- Data security
    "Cryptography": {
        "terms": ["encrypt*", "decrypt*", "cryptograph*", "cryptosystem*", "cipher*", "homomorphic*",
                  "attribute-based", "ABE", "CP-ABE", "KP-ABE", "proxy re-encryption", "key management",
                  "key distribution", "key agreement", "key exchange", "KMS", "secret sharing", "zero-knowledge",
                  "MPC", "secure multi-party computation", "multiparty computation", "differential privacy",
                  "differentially private", "anonymi*", "anonymous", "pseudonym*", "digital signature*",
                  "signcryption", "signature scheme*", "elliptic curve*", "ECC", "AES", "RSA", "hash function*",
                  "privacy-preserving", "privacy preserving", "sensitive data", "data confidentiality",
                  "confidential data", "data privacy", "privacy of data", "privacy protection", "steganograph*",
                  "watermark*", "obfuscat*", "quantum key", "post-quantum", "lattice-based"],
    },
    "Redundancy": {
        "terms": ["backup*", "replica*", "data loss", "data integrity", "integrity of data", "integrity of the data",
                  "data availability", "data durability", "erasure cod*", "integrity check*", "data recovery",
                  "fault toleran*", "fault-toleran*", "redundan*", "deduplication", "data corruption"],
    },
    "Disposal": {
        "terms": ["data deletion", "data destruction", "data disposal", "data remanence", "assured deletion",
                  "secure deletion", "verifiable deletion", "residual data", "sanitiz*", "sanitis*",
                  "crypto-shredding", "right to be forgotten", "right to erasure", "data erasure", "deletion of data"],
    },
    # ---- Network security
    "Transfer security": {
        "terms": ["data in transit", "in transit", "TLS", "SSL", "HTTPS", "VPN", "VPNs", "IPsec", "secure channel*",
                  "secure communication*", "secure transmission", "data transmission", "transmission of data",
                  "man-in-the-middle", "MITM", "eavesdrop*", "replay attack*", "live migration", "VM migration",
                  "virtual machine migration", "transport layer security", "sniff*", "spoof*",
                  "communication security"],
    },
    "Firewalling": {
        "terms": ["firewall*", "packet filter*", "intrusion detection", "intrusion prevention", "intrusion*", "IDS",
                  "IPS", "IDPS", "DDoS", "DoS", "denial of service", "denial-of-service", "security group*",
                  "microsegment*", "micro-segment*", "network segmentation", "network isolation", "VLAN*", "botnet*",
                  "traffic filtering", "malicious traffic", "flooding attack*", "EDoS", "threat detection"],
        "net": ["anomaly detection", "anomal*", "attack detection", "malware detection", "malware"],
    },
    "Security configuration": {
        "terms": ["misconfigur*", "security configuration*", "configuration management", "hardening", "hardened",
                  "patch management", "patching", "SDN", "software-defined network*", "software defined network*",
                  "NFV", "security misconfiguration*", "configuration error*", "secure configuration*"],
    },
    # ---- Interfaces
    "API": {
        "terms": ["API", "APIs", "application programming interface*", "RESTful", "REST", "web service*",
                  "API gateway*", "SOAP", "WSDL", "insecure interface*", "microservice*"],
    },
    "Administrative interface": {
        "terms": ["management interface*", "management console*", "management portal*", "control plane",
                  "management plane", "admin* console*", "admin* interface*", "orchestrat*",
                  "infrastructure as code", "infrastructure-as-code", "IaC", "DevOps", "DevSecOps", "CI/CD",
                  "VM management", "remote management", "cloud management platform*", "self-service portal*",
                  "cloud administrator*", "cloud management"],
    },
    "User interface": {
        "terms": ["user interface*", "web interface*", "web portal*", "browser*", "dashboard*", "usability",
                  "phishing", "web application*", "UI", "user experience", "front-end", "front end"],
    },
    "Authentication": {
        "terms": ["authenticat*", "access control*", "authori*", "identity management", "identity provider*",
                  "identity and access management", "IAM", "single sign-on", "SSO", "OAuth", "OpenID", "SAML",
                  "multi-factor", "MFA", "2FA", "two-factor", "password*", "credential*", "account hijack*",
                  "biometric*", "RBAC", "ABAC", "role-based access", "attribute-based access", "user identit*",
                  "login", "log-in", "sign-on"],
        "exclude": ["authority", "authorities", "authoritative"],
    },
}

# ---------------------------------------------------------------------------- 5 Figure-11 virtualization axes
AXES = {
    "hypervisor-vulnerabilities": {
        "terms": ["virtualization security", "virtualisation security", "virtualization vulnerabilit*",
                  "virtualisation vulnerabilit*", "virtualization attack*", "hypervisor security", "hypervisor attack*",
                  "hypervisor vulnerabilit*", "hyperjack*", "kernel vulnerabilit*"],
        "threat": ["hypervisor*", "virtual machine monitor*", "VMM", "Xen", "KVM", "QEMU", "ESXi", "vSphere", "Hyper-V",
                   "VirtualBox", "virtualization layer", "virtualisation layer", "virtualization platform*",
                   "container runtime*", "runc", "containerd", "docker daemon", "docker engine", "shared kernel",
                   "host kernel"],
        "virt": ["kernel exploit*", "virtuali* vulnerabilit*", "virtuali* threat*",
                 "virtuali* risk*", "virtuali* attack*", "virtuali* security"],
    },
    "isolation": {
        "terms": ["VM isolation", "tenant isolation", "container isolation", "performance isolation",
                  "resource isolation", "memory isolation", "kernel isolation", "hardware isolation",
                  "workload isolation", "VM escape", "container escape", "guest escape", "guest-to-host",
                  "noisy neighbo*", "performance interference", "TEE", "TEEs", "trusted execution environment*",
                  "SGX", "enclave*", "TrustZone", "SEV", "TDX", "confidential computing", "confidential VM*",
                  "confidential virtual machine*", "unikernel*", "microVM*", "gVisor", "Kata Containers", "seccomp",
                  "multi-tenant isolation", "multitenant isolation", "strong isolation"],
        "virt": ["isolat*", "sandbox*", "escape*", "breakout", "resource contention", "namespace*", "cgroup*",
                 "separation"],
        "exclude": ["network isolation", "fault isolation"],
    },
    "cross-vm-attacks": {
        "terms": ["cross-VM", "cross VM", "cross-tenant", "inter-VM", "co-resid*", "flush+reload", "prime+probe",
                  "rowhammer", "speculative execution", "transient execution", "Spectre", "Meltdown", "L1TF",
                  "Foreshadow", "VM placement", "placement attack*", "VM hopping", "malicious tenant*", "co-tenant*",
                  "malicious VM*", "malicious virtual machine*"],
        "virt": ["side-channel*", "side channel*", "covert channel*", "cache timing", "cache attack*",
                 "cache-based attack*", "cache side", "co-locat*", "colocat*", "neighbo*"],
    },
    "data-leakage": {
        "terms": ["memory deduplication", "page sharing", "KSM", "memory disclosure"],
        "virt": ["data leak*", "information leak*", "leak*", "residual data", "residual memory", "data exposure",
                 "snapshot*", "VM image*", "image leak*"],
    },
    "vm-identification": {
        "terms": ["VM identification", "VM identity", "virtual machine identification", "virtual machine identity",
                  "virtual machine introspection", "VM introspection", "VMI", "VM fingerprint*", "workload identit*",
                  "instance identit*", "VM attestation", "container attestation", "vTPM", "virtual TPM",
                  "VM image integrity", "image provenance", "tenant attribution", "tenant identification"],
        "virt": ["attestation", "remote attestation", "trusted boot", "measured boot", "introspection",
                 "fingerprint*", "identif* VM*", "identity of VM*"],
    },
}

# Terms that make an axis hit "non-classic" (RB3 reruns without containers, serverless and TEEs).
NON_CLASSIC = ["container*", "docker", "kubernetes", "serverless", "TEE", "TEEs",
               "trusted execution environment*", "SGX", "enclave*", "TrustZone", "SEV", "TDX", "confidential computing",
               "unikernel*", "microVM*", "gVisor", "Kata Containers", "runc", "containerd", "seccomp", "cgroup*",
               "namespace*"]

# ---------------------------------------------------------------------------- type rules
SURVEY_TITLE = ["survey*", "review*", "systematic literature", "systematic mapping", "state of the art",
                "state-of-the-art", "overview", "open issues", "open challenges", "research challenges",
                "research directions", "future directions", "tutorial", "SoK", "taxonomy", "literature",
                "an introduction", "introduction to", "current challenges", "key challenges", "a primer",
                "bibliometric*", "a study of", "an analysis of", "challenges and", "issues and challenges"]
SURVEY_LEAD = ["survey*", "we review", "this review", "literature review", "systematic review", "systematic literature",
               "systematic mapping", "overview of", "an overview", "comprehensive review",
               "bibliometric*", "this chapter", "taxonomy of", "we discuss", "this paper discusses",
               "this article discusses", "re:we analy[sz]e the (?:security )?(?:issues|challenges)"]
# A contribution sentence needs a subject (or "proposed"), a proposing verb and an artifact noun.
SUBJECT_CUES = ["we", "our", "this paper", "this work", "this article", "this study", "this chapter",
                "this research", "this thesis", "this project", "the authors", "the proposed", "proposed"]
CONTRIBUTION_VERBS = [
    r"re:\b(?:propos(?:e|es|ed|ing)|present(?:s|ed|ing)?|introduc(?:e|es|ed|ing)|develop(?:s|ed|ing)?"
    r"|design(?:s|ed|ing)?|devis(?:e|es|ed|ing)|build(?:s|ing)?|built|implement(?:s|ed|ing)?"
    r"|construct(?:s|ed|ing)?|put forward|formulat(?:e|es|ed|ing)|creat(?:e|es|ed|ing)|establish(?:es|ed|ing)?"
    r"|deploy(?:s|ed|ing)?|offer(?:s|ed|ing)?|suggest(?:s|ed|ing)?|contribut(?:e|es|ed|ing)|provid(?:e|es|ed|ing)"
    r"|enhanc(?:e|es|ed|ing)|improv(?:e|es|ed|ing)|extend(?:s|ed|ing)?|integrat(?:e|es|ed|ing))\b"]
# Present-tense passive ("a scheme is proposed") stands for subject + verb (+ artifact).
PASSIVE_CONTRIBUTION = [
    r"re:\b(?:is|are)\s+(?:also\s+|then\s+|further\s+|hereby\s+)?"
    r"(?:propos|present|introduc|develop|design|implement|construct|devis|put forward)\w*",
    r"re:\bhas\s+been\s+(?:develop|design|implement|construct|devis)ed"]
# Other people's work and claims are not contributions; masked before the contribution test.
NOT_OURS = ["proposed by", "presented by", "introduced by", "developed by",
            r"re:\b(?:was|were|have\s+been|recently|previously|already|earlier|traditionally)\s+(?:\w+\s+)?(?:propos|present|introduc|develop|design)\w*",
            r"re:\bet\s+al\.?,?\s+(?:\w+\s+){0,3}?(?:propos|present|introduc|develop|design)\w*",
            r"re:\b(?:suggest|show|indicate|demonstrate|argue|claim)s?\s+that\b", "existing scheme*", "existing work*",
            "existing approach*", "existing method*", "existing solution*",
            r"re:\b(?:need|needs|needed|calls?)\s+(?:for|to)\s+\w+"]
ARTIFACT_NOUNS = ["scheme*", "framework*", "protocol*", "mechanism*", "system*", "approach*", "architecture*",
                  "model*", "method*", "methodolog*", "technique*", "algorithm*", "tool*", "solution*", "prototype*",
                  "countermeasure*", "defen*", "mitigation*", "platform*", "construction*", "polic*", "middleware",
                  "strategy", "strategies", "engine*", "detector*", "classifier*", "library", "libraries",
                  "service*", "infrastructure*", "design*", "implementation*", "process", "structure"]
ATTACK_CUES = ["attack*", "exploit*"]
DEFENSIVE_CUES = ["defen*", "mitigat*", "countermeasure*", "detect*", "prevent*", "protect*", "thwart*", "resist*",
                  "secure*", "securing", "defeat*", "block*", "harden*", "enforc*"]

# ---------------------------------------------------------------------------- NVD axis rules (CVE descriptions)
NVD_VIRT_CONTEXT = ["hypervisor*", "virtual machine*", "VM", "VMs", "VMM", "guest*", "Xen", "KVM", "QEMU", "ESXi",
                    "Hyper-V", "VirtualBox", "bhyve", "Firecracker", "runc", "containerd", "CRI-O", "LXC", "gVisor",
                    "Kata Containers", "docker daemon", "docker engine", "dockerd", "container runtime*",
                    "container escape*", "container isolation", "privileged container*", "VMware", "vSphere",
                    "virtuali*", "virtualis*", "enclave*", "SGX", "TDX", "SEV"]
NVD_EXCLUDE = ["java virtual machine", "JVM", "memory leak*", "guest user*", "guest account*", "guest network*",
               "guest wi-fi", "guest wifi", "guest wireless", "guest access", "guest portal*", "guest login",
               "docker hub image* contain*"]
NVD_AXES = {
    "virtualization-layer": ["hypervisor*", "virtual machine monitor*", "Xen", "KVM", "QEMU", "ESXi", "Hyper-V",
                             "VirtualBox", "bhyve", "Firecracker", "runc", "containerd", "CRI-O", "LXC", "gVisor",
                             "Kata Containers", "docker engine", "docker daemon", "container runtime*", "vSphere",
                             "VMware Workstation", "VMware Fusion", "VMware Tools"],
    "isolation": ["escape*", "breakout", "break out", "guest-to-host", "guest to host",
                  "code execution on the host", "execute code on the host", "execute arbitrary code on the host",
                  "host OS", "access the host", "the host system", "privileged container*", "container isolation"],
    "cross-vm-attacks": ["side channel*", "side-channel*", "speculative execution", "transient execution",
                         "another guest", "other guest*", "other virtual machine*", "another virtual machine",
                         "another VM", "other VMs", "cross-tenant", "co-resident", "cache timing", "covert channel*"],
    "data-leakage": ["information disclosure", "disclose*", "disclosure", "leak*", "read host memory",
                     "read guest memory", "uninitiali* memory", "sensitive information", "memory contents",
                     "out-of-bounds read", "obtain sensitive"],
}
