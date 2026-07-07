# Security Policy

## Supported Versions

PoultryGuard AI is in early repository setup. Formal supported versions will be defined after the first tagged release.

| Version | Supported |
| ------- | --------- |
| main    | Best effort |

## Reporting a Vulnerability

Please do not open public issues for security vulnerabilities.

Report suspected vulnerabilities to the project maintainers through the private security contact that will be published before the first public release.

Include:

- A clear description of the issue
- Steps to reproduce
- Potential impact
- Affected files or components
- Suggested remediation, if known

## Security Scope

Future security reviews should include:

- Offline model and data provenance
- Prompt injection risks in local knowledge-base content
- Unsafe file handling
- Dependency vulnerabilities
- Local configuration secrets
- Dataset and model artifact integrity

## Runtime Privacy

PoultryGuard AI is designed to run offline. The project should not transmit farm data, user questions, logs, or model inputs to external services at runtime.

