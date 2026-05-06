---
name: web-app-security-inspection
description: Perform authorized live or local web application security inspection using browser-visible behavior, HTTP traffic, API calls, authentication and authorization flows, session state, client-side storage, security headers, browser console evidence, and safe runtime validation. Use when Codex needs to inspect a web app, SPA, API-backed UI, admin panel, SaaS workflow, OAuth/OIDC flow, GraphQL/REST endpoint, WebSocket, upload/import/export feature, AI/agent web feature, or bug bounty target through a browser or controlled HTTP/runtime testing.
---

# Web App Security Inspection

Use this skill after `engagement-scope` has established the authorized target,
scope evidence, impact tolerance, accounts/roles, and desired deliverable. If no
engagement brief is present, infer local/read-only scope from the workspace or
ask only for the missing boundary that changes whether live testing is allowed.

Prefer the Codex browser use feature for exploration and validation. Fall back
to Chrome DevTools Protocol (CDP) only when browser use lacks the control needed
for network interception, storage inspection, service worker state, WebSockets,
HAR-style capture, request mutation, console/runtime collection, or precise
device/emulation behavior.

## Current Trend Bias

Recent web-app security sources emphasize:

- Broken access control remains the top web risk; prioritize horizontal and
  vertical authorization checks across UI routes, APIs, object IDs, tenants,
  roles, methods, and hidden functions.
- APIs are the real attack surface for many web apps. Inspect REST, GraphQL,
  WebSocket, mobile-backend, and SPA fetch traffic instead of stopping at the UI.
- Identity exposure, weak MFA, token misuse, session confusion, credential
  stuffing, and account takeover deserve early attention.
- Bot and automation abuse increasingly targets login, checkout, search,
  inventory, password reset, invite, coupon, booking, voting, and other business
  flows at API speed.
- AI and agentic features turn prompt, tool, connector, retrieval, and API
  authorization mistakes into web-app vulnerabilities.
- Supply chain and client-side trust matter: third-party JavaScript, dependency
  updates, CDNs, browser extensions, service workers, CSP, and integrity controls
  can change the runtime security boundary.
- Exploitation windows are shorter, so exposed admin panels, control planes,
  file import/export, support bundles, SSRF-like URL fetchers, and upload flows
  deserve fast triage.

## Inspection Modes

Choose one primary mode:

- Recon and map: discover routes, APIs, roles, browser storage, security headers,
  client bundles, workflows, and trust boundaries.
- Auth and session review: inspect login, logout, MFA, reset, OAuth/OIDC/SAML,
  invitations, token refresh, cookies, device trust, and account linking.
- Authorization review: compare roles, tenants, object ownership, methods,
  hidden UI actions, and direct API calls.
- API and SPA review: inspect fetch/XHR, GraphQL, WebSockets, mobile-style APIs,
  BFF routes, CORS, rate limits, schemas, and error handling.
- Client-side review: inspect DOM XSS, CSP, postMessage, storage, service
  workers, client routing, third-party scripts, source maps, and dependency
  exposure.
- Business logic review: inspect ordering, payment, quotas, coupons, inventory,
  referrals, invite flows, approval state, idempotency, and replay behavior.
- Finding validation: safely reproduce a suspected issue, establish impact, and
  decide whether it is confirmed, duplicate, mitigated, or needs source review.
- Report prep: turn browser and HTTP evidence into a clear bounty, advisory, or
  internal report.

## Browser-First Workflow

1. Restate the engagement brief: target URLs, allowed accounts/roles, in-scope
   flows, prohibited techniques, rate limits, and deliverable.
2. Start passively. Load the app with the Codex browser, capture visible routes,
   navigation, roles, forms, feature flags, console errors, exposed build
   metadata, and interesting client-side state.
3. Build a runtime trust-boundary map. Track actors, tenants, roles, sessions,
   cookies, local/session storage, API tokens, CSRF material, CORS origins,
   service workers, third-party scripts, backend APIs, file/network sinks, and
   privileged business actions.
