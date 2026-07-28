# windows-remote — Desktop remote-access bootstrap

Gate scripts for **docs/17-remote-access-runbook.md** (SSH + Claude Code + Sunshine over Tailscale).
Read the runbook first — it carries the contract, the verification steps, and the rollback for
everything here.

| Script | Gate | Runs as |
|---|---|---|
| `gate1-bootstrap.ps1` | Gate 1 — enable sshd, firewall scoped to the tailnet at birth | Rab, elevated **unpackaged** PowerShell, at the desk |
| `gate2-lockdown.ps1` | Gate 2 — key install → *proven login* → password-auth lockout (two runs by design) | Rab, elevated |

Both scripts self-assert what they need (elevation via `#Requires`; Gate 1 also refuses
MSIX-sandbox-redirected shells — the S29 ghost surface must never do system configuration).

Zero coupling to the pipeline: nothing here reads or writes `ml\library`, the widget, or the vault.
