# WEEKEND BRIEFING: AI Security & Cybersecurity Research

**June 26–27, 2026**

---

## 🔑 HEADLINE SUMMARY

- **Agentjacking attacks hit 85% success rate** — Tenet Threat Labs reveals new attack class targeting AI coding agents (Claude Code, Cursor, Codex). Malicious instructions embedded in trusted data (error reports, PR titles) hijack agent tool calls and credentials. Even fresh workspaces succumb.
- **LLM agents weaponized for post-exploitation** — First confirmed operational use: threat actors deployed an LLM agent after exploiting Marimo CVE, achieving 4 lateral pivots and full PostgreSQL exfiltration in under 2 minutes. Autonomous, not assisted.
- **vLLM SSRF vulnerability (CVE-2026-24779, CVSS 7.1)** — All pre-0.14.1 versions affected. Backslash URL parsing difference lets attackers access internal resources through multimodal MediaConnector. Patch immediately.

---

## 📄 RESEARCH & PAPERS

### This Week / Recent

| Paper | Venue/Date | Key Finding |
|-------|------------|-------------|
| **Agentjacking AI Coding Agents** | [Tenet Report](https://www.tenetsecurity.com/blog/agentjacking) Jun 2026 | Embedded injections in trusted data achieve ~85% success on Claude Code, Cursor, Codex |
| **Security Analysis of Agentic AI** | [arXiv 2606.14816](https://arxiv.org/html/2606.14816v1) Jun 12 | First taxonomy of agentic AI attack vectors + propagation framework |
| **Automated Multi-Defense Jailbreaks** | [arXiv 2606.14817](https://arxiv.org/html/2606.14817v1) Jun 16 | UniAttack framework beats multiple layers with 64–249% ASR gains |
| **AI Agents May Always Fall for Prompt Injection** | [arXiv 2605.14817](https://arxiv.org/html/2605.14817v1) May 17 | Theses that prompt injection is architectural, not fixable; proposes Contextual Integrity lens |
| **Jailbreaking AI Code Agents** | [arXiv 2510.01359v2](https://arxiv.org/html/2510.01359v2) Jun 15 | JAWS-Bench: prompt-only attacks hit 70%+ ASR on code agents |
| **Red-Team Study: Fable 5 & Opus 4.8** | [arXiv Jun 17](https://arxiv.org/html/2606.18193) | Opus 4.8 still vulnerable at 27.6% to child-safety framing under adaptive search |
| **Indirect Prompt Injection Analysis** | [Google Security Blog](https://blog.google/security/prompt-injections-web/) Apr 2026 | 32% increase in malicious payloads in web content (Nov '25–Feb '26) |

### Notable / High-Impact (Earlier 2026)

- **Prompt Injection as Role Confusion** — [ICML 2026](https://role-confusion.github.io/), [arXiv](https://arxiv.org/abs/2603.12277) — Introduces "CoT Forgery" achieving 60% success by injecting fabricated reasoning into frontier models
- **LLM Ranker Vulnerability Study** — [arXiv 2602.16752](https://arxiv.org/abs/2602.16752) — Comprehensive empirical analysis; encoder-decoder shows strong inherent resilience
- **Blindfold: Jailbreaking Embodied LLMs** — [arXiv 2603.01414](https://arxiv.org/abs/2603.01414) — Physical actions misaligned with linguistic security in robots/embodied systems

---

## 🚨 SECURITY INCIDENTS & CVEs

### Active / New

| ID | Target | Severity | Description |
|----|--------|----------|-------------|
| **CVE-2026-24779** | vLLM (all < 0.14.1) | CVSS 7.1 | SSRF via MediaConnector backslash URL parsing; internal network access |
| **CVE-2026-39987** | Marimo notebooks | Critical | Authenticated RCE → weaponized in first known LLM agent post-exploitation attack |

### Recent Major Incidents

- **OpenAI Codex Token Theft** — Functional npm package `codexui-android` (29K weekly downloads) silently exfiltrating tokens for 1+ month. Not typosquatted; fully maintained legitimate package.

- **Mastra npm Supply Chain Attack** (Jun 17) — Compromised organization, poisoned 140+ packages via `easy-day-js` (dayjs typosquat). 1.1M+ weekly downloads affected. Self-deleting dropper.

- **Malicious AI Agent Skill** — Fake skill passed security checks, reached 26,000+ users on Instagram platform. Operated for weeks before discovery.

- **OTter.ai Meeting Manipulation** — "Ignore prior instructions" speech in meeting destroyed summaries across Otter.ai. Zero technical access needed.

---

## 🏢 INDUSTRY NEWS

### Significant Activity

- **AI Safety Funding Surging** — ~$439M raised YTD 2026 across 9 deals in AI safety sector. Shift toward eval platforms and governance, not just research.

- **Check Point AI Security** — Lakera Guard remains top runtime LLM firewall offering; recently acquired by Check Point (Sep 2025).

- **Palo Alto Networks** — Prisma AIRS expanded via Protect AI acquisition (Jul 2025); leading enterprise AI security platform.

- **GSA New Regulation** — GSAR clause 552.239-7001 finalizes requirements for government LLM data safeguarding.

- **Skills Gap Widens** — 2.5x growth in AI+cybersecurity job demand since 2020. Adversarial ML and LLM security knowledge now table stakes.

### Tooling Worth Noting

- **Bifrost** — Open-source AI gateway consolidating LLM/MCP/Agent gateways in single control plane
- **AccuKnox** — 6-layer runtime protection with prompt firewall + AI red teaming + governance
- **Lasso Security** — LLM interaction monitoring and MCP visibility for agentic workloads
- **HiddenLayer** — Runtime model protection focused on behavioral anomaly detection

---

## 📚 READING LIST

### Priority Reading (this weekend)

1. **[The OWASP Top 10 for AI Agentic Applications (2026)](https://genai.owasp.org/event/rsac-conference-2026-owasp-ai-security-summit-safeguarding-genai-agents-autonomous-ai-risk-2026/)** — Updated framework covering agentic systems. Agent Goal Hijacking is the new #1.

2. **[Tenet Agentjacking Report](https://www.tenetsecurity.com/blog/agentjacking)** — New attack class on coding agents. Actionable findings for development teams.

3. **[Google: Mitigating Indirect Prompt Injections](https://blog.google/security/prompt-injections-web/)** — Technical deep-dive from Google's GenAI security team on layered defense.

4. **[CIS GenAI Security Report](https://www.cisecurity.org/about-us/media/press-release/new-cis-report-warns-prompt-injection-attacks-pose-growing-risk-to-generative-ai)** (Apr 2026) — Concrete steps to reduce exposure.

5. **[BrightSec 2026 State of LLM Security](https://brightsec.com/blog/the-2026-state-of-llm-security-key-findings-and-benchmarks/)** — Benchmarks and threat landscape analysis.

### Secondary Reading

6. **[Future UX Group: Indirect Prompt Injection Universal Flaw](https://futurumgroup.com/insights/indirect-prompt-injection-exposes-a-universal-ai-security-flaw-no-deployment-model-is-immune/)** — Cloud and local AI both vulnerable.

7. **[Simon Willison on Role Confusion](https://simonwillison.net/2026/Jun/22/prompt-injection-as-role-confusion/)** — Good commentary on the fundamental problem.

8. **[PA Unit 42: OpenClaw AI Supply Chain Risk](https://unit42.paloaltonetworks.com/openclaw-ai-supply-chain-risk/)** — Analysis of persistent threats in AI agent ecosystems.

---

## 📅 UPCOMING EVENTS

| Event | Date | Location | Why |
|-------|------|----------|-----|
| **Real World AI Security 2026** | Jun 23–25 | Stanford University | The academic-industry crossover event. If you attend one, this one. |
| **Global AI Security & Ethics (AISE26)** | Jun 18–19 | Geneva + Online | UNIDIR-hosted. Policy meets technical. Broadest scope. |
| **OWASP GenAI Summit at RSAC** | Jun 2026 | San Francisco | Agentic Top 10, autonomous agents discussion |
| **InfoSec Europe + OWASP GenAI** | Jun 2–4 | London | European angle on GenAI security |
| **AI Risk Summit** | Aug 11–12 | Half Moon Bay, CA | Executive focus but solid technical sessions |
| **Black Hat USA AI Summit** | Sep 2026 | Las Vegas | Vendor-heavy but strong research from security vendors |
| **GrrCON 2026** | Sep 24–25 | Grand Rapids, MI | Hacker/cyber/AI crossover. Best for networking. |

---

*Last updated: June 26, 2026*
