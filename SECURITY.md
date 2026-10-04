# Security Policy

## Supported versions

Security fixes go into the latest release line (currently `v3.1.0`) and the `main` branch. Older releases are not patched; please upgrade.

## Reporting a vulnerability

**Please do not open a public issue, discussion or pull request for a security problem.**

Report it privately through GitHub: **Security → Advisories → "Report a vulnerability"** on this repository (<https://github.com/SigmaHQ/sigma-cli/security/advisories/new>).
If you cannot use GitHub, contact one of the maintainers listed in `pyproject.toml` privately.

Please include:

- the version or commit, and a minimal Sigma rule, pipeline or command that reproduces the problem, with the observed and expected output;
- the impact you see (see the scope below) and, if you have one, a proposed fix.

## What we treat as a vulnerability

sigma-cli converts, checks and analyses Sigma rules and pipelines, which are often third-party or community content, and writes the results to the terminal or to files. The following are in scope:

- **File system safety:** rule, pipeline or command-line content that causes reads or writes outside the locations the user asked for.
- **Code execution:** processing rules, pipelines, templates or plugins that leads to code execution, unsafe deserialisation, or template evaluation of untrusted input beyond what the user explicitly enabled.
- **Output injection:** untrusted rule content that is not treated as data in generated queries, output formats or console output.
- **Plugin supply chain:** flaws in `sigma plugin` discovery or installation that could install or load unintended packages.
- **Denial of service:** a small crafted rule or pipeline that causes excessive CPU or memory use.
- **Release and supply chain:** weaknesses in this repository's CI or release workflows that could let an outsider publish or alter a released package.

**Out of scope (report publicly as bugs):**

- Conversion or mapping errors that make a rule match more or fewer events than intended, without attacker-controlled input changing the structure of the output. These are important, but they are handled as normal issues and pull requests so fixes reach users quickly.
- A systemic and severe detection gap may be reported privately; the maintainers decide whether it becomes an advisory.

Report problems whose root cause is in pySigma itself (rule parsing, modifiers, processing pipeline machinery, conversion base classes) to [SigmaHQ/pySigma](https://github.com/SigmaHQ/pySigma). Report problems specific to this repository here. Backend-specific query problems go to the backend's repository.

## Our process

| Step                                                                          | Target                                        |
| ----------------------------------------------------------------------------- | --------------------------------------------- |
| Acknowledge the report                                                        | within 5 working days                         |
| Initial assessment and severity (CVSS 3.1)                                    | within 14 days                                |
| Fix developed in the advisory's temporary private fork                        | as soon as practical, normally within 90 days |
| Coordinated release, then GitHub Security Advisory published (CVE via GitHub) | at the fix release                            |

- We credit reporters in the advisory unless they ask not to be credited.
- When a fix affects other SigmaHQ projects, we may coordinate their releases.
- We ask reporters to keep details private until the advisory is published or 90 days have passed, whichever comes first, unless agreed otherwise.
