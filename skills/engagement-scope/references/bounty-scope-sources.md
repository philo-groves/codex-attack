# Bounty Scope Sources

Use this reference when a target appears to be covered by a public bug bounty, vulnerability disclosure, or coordinated vulnerability disclosure program. Always verify live program scope before testing; these URLs are lookup starting points, not cached authorization.

## Source Priority

1. User-provided private invitation, contract, rules of engagement, or current program brief.
2. Official platform program page or official platform API for the named program.
3. Official company security, bounty, or vulnerability disclosure page.
4. Official `security.txt` at `https://<domain>/.well-known/security.txt`.
5. Search results, public writeups, program directories, or third-party aggregators as leads only.

Never treat a brand-owned domain, subsidiary, ASN, repository, package, or mobile app as in scope unless the official program says so. If a scope page says only listed assets are in scope, do not infer neighboring assets.

## HackerOne

- Program page pattern: `https://hackerone.com/<handle>?type=team`
- Use `scripts/hackerone_program_lookup.py` for public GraphQL lookup when a handle is known.
- The lookup script caches public results for 6 hours by default under the Codex cache directory. Use `--refresh` for current verification and include cache status in the engagement brief.
- HackerOne's authenticated Hacker API also has structured scope and scope exclusion endpoints, but it requires an API username and token.
- HackerOne scope fields to preserve: `eligible_for_submission`, `eligible_for_bounty`, asset identifier, asset type, max severity, asset instructions, scope exclusions, safe harbor, submission state, and policy change timestamp.

## Bugcrowd

- Search official engagements first: `site:bugcrowd.com/engagements <program or company>`.
- Individual public engagement pages commonly live under `https://bugcrowd.com/engagements/<slug>`.
- Read the engagement brief, especially Overview, Description, Targets, Known Issues, What's New, Things to Know, Testing Requirements, Disclosure, Safe Harbor, and target reward flags.
- Bugcrowd documentation says the brief's Targets section distinguishes in-scope and out-of-scope targets and that reports against targets not explicitly in scope may be marked out of scope.

## Intigriti

- Search official public program pages first: `site:app.intigriti.com/programs <program or company>`.
- Public program pages commonly use `https://app.intigriti.com/programs/<organization>/<program>`.
- Preserve assets, tiers, asset types, skills, rules, validation timelines, exclusions, disclosure terms, and any required account or VPN instructions.

## YesWeHack

- Search official public program pages first: `site:yeswehack.com/programs <program or company>`.
- Public program pages commonly use `https://yeswehack.com/programs/<slug>`.
- YesWeHack guidance treats scope as the assets hunters are invited to test and recommends treating anything not listed as out of scope by default unless the program states otherwise.
- Preserve scope, type, asset value, reward grid, user-agent, VPN, credentials, disclosure terms, and program version notes.

## Major Direct Programs

- Apple Security Bounty: `https://security.apple.com/bounty/`
- Google Bug Hunters: `https://bughunters.google.com/`
- Google and Alphabet VRP rules: `https://bughunters.google.com/about/rules/google-friends/google-and-alphabet-vulnerability-reward-program-vrp-rules`
- GitHub Bug Bounty scope: `https://bounty.github.com/scope`
- Microsoft Bounty Programs: `https://www.microsoft.com/en-us/msrc/bounty`
- Meta Bug Bounty: `https://www.facebook.com/whitehat`
- Mozilla Security Bug Bounty: `https://www.mozilla.org/en-US/security/bug-bounty/`

When these pages link to product-specific subprograms, rules, target lists, payout guidelines, legal safe harbor, or reporting requirements, follow those official links and use the most specific page for the target.

## Evidence To Capture

For the engagement brief, record:

- Source URL and retrieval date.
- Program name, platform, and handle or slug.
- In-scope targets and asset types.
- Explicitly out-of-scope targets and vulnerability classes.
- Submission and bounty eligibility.
- Safe harbor or legal terms.
- Testing limits, rate limits, account rules, VPN or user-agent requirements, and prohibited techniques.
- Whether production testing is allowed or a lab/staging/local reproduction is required.

If scope is ambiguous, ask the user to provide the current brief or request clarification from the program before continuing.
