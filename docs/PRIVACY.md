# Privacy model

## Repository boundary

The public repository contains synthetic demonstration records only. Generated names
have been replaced with neutral `Demo Patient` labels, source encounter identifiers
have been removed, and raw clinical corpora are not included.

Do not add real charts, exported EHR records, screenshots containing patient details,
API keys, `.env` files, model caches, or Ollama runtime data.

## Runtime boundary

- The web application starts on `127.0.0.1`, not the LAN interface.
- Ollama endpoints are accepted only when their hostname is `localhost`, `127.0.0.1`,
  or `::1`.
- Retrieval vectors and BM25 indexes remain in process memory.
- Browser results are session-only and are not written to `localStorage`.
- The application has no telemetry or cloud API client.

The browser, Python process, embedding model, and Ollama still share the security of
the host computer. Local-only does not replace device encryption, OS access control,
malware protection, backups governance, or clinical privacy procedures.

## Network exceptions

Installation and initial model downloads require internet access. The policy scraper
also contacts `gov.bc.ca`, but refuses to run unless `--allow-network` is supplied.
Patient content is not an input to the scraper.

## Real-world use

This repository is not configured for identifiable health information. A real pilot
would require a documented privacy impact assessment, role-based access, audit logs,
data retention controls, encrypted storage and transport, threat modelling, incident
response, and review by the responsible clinical/privacy teams.
