# CareerPilot — Data Retention Policy

> **Status: DRAFT for legal review.** This is an engineering-authored starting point grounded in
> the system design; it is **not legal advice** and must be reviewed by qualified counsel before
> publication. Defaults marked _(proposed)_ need a business/compliance sign-off.

## 1. Scope

This policy covers all personal data processed by a CareerPilot instance, across every store it
uses: PostgreSQL, S3-compatible object storage, vector embeddings (pgvector), Redis caches, and
any backups. It applies to the operator of the instance (data fiduciary/controller) and to each
end user.

## 2. Principles

- **Data minimisation:** collect only what a feature needs (e.g. email integration stores
  **metadata + snippets only**, never full mailboxes).
- **Purpose limitation:** each data category is tied to a stated purpose (see
  `DATA-PROCESSING.md`).
- **Storage limitation:** nothing is kept longer than the schedule below.
- **Erasure everywhere:** deletion cascades across **all** stores and is **verified by tests**.
- **Consent-gated processing:** optional processing (e.g. model training, email reading) runs only
  with explicit, revocable consent recorded in the `consents` table.

## 3. Retention schedule _(proposed defaults — confirm)_

| Data category | Store | Retention | Notes |
|---|---|---|---|
| Account & identity (email, password hash, keys) | Postgres | Until account deletion | Password hashes are one-way; keys wrapped |
| Profile, career goal, deal-breakers | Postgres | Until deleted or account deletion | Encrypted PII subset |
| Resume files & resume versions | S3 + Postgres | Until deleted or account deletion | Version history is append-only; user can delete versions |
| Generated documents (tailored resumes, cover letters) | S3 + Postgres | Until deleted or account deletion | |
| Applications & `application_events` | Postgres | Until deleted or account deletion | Event log is the application's history |
| Contacts (CRM) & outreach drafts | Postgres | Until deleted or account deletion | |
| Job postings, sources, leads (public data) | Postgres | Until expired/stale, then pruned | Not personal data; refreshed on lifecycle checks |
| Email metadata + snippets | Postgres | **90 days** _(proposed)_ | Full bodies are never stored |
| OAuth tokens (Gmail, GitHub, etc.) | Postgres (field-encrypted) | Until integration disconnected | Revoked + purged on disconnect |
| LLM usage logs (`llm_usage`) | Postgres | **180 days** _(proposed)_ | Token/cost counts + model id; **no prompt content** |
| Audit logs (`audit_log`) | Postgres | **365 days** _(proposed)_ | Sensitive actions incl. agent tool calls |
| Consents (`consents`) | Postgres | Until withdrawn + retention window | Kept as proof of consent state |
| Fetch logs (`fetch_log`) | Postgres | **90 days** _(proposed)_ | Outbound-fetch provenance; not personal data |
| Redis caches / quota counters | Redis | TTL-bound (minutes–hours) | Includes 24 h query cache |

## 4. Deletion & erasure

- **User-initiated:** users can export all data, delete individual items (resumes, applications,
  documents, integrations), or delete their account.
- **Cascade:** deletion removes rows (**Postgres**), objects (**S3**), embeddings (**pgvector**),
  and cache entries (**Redis**) — in one coordinated operation, **asserted by tests** across all
  four stores.
- **Timing:** primary-store deletion is immediate; backups age out on the backup rotation
  (**30 days** _(proposed)_).
- **Consent withdrawal** stops the relevant processing and triggers erasure of data held solely
  for that purpose.

## 5. Legal holds & exceptions

Data may be retained beyond the schedule only where legally required (e.g. an active legal hold),
and the reason is recorded. Aggregated, de-identified analytics that cannot be linked to a user
are out of scope.

## 6. Governance

- **Owner:** the instance operator acts as data fiduciary/controller.
- **Review cadence:** reviewed at least **annually** or on material design change.
- **Grievance / DPO contact:** _to be completed by the operator (required under India's DPDP Act)._
