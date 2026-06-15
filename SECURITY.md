# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report it privately via GitHub's
[private vulnerability reporting](https://github.com/Somu60789/DevSecOps/security/advisories/new)
(Security tab → "Report a vulnerability"). If that is unavailable, open a minimal
issue asking for a private contact channel — without disclosing details.

When reporting, please include:

- A description of the issue and its impact.
- Steps to reproduce or a proof of concept.
- Affected version / commit.

## What to expect

- Acknowledgement of your report as soon as possible.
- An assessment and, where confirmed, a fix on a coordinated timeline.
- Credit in the release notes if you wish.

## Supported versions

Security fixes target the latest `v1` release. Pin `@v1` to receive them
automatically.

## Scope notes

This product orchestrates third-party scanners and an AI runtime. Vulnerabilities
in those upstream tools should be reported to their respective projects;
issues in *this* product's workflows, scripts, or how it invokes those tools are
in scope here.
