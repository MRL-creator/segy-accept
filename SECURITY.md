# Security

Only the latest v0.1 preview is maintained. This is an offline local-file tool;
it is not a sandbox for hostile files, a hosted upload service, or a SEG-Y
conformance certification. Its native segyio dependency has its own security
boundary. Use stable, trusted copies of inputs and a current Python environment.

To report a vulnerability privately, use
[GitHub private vulnerability reporting](https://github.com/MRL-creator/segy-accept/security/advisories/new).
Provide the affected version, impact, and a synthetic reproduction. Do not post
credentials, proprietary surveys, or exploit details in a public issue. If private
reporting is unavailable, open a minimal issue requesting a private reporting
channel without disclosing the vulnerability.

Release checks audit resolved dependencies and build/install the package in clean
environments. Input guards, bounded reads, HTML escaping, and report alias checks
reduce specific risks; they do not establish absence of native-parser defects or
provide an atomic filesystem snapshot.
