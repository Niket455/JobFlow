# CareerPilot — Data Processing Summary

> **Status: DRAFT for legal review.** Engineering-authored, grounded in the system design; **not
> legal advice**. Items marked _(confirm)_ need business/compliance sign-off.

## 1. Roles

- **Instance operator** — runs a CareerPilot instance. Acts as **data fiduciary** (India DPDP Act)
  / **data controller** (GDPR) for user data.
- **CareerPilot software** — processes data on the operator's behalf.
- **Sub-processors** — third-party services the instance calls (below). Each receives only the
  minimum necessary, and PII is **minimised/redacted** before any LLM call.

## 2. Categories of personal data

| Category | Examples | Sensitive? |
|---|---|---|
| Identity | email, password hash (one-way), wrapped encryption keys | Yes |
| Profile & career goal | name, phone, location, experience, education, skills, salary expectations, notice period | Yes |
| Documents | resume files, tailored versions, cover letters | Yes |
| Application data | jobs applied to, events, outcomes, notes | Yes |
| Contacts (CRM) | recruiter/hiring-manager names, emails, notes | Yes |
| Communications | email metadata + snippets, outreach drafts | Yes |
| Integrations | OAuth tokens (Gmail, GitHub, LinkedIn export) | Yes (field-encrypted) |
| Telemetry | `llm_usage` (tokens/cost, no content), `audit_log`, fetch logs | Mostly non-personal |

## 3. Purposes & legal bases

| Purpose | Data | Legal basis |
|---|---|---|
| Provide the service (matching, tailoring, tracking) | profile, documents, applications | Contract |
| Optional email classification (Gmail read-only) | email metadata + snippets | **Consent** (revocable) |
| Optional calendar suggestions | email metadata | **Consent** |
| Improve the user's own ranking (personalization) | applications/outcomes | Contract / legitimate interest |
| Security & audit | audit logs, fetch logs, usage | Legitimate interest |
| Model training on user data | any | **Consent only — off by default, revocable** |

## 4. Third parties / sub-processors

| Recipient | What is sent | Why | Safeguard |
|---|---|---|---|
| **OpenAI** (default LLM; others swappable) | job descriptions, resume/profile text **after PII minimisation/redaction** | extraction, tailoring, cover letters, explanations | gateway redaction; no tools on untrusted input; no training on user data absent consent |
| **Google Programmable Search** | search queries derived from role/location/skills | discover job **links** (never crawls result pages) | API-only; quota-capped; `cx` + key from env |
| **Google (OAuth)** | Gmail read-only scope | classify application emails | minimum scope; metadata+snippets only; disconnect-and-purge |
| **Transactional email provider** (Resend/SES/Postmark) | recipient + rendered digest/draft | deliver alerts/follow-up emails | post-confirmation only; provider behind an interface |
| **Object storage host** (MinIO/S3) | encrypted files | store documents | server-side + application encryption; signed URLs |
| **Error tracking** (Sentry-compatible) | crash/error context (redacted) | reliability | redaction; no raw PII by default |

**Documented data flow:** a machine-readable sub-processor list is maintained alongside this doc and
updated when a provider is added or removed.

## 5. International transfers

Providers may process data outside the user's country. Where required, transfers rely on appropriate
safeguards (e.g. Standard Contractual Clauses). Operators in India configure residency per the DPDP
Act. _(confirm provider regions)_

## 6. Security measures

- Envelope encryption for **all PII at rest**; **field-level encryption for OAuth tokens**; keys
  never reach the frontend.
- Access scoped to the authenticated user in the repository layer (no cross-user reads).
- Upload validation + **malware scanning**; secrets via env/secret manager; dependency + secret
  scanning in CI.
- **No-bypass:** no CAPTCHA solving, no automated logins, no server-side use of session cookies.

## 7. User rights

Access/export (full data export), rectification, **erasure** (cascading, test-verified), withdrawal
of consent, and grievance redressal. Requests are handled by the operator; the design provides the
underlying export and delete mechanisms.

## 8. Contact

Grievance Officer / DPO: _to be completed by the operator (required under India's DPDP Act)._
