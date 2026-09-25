# Privacy and security threat model

## Scope

This document covers the local research prototype included in this repository.
The project is not approved for production use or real patient care.

## Assets to protect

- Clinical text processed during local evaluation
- Locally generated policy caches
- Model prompts and responses
- Configuration and local runtime files
- Any credentials used outside the public demo

The public repository contains only synthetic patients and fictional criteria.

## Trust boundaries

| Boundary | Expected behaviour |
| --- | --- |
| Browser to API | Same-device communication through `127.0.0.1` |
| API to Ollama | Requests are restricted to a loopback address |
| Policy maintenance | Network access requires an explicit maintenance command |
| Public repository | Only synthetic demonstration data is permitted |

## Threats and safeguards

| Threat | Safeguard |
| --- | --- |
| Accidental patient-data commit | Private data paths are ignored and automated tests enforce synthetic demo records |
| Credential exposure | `.env`, key, certificate, and local configuration files are excluded by `.gitignore` |
| Remote access to the application | The supplied launcher binds only to `127.0.0.1` |
| Sending prompts to a remote model | Non-loopback Ollama endpoints are rejected |
| Browser data persistence | Responses use `no-store` headers and the interface does not retain patient history |
| Unsupported model conclusions | Positive findings require evidence citations and numeric threshold checks |
| Outdated policy criteria | Policy updates are explicit and locally generated caches must be manually verified |
| Dependency vulnerabilities | Dependabot checks Python and GitHub Actions dependencies |

## Known limitations

- Loopback binding is not a replacement for authentication in a shared or hostile computer environment.
- A compromised local machine can access locally processed information.
- Dependencies and model files require internet access during installation.
- Extracted policy criteria can be incomplete, outdated, or structurally incorrect.
- Local model output can be inaccurate despite the supplied safeguards.
- The project has not undergone formal clinical, regulatory, penetration, or privacy testing.

## Reporting concerns

Do not include credentials, patient information, or working exploits in a public
GitHub issue. Follow the instructions in the repository’s `SECURITY.md` file.
