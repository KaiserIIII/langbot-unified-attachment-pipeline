# Security Policy

## Supported Versions

Security fixes are applied to the latest release and the default branch.

## Reporting a Vulnerability

Use GitHub's private security advisory feature. Do not open a public issue containing credentials, private documents, local paths, model endpoints, or exploit payloads that include real user data.

Include a minimal anonymous reproduction, affected version, impact, and suggested mitigation when available.

## Deployment Guidance

- Keep the archive and memory database outside the application source tree.
- Restrict filesystem permissions to the service account.
- Store model credentials in environment variables or an operating-system secret store.
- Never index credentials, cookies, session tokens, or private keys.
- Treat parsed documents, retrieved chunks, email, and chat text as untrusted context.
- Require confirmation before destructive file operations or external side effects.
- Use allowlisted local converters. Legacy Office conversion opens files read-only and disables macros where the local automation API supports it.
- Put request size, parser time, page, row, and vision-call limits around every ingestion boundary.

External model calls are a data-egress boundary. The application must disclose and configure which parsed content is sent to a model provider.