4. Observe normal traffic before modifying anything. Record route, request
   method, endpoint, auth mechanism, object identifiers, request body shape,
   response status, response data, cache behavior, and side effects.
5. Test one hypothesis at a time using low-impact mutations. Prefer changing
   IDs, roles, methods, content types, optional fields, duplicated parameters,
   tenant headers, pagination, filters, GraphQL selections, and replay timing
   before trying payload-heavy tests.
6. Validate with two states when possible: authorized user versus unauthorized
   user, owner versus non-owner, admin versus standard user, tenant A versus
   tenant B, before versus after logout, or fresh token versus revoked token.
7. Preserve evidence. Capture the smallest request/response pair, screenshot,
   console output, storage value, or browser state needed to explain the issue.
   Redact secrets, tokens, PII, and third-party data.

## CDP Fallback

Use CDP when browser use cannot answer a specific question. Prefer a temporary
browser profile and localhost-only debugging endpoint. Close the browser and
remove temporary profiles when done.

Reach for CDP to:

- Capture or export precise network requests, headers, redirects, preflights,
  WebSocket frames, timing, and cache behavior.
- Inspect cookies, local storage, session storage, IndexedDB, Cache Storage,
  service workers, permissions, and security state.
- Intercept and modify requests when the normal browser interface cannot change
  a field, header, method, body, GraphQL query, or WebSocket message.
- Reproduce device, viewport, locale, geolocation, user-agent, or network
  conditions that affect security logic.
- Collect DOM snapshots, console errors, source maps, bundle references,
  CSP/report-only violations, and JavaScript runtime state.

Do not use CDP to bypass scope, hide activity, defeat consent boundaries, or run
high-volume automation against live systems. If the needed test materially
increases impact, return to `engagement-scope` before proceeding.

## Test Areas

### Authentication And Session

Check login, logout, reset, MFA, remember-me, OAuth/OIDC/SAML, account linking,
device trust, refresh tokens, invite acceptance, and password changes.

Confirm: token scope, audience, expiry, rotation, revocation, SameSite/Secure/
HttpOnly cookie flags, CSRF defenses, session fixation, logout invalidation,
MFA bypass through alternate flows, and state/nonce validation in identity
provider callbacks.

### Authorization And Tenant Boundaries

Check object IDs, nested resources, organization/project/workspace switching,
admin actions, hidden UI controls, bulk endpoints, exports, file downloads,
GraphQL fields, and method changes.

Confirm: server-side authorization occurs for every action and object, including
POST/PUT/PATCH/DELETE, batch APIs, alternate routes, direct API calls, stale UI
state, background jobs, and object references embedded in URLs, bodies, headers,
cookies, or GraphQL variables.

### APIs, GraphQL, And WebSockets

Check REST, GraphQL, BFF routes, WebSocket channels, SSE, mobile API variants,
versioned endpoints, debug schemas, introspection, subscriptions, and batch
operations.

Confirm: object-level and property-level authorization, function-level
authorization, rate limits, input validation, schema exposure, error leakage,
excessive data exposure, mass assignment, query depth/cost limits, replay, and
cross-tenant subscription leakage.

### Client-Side And Browser Boundaries

Check DOM XSS, reflected/stored XSS, postMessage, prototype pollution,
client-side redirects, CSP, Trusted Types, sandboxed iframes, CORS, source maps,
third-party scripts, service workers, browser storage, and URL fragment routing.

Confirm: untrusted data reaches DOM sinks or script execution; messages validate
origin and schema; CSP actually blocks execution; secrets are not stored in
browser-readable locations; service workers cannot cache or serve sensitive
cross-user data; CORS does not expose credentialed APIs to untrusted origins.

### Files, URLs, And Server-Side Fetches

Check uploads, downloads, image/PDF previews, CSV/imports, archives, avatars,
webhooks, URL importers, metadata fetchers, oEmbed, redirects, and export flows.

Confirm: MIME and extension checks are server-side; filenames and archive paths
cannot traverse or overwrite; uploaded content cannot become executable; URL
fetchers cannot reach loopback, link-local, cloud metadata, internal services,
or attacker-controlled redirects; generated files do not leak other users' data.

### Business Logic And Abuse

Check flows where intent and sequence matter: checkout, refunds, coupons,
points, inventory, reservations, invites, approvals, roles, quotas, trials,
search, posting, voting, reporting, and notifications.

Confirm: replay, parallel requests, stale state, duplicate submissions,
negative/large values, missing idempotency, quota bypass, workflow skipping,
automation at scale, and rate-limit gaps on expensive or monetizable actions.

### AI, Agent, And Connector Features

Check chat, copilot, summarization, retrieval, tool execution, workflow agents,
browser agents, connectors, model/plugin settings, file ingestion, and
cross-tenant memory.

Confirm: prompts and retrieved content cannot override tool policy; model output
is treated as untrusted before tool/API calls; tool permissions are bound to the
user, tenant, task, and data source; secrets do not enter prompts, logs, traces,
or eval datasets; one tenant cannot poison retrieval, memory, or connector
state for another.

### Misconfiguration, Headers, And Exceptional Conditions

Check TLS, HSTS, CSP, frame ancestors, X-Content-Type-Options, Referrer-Policy,
Permissions-Policy, cache headers, error responses, debug endpoints, staging
assets, directory listings, source maps, CORS, and unexpected 4xx/5xx handling.

Confirm: failures do not fail open, disclose stack traces/secrets, cache private
responses, expose admin/debug functionality, or create security differences
between frontend, edge, and origin.

## Evidence Standard

Treat a finding as confirmed only when the inspection can explain:

- Entry point: route, screen, API endpoint, WebSocket channel, callback, or
  browser feature.
- Actor and state: account, role, tenant, session age, token state, browser
  storage, and relevant feature flags.
- Control: which fields, headers, identifiers, messages, files, URLs, or timing
  the attacker controls.
- Missing guard: the authorization, validation, isolation, rate limit,
  sandboxing, escaping, signing, or lifecycle check that should exist.
- Impact: confidentiality, integrity, availability, account, tenant, financial,
  automation, or business-process boundary affected.
- Constraints: privileges, victim interaction, rate limits, environment,
  browser behavior, deployment mode, or timing assumptions.
- Reproduction: minimal safe steps, request/response evidence, screenshots, and
  expected versus actual behavior.

Use `Potential` or `Needs validation` when any of these links is missing.

## Output Format

For findings, lead with issues ordered by severity and confidence:

```text
Finding: <short title>
Severity: <critical/high/medium/low/info>
Confidence: <high/medium/low>
Affected surface: <URL/route/API/flow>
Actor/state: <role, tenant, session, browser state>
Issue: <why the security boundary fails>
Impact: <what can happen>
Evidence: <browser observations, request/response, screenshots, console/storage>
Reproduction: <minimal safe steps>
Fix: <specific remediation>
Tests: <browser/API/regression coverage to add>
```

If no issues are found, state the reviewed scope, accounts/roles, flows,
browser/tooling used, assumptions, and remaining coverage gaps.

## Handoff

Use `code-vulnerability-review` when runtime evidence needs source tracing or a
patch. Use `cve-research` for dependency or platform advisories. Use
`fuzz-harness-builder` when a parser, API, or protocol needs systematic input
generation. Use `exploit-chain-analysis` only for authorized lab-only chaining
after individual issues are validated.

## Research Basis

This workflow reflects OWASP Top 10:2025, OWASP API Security Top 10:2023, OWASP
WSTG, OWASP LLM Top 10:2025, CISA KEV trends, Rapid7 2026 Global Threat
Landscape reporting, Wallarm 2026 API ThreatStats, and Imperva/Thales 2026 Bad
Bot reporting. Treat these as prioritization signals; the engagement brief and
observed application behavior remain authoritative.
