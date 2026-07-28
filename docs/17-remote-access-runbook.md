# 17 — Remote Access Runbook: SSH + Claude Code + Sunshine over Tailscale (Desktop)

**Status:** Gate 0 (preflight + this runbook) complete — Desktop S46, 2026-07-28.
Gates 1–2 are Rab's next move (~15 min total, one of them at the desk). Gates 3–6 follow over SSH.

**Source:** Rab's "whole plan" brief (2026-07-28, pasted from Gmail, built on an external fact-check).
This document **supersedes that brief.** Every command here was re-grounded against the actual machine
on 2026-07-28 (§1), every claim re-verified (§2), and the steps re-sequenced into verification-gated
phases with rollback (§4). Do not run commands from the original brief — two of its command blocks are
corrupted (§2 items 2–3) and one targets an account that no longer exists (§2 item 1).

---

## 0. Why — and why this shape

**The need (Rab's words):** develop outside the home, when the desktop can't be reached in person.

**The motivating incident is already in the ledger.** S45 (2026-07-25): a 1,356-page convert wedged at
the VRAM ceiling — progress frozen five hours, GPU pinned at 9,469/10,240 MiB, 100 % util — and the
only reason it was caught at all was that a Claude session happened to be running. With SSH, that is a
two-minute check-and-kill from a phone terminal or the ThinkPad, from anywhere. Remote access is not a
gaming feature with a dev side benefit; for this factory it is an operations requirement.

**What this build delivers — four rails on one transport (the tailnet):**

1. **Remote terminal + Claude Code** (OpenSSH Server): git, pipeline ops, diagnostics, and full
   Claude Code sessions with the pinned memory library — the MUSTER works identically over SSH
   because it's the same machine, same user, same `~/.claude`.
2. **Remote file intake:** `scp book.pdf desktop:ml/library/drop/` — the pipeline becomes remotely
   fed. The watcher, dedup, quarantine, and audit semantics all apply unchanged; this is the
   docs/14 Phase B "submit" action, delivered early through a door that already exists.
3. **Remote GUI + game streaming** (Sunshine → Moonlight): the full desktop at 60 fps — which means
   the **widget's Room is visible from anywhere**, and the RTX 3080 becomes a personal cloud gaming
   box on the ThinkPad.
4. **Forensic accounting for all of it** (§8): every SSH authentication lands in an independent
   Windows event log — a third clock, cross-checkable against the ledger's claims about remote
   sessions.

**Relation to docs/14 / the remote-dispatch vision:** complementary, not competing. docs/14 is the
*phone window* (projection, ThinkPad-hosted, button-only). This runbook is the *Desktop door* that
both docs/14 Phase B and the remote-dispatch north star quietly assumed would exist. Note for that
vision: the Mac static host is **not enrolled in the tailnet yet** (§1) — that remains future work.

**A structural win worth naming:** an SSH session is an **unpackaged** surface by construction. Every
Claude session dispatched through the desktop app runs inside the MSIX container (the S29 ghost —
re-proven this session, §1). Claude-over-SSH is therefore the first Desktop execution surface where
AppData reads/writes are guaranteed real. The ghost class ends at the SSH prompt.

---

## 1. Ground truth (measured, S46 preflight, 2026-07-28)

| Fact | Measured value |
|---|---|
| Windows account | **`bndit`** (`whoami` → `desktop-bndit\bndit`). The brief's `Rabbiallah` is the dead pre-reset account. |
| Hostname | **`DESKTOP-BNDIT`** (memory + old ledger rows say `DESKTOP-OBTQIRD` — stale or renamed; flagged to Rab) |
| Desktop tailnet | `100.108.102.101` · MagicDNS `desktop-bndit.tailc44e8c.ts.net` |
| ThinkPad tailnet | `archlinux` = `100.107.238.61` — a **tagged** node (`tagged-devices`), so the tailnet ACL needs checking at Gate 2 |
| Other nodes | `iphone-14` = `100.97.237.60` (offline at measure time). **No Mac node.** |
| OpenSSH Server | **Absent** — no `sshd` service, no `sshd.exe`. Client tools present (`C:\WINDOWS\System32\OpenSSH\ssh.exe`). |
| RDP | **Disabled** (`fDenyTSConnections = 1`) — and stays that way (§6) |
| Firewall | No ssh/sunshine rules exist yet |
| GPU | RTX 3080 **10 GB**, driver 610.62 — Ampere: NVENC H.264 + HEVC, **no AV1 encode** (brief correct) |
| Sunshine | Not installed. winget v1.29.280 present. |
| Power | **AC sleep = Never (0x0)** — the box stays reachable while powered on. Fast Startup ON (only matters for the deferred WoL step, §6). |
| `claude` CLI | **Not installed for `bndit`** — no npm global, no native install, `where claude` empty. The agent running S46 belongs to the desktop app, not the shell. Gate 3 installs the CLI. |
| This session's surface | **Medium integrity (filtered admin token)** + **MSIX-sandbox-redirected** (AppData probe appeared in `Claude_pzs8sxrjxfjjc\LocalCache` — the S29 ghost, live). Structurally unable — and per the rule below, forbidden — to perform system configuration. |

**Standing rule (new, from this preflight):** *system configuration (services, firewall, HKLM,
`C:\ProgramData`) is only ever done from an elevated, unpackaged shell.* A packaged session's writes
can be silently virtualized into the app container — a ghost sshd config would be strictly worse than
no sshd. Both gate scripts self-assert elevation **and** non-redirection before touching anything.

---

## 2. Corrections ledger — what the brief got wrong, what it missed, what it got right

**False / broken (would have failed or bitten):**

1. **Wrong account everywhere.** `Rabbiallah` appears in the scp target, the ssh login, and the
   scheduled-task `-User`. That account is dead (pre-reset). Everything is `bndit`.
2. **Both firewall command blocks are corrupted.** `-RemoteAddress` reads
   `https://www.google.com/url?q=http://100.64.0.0/10&…` — Gmail rewrote the CGNAT range into a
   redirect URL in transit. Pasted as-is, `New-NetFirewallRule` throws. Correct value: `100.64.0.0/10`.
   *(Systemic lesson: email is a mangling transport. This runbook lives in git; the desktop already
   has the repo — `git pull` is the delivery mechanism, no scp of briefs needed.)*
3. **The tailnet scoping was ineffective as written.** Installing the OpenSSH.Server capability
   auto-creates rule `OpenSSH-Server-In-TCP` allowing port 22 from **any** address, on all profiles.
   The brief adds a scoped rule but never disables the auto rule — so the box would have been open
   to the whole LAN regardless, and (worse) the brief runs firewall scoping as Step 3, *after* two
   steps of exposed operation. Gate 1 disables the auto rule and scopes **at birth**, atomically.
4. **Step 2 is lockout-unsafe.** It installs the key and sets `PasswordAuthentication no` in one
   motion, with no verified key login in between. One BOM, one ACL slip, one wrong key format —
   and every remote door is shut with the only fix being physical. Gate 2 splits this into
   install → **test** → lockdown, enforced by the script's two-step design.
5. **The UAC-over-SSH diagnosis is wrong (the workaround survives for a different reason).**
   Windows OpenSSH gives an admin account the **full, elevated token** in SSH sessions — there is no
   UAC prompt to stall on. The *real* winget-over-SSH risk is MSIX/packaged-app activation failing in
   non-interactive session 0-adjacent contexts. So: try winget first, and the brief's scheduled-task
   fallback remains valid (registered from the SSH session, which *is* elevated) — with the corrected
   username. Verify the token at Gate 4 with `whoami /groups` before relying on this.
6. **`claude` was assumed to exist as a shell command.** It doesn't (§1). Gate 3 installs it —
   without this the entire "ssh in and run Claude on the brief" flow dies at the prompt.

**Missing (an engineer would have hit each of these):**

7. **The tailnet ACL.** The ThinkPad is a *tagged* node and this tailnet has a customized policy
   (docs/02 defines ssh rules). Nothing guarantees `tag:…` → `desktop-bndit:22` is allowed. Gate 2
   includes the reachability probe and the admin-console check.
8. **Sunshine's installer adds its own allow-any firewall rules.** Same class of bug as #3. Gate 4
   audits and scopes them post-install.
9. **Host-key pinning.** Gate 1 prints the server fingerprints; Gate 2's first connect verifies
   against them instead of blind-TOFU. Cheap, and it's the difference between "encrypted" and
   "authenticated".
10. **WAN reality for out-of-home streaming.** Two hard constraints the brief never mentions:
    (a) if Tailscale falls back to a **DERP relay**, streaming is unusable — verify `tailscale ping
    desktop-bndit` reports *direct*; (b) stream bitrate is capped by the **home connection's
    upload** — measure it, set Moonlight to ~70 % of it (720p60 ≈ 10 Mbps, 1080p60 ≈ 20 Mbps).
11. **Power/console interactions.** AC sleep is already Never (nothing to do — but it had to be
    *checked*, not assumed). Monitor-off vs display-active: an HDMI dummy plug keeps EDID present
    with the physical monitor off; DisplayPort hot-unplugs on power-off, which is exactly the
    black-screen trap. Prefer the HDMI plug.
12. **Coexistence laws** (§8): streaming is GPU work — never stream while a convert runs; Sunshine
    captures the **active console session** — if `comed` is at the console, connecting would show and
    control *his* seat. Check `query user` first, always.
13. **Forensic accounting** (§8): sshd logs to a dedicated Windows event channel; that's the access
    ledger for every remote session, and nothing in the brief surfaces it.
14. **Session-death semantics for long jobs.** A process started in an SSH shell dies with the
    connection. The pipeline already solves this — the watcher is the detached executor; remote
    long work is *queued* (`scp` → `drop/`), never run shell-tied. This is a rule, not a tip (§7).

**Correct in the brief (verified, kept):** Sunshine supports Win10 1809+; winget id
`LizardByte.Sunshine`; web UI `https://<ip>:47990`, first launch sets creds; port family off base
47989; Ampere = no AV1; dummy-plug/black-screen mechanism (Desktop Duplication needs an active
display); `administrators_authorized_keys` + its icacls ACL + UTF-8-no-BOM requirement;
`ssh -t` for the TUI; Moonlight can't LAN-discover across the tailnet (add by IP/MagicDNS);
Tailscale cannot wake a sleeping host; Win10-EOL posture (tailnet-only, key-only, never
port-forwarded).

---

## 3. The end state (so every gate has a target)

From anywhere, with the ThinkPad (or any tailnet device):

```bash
ssh desktop                      # ~/.ssh/config alias, key-only, fingerprint-pinned
# → PowerShell on the Desktop, full admin token, real (unpackaged) filesystem
```

- `git pull` / build / test in `Projects\file-portal`, exactly as at the desk.
- `claude` runs with the pinned memory library; MUSTER passes or fails honestly; ledger rows written
  from these sessions are marked *(via SSH)*.
- `scp paper.pdf desktop:ml/library/drop/` from the ThinkPad — or from the phone via any scp app —
  and the watcher, audit, exporter, and vault do the rest; the Gmail-draft standing rule reports it.
- Moonlight (ThinkPad) streams the desktop: the Room on one screen while a convert runs, or a full
  game session in the evening — bounded by the coexistence laws in §8.
- Every one of those accesses is independently accounted for in the OpenSSH event log.
- When the box is *off*, it's off — WoL is deferred work (§6), and the honest UI for it is the
  docs/14 pattern: "plant offline."

---

## 4. The gates

*Each gate: who runs it, where, done-when. Never skip a verification; never run two gates in one
sitting if the first's verification failed.*

### Gate 0 — preflight + runbook ✅ (S46, this document)

No system state changed. Findings in §1; blocked-by-design confirmation: the desktop-app session
measured Medium-IL + sandbox-redirected, which is precisely why Gates 1–2 are structured as below.

### Gate 1 — enable sshd, scoped at birth — **RAB, at the desk, ~5 min**

Open an **elevated, unpackaged** PowerShell (Start menu → Windows PowerShell → Run as administrator
— *not* a shell opened through the Claude app), then:

```powershell
cd C:\Users\Bndit\Projects\file-portal
git pull
Set-ExecutionPolicy -Scope Process Bypass -Force
.\windows-remote\gate1-bootstrap.ps1
```

The script (read it first — it's short): asserts elevation + non-sandbox → installs the
`OpenSSH.Server` capability (name resolved, not hardcoded) → starts `sshd` + sets it Automatic →
sets PowerShell 5.1 as the SSH shell (HKLM `DefaultShell`) → **disables the auto-created allow-any
rule** → adds `SSH (Tailscale only)` scoped to `100.64.0.0/10` → prints the **host-key
fingerprints**. A transcript lands on the Desktop for the ledger.

**Record the fingerprints** (photo or copy into the password manager — they are pinned at Gate 2).
Password auth is deliberately still ON — exposure is tailnet-only, and Gate 2 closes it properly.

**Done when:** `Get-Service sshd` → Running; the fingerprints are recorded.
**Rollback:** `Stop-Service sshd; Set-Service sshd -StartupType Disabled;
Get-NetFirewallRule -DisplayName 'SSH (Tailscale only)' | Disable-NetFirewallRule` (full removal:
`Remove-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`).

### Gate 2 — key-only auth, lockout-safe — **RAB, from the ThinkPad**

```bash
# ThinkPad, once:
ssh-keygen -t ed25519 -C "rab@archlinux -> desktop"     # passphrase recommended
cat >> ~/.ssh/config <<'EOF'
Host desktop
    HostName 100.108.102.101
    User bndit
    ServerAliveInterval 30
    ServerAliveCountMax 4
EOF
ssh desktop whoami        # first connect: COMPARE the fingerprint to Gate 1's record, then yes
```

- **If the connection is refused/filtered:** check the tailnet policy in the admin console — the
  ThinkPad is tagged, and the ACL must allow it to reach `desktop-bndit:22`
  (`nc -zv 100.108.102.101 22` is the probe; `tailscale ping desktop-bndit` proves the path).
- `whoami` over password auth proving `desktop-bndit\bndit` = transport and shell are good.

Then, in an elevated unpackaged PowerShell on the desktop (or over the now-working SSH — it carries
the full token):

```powershell
.\windows-remote\gate2-lockdown.ps1 -PubKey 'ssh-ed25519 AAAA… rab@archlinux -> desktop'
```

Admin accounts ignore `~/.ssh/authorized_keys`; the script writes
`C:\ProgramData\ssh\administrators_authorized_keys` **UTF-8 without BOM** (PS 5.1's default
encodings both break sshd here) and locks its ACL to SYSTEM + Administrators.

**Test — the step the brief skipped:**

```bash
ssh -o PreferredAuthentications=publickey desktop whoami   # must succeed with NO password prompt
```

Only after that succeeds:

```powershell
.\windows-remote\gate2-lockdown.ps1 -DisablePasswordAuth
# backs up sshd_config, sets PasswordAuthentication no, restarts sshd
```

**Done when:** key login works; password login is *refused*
(`ssh -o PreferredAuthentications=password desktop` → permission denied); an scp round-trip is
byte-identical (`scp` a file both ways, `sha256sum` / `Get-FileHash` match).

### Gate 3 — Claude Code over SSH — **Claude executes, Rab watches the first one**

```powershell
# in the SSH session (real, unpackaged surface):
irm https://claude.ai/install.ps1 | iex      # install the Claude Code CLI for bndit
claude --version
```

Then the working pattern replacing the brief's scp-the-brief flow:

```bash
ssh -t desktop        # -t: TTY, so the Claude Code UI renders
# then in PowerShell:
cd C:\Users\Bndit\Projects\file-portal ; git pull ; claude
```

Rules of the SSH era (standing):

- **MUSTER applies unchanged.** Same machine, same user, same pinned `autoMemoryDirectory` — an SSH
  session must run the same two-clock check before work. Ledger rows from these sessions mark the
  machine as `Desktop (via SSH)` so the origin is auditable against the event log (§8).
- **Long GPU work is queued, never shell-tied.** `scp → drop/` and let the watcher own it. An SSH
  disconnect kills the shell's children; the pipeline's detached executor is the design answer.
- **UTF-8:** if box-drawing or emoji garble in the TUI, `chcp 65001` first (PS 5.1 default OEM
  codepage; any modern terminal on Arch is fine on its end).

**Done when:** a MUSTER-clean Claude session has run over SSH end to end, and one queued remote drop
has converted and shipped without the SSH session staying open.

### Gate 4 — Sunshine install + scoping — **Claude over SSH, Rab approving**

```powershell
whoami /groups | findstr /i "S-1-16"     # expect High Mandatory Level — full token, no UAC issue
winget install --id LizardByte.Sunshine --silent --accept-package-agreements --accept-source-agreements
```

If winget fails under sshd (MSIX activation, not UAC — §2 item 5), fallbacks in order:
(a) the one-shot elevated scheduled task from the brief **with `-User "bndit"`**, then unregister it;
(b) download the official installer from LizardByte's GitHub releases (Rab approves the download,
verify the release checksum), run it silently.

Post-install, immediately:

```powershell
# Sunshine's installer adds its own allow-any rules — scope them like Gate 1 did for sshd:
Get-NetFirewallRule | Where-Object DisplayName -match 'Sunshine' | Disable-NetFirewallRule
New-NetFirewallRule -DisplayName 'Sunshine TCP (Tailscale only)' -Direction Inbound -Protocol TCP `
  -LocalPort 47984,47989,47990,48010 -RemoteAddress 100.64.0.0/10 -Action Allow
New-NetFirewallRule -DisplayName 'Sunshine UDP (Tailscale only)' -Direction Inbound -Protocol UDP `
  -LocalPort 47998,47999,48000,48002 -RemoteAddress 100.64.0.0/10 -Action Allow
Get-Service | Where-Object Name -match 'sunshine'      # service present + running
```

**Rab-only:** first visit to `https://100.108.102.101:47990` (self-signed cert warning expected)
sets the web-UI username/password — **password manager, never the repo, never memory, never chat**
(the GEMINI_API_KEY rule applies). Not recoverable if lost.

**Done when:** service running, rules scoped (the allow-any ones disabled), creds stored.

### Gate 5 — display + first stream — **RAB**

1. **Display:** seat an **HDMI dummy plug** (recommended: zero software, zero attack surface, and
   HDMI keeps EDID with the monitor off — DP would hot-unplug). Software alternative if preferred:
   an IDD virtual display driver (e.g. the open-source *Virtual-Display-Driver* project) — Rab
   approves that install explicitly; don't stack it with the plug.
2. **Moonlight on the ThinkPad:** `moonlight-qt` (AUR or Flatpak). Add PC by `100.108.102.101` or
   `desktop-bndit.tailc44e8c.ts.net` (no LAN discovery across the tailnet — brief correct). PIN
   appears in Moonlight → entered in Sunshine's web UI PIN tab.
3. **First stream in-home** (eliminates WAN variables): desktop stream, then a short game run.
   Watch `nvidia-smi` — NVENC uses dedicated silicon, but the 3D load is real.
4. **Out-of-home qualification:** from the remote site, `tailscale ping desktop-bndit` must say
   **direct** (a DERP relay = fix NAT/firewall before judging quality); set Moonlight bitrate to
   ~70 % of the home *upload* (measure it once: fast.com from the desktop).

**Done when:** a stable 10-minute out-of-home desktop stream + input, at a bitrate the home upload
sustains.

### Gate 6 — deferred, deliberately

- **Wake-on-LAN:** requires wired NIC WoL in BIOS, **Fast Startup OFF** (currently ON — §1), and an
  always-on same-LAN emitter. Candidates: the future Mac static host (not enrolled yet) or the
  ThinkPad when home. Tailscale cannot wake a sleeping host (brief correct). Until then the honest
  state is docs/14's "plant offline."
- **RDP stays disabled.** SSH covers the terminal, Sunshine covers the GUI, and an RDP session
  steals/locks the console session Sunshine captures — enabling it would add a surface *and* a
  failure mode for zero coverage gain.
- **Win10 EOL (2025-10-14, passed):** the posture that makes this acceptable is exactly this
  design — tailnet-scoped by address with the default rules disabled, key-only, nothing
  port-forwarded, and the OS-migration question handled separately, on its own timeline.

---

## 5. Security model delta (extends docs/06)

New inbound surface after all gates:

| Port(s) | Service | Scope | Auth |
|---|---|---|---|
| TCP 22 | sshd | `100.64.0.0/10` only (allow-any rule disabled) | ed25519 key only (post-Gate 2), admin ⇒ full token |
| TCP 47984/47989/47990/48010 | Sunshine | tailnet only | web UI creds (47990); Moonlight PIN pairing |
| UDP 47998–48000/48002 | Sunshine streams | tailnet only | paired clients only |

**Non-negotiables:** never port-forward any of these; never re-enable the auto allow-any rules; keys
over passwords always; Sunshine creds in the password manager only; host-key fingerprints pinned on
every new client.

**What this does NOT protect against (docs/06 honesty):** a compromised Tailscale account (2FA is
the mitigation — it's the perimeter for *everything* here); a stolen, unlocked ThinkPad (its key is
a full admin door → key passphrase + immediate revocation path: delete its line from
`administrators_authorized_keys` + revoke the device in the Tailscale console); anything already
running as `bndit` locally. Note the asymmetry with docs/06's Linux posture: the ThinkPad ACL
restricts SSH to an unprivileged user, but on Windows **`bndit` over SSH is a full administrator** —
that is precisely why key-plus-tailnet is the floor, not a nicety.

---

## 6. Remote operations cookbook (the day-2 reference)

**Git / repo** — identical to local; the repo protocol (pull first, ledger discipline) is
location-independent. Merge conflicts on `CLAUDE_README.md` from two machines remain the known
hazard — pull before every push, same as always.

**Pipeline ops from the ThinkPad:**

```bash
scp book.pdf desktop:ml/library/drop/                      # feed the factory
ssh desktop "type C:\Users\Bndit\ml\library\.convert-progress.json"   # live convert stage
ssh desktop nvidia-smi                                     # GPU truth
ssh desktop "type C:\Users\Bndit\ml\library\watcher.log"   # tail the watcher story
```

**The S45 drill, remote edition (wedge triage):** progress file frozen + VRAM pinned ≥ ~9.4 GB +
util 100 % for >30 min ⇒ the documented thrash mode. Per Rab's stall policy (his open S45 question),
kill the convert tree, verify `.gpu-lock` is gone, and leave the evidence in the morning note /
Gmail draft exactly as S45 did locally.

**Reading Claude's reports remotely:**

```bash
ssh desktop "dir \"C:\Users\Bndit\Desktop\CLAUDES DESKTOP MESSAGES FOR BNDIT\""
```

**Who's at the console (before any stream or loud GPU work):**

```bash
ssh desktop "query user"      # comed active ⇒ the seat is his; coordinate, don't connect
```

---

## 7. Diagnostics playbook

| Symptom | Check, in order |
|---|---|
| Can't reach port 22 | `tailscale ping desktop-bndit` (node up? direct?) → `Get-Service sshd` → firewall rule enabled + auto-rule still disabled → tailnet ACL (tagged ThinkPad!) |
| Key auth refused | `administrators_authorized_keys`: exists? BOM-free? ACL = SYSTEM+Administrators only? Key line intact (one line, no wraps)? Then the event log (below) says *why* |
| Every auth, audited | `Get-WinEvent -LogName 'OpenSSH/Operational' -MaxEvents 50` — successes, failures, source IPs. This is the third clock. |
| TUI garbled over SSH | `chcp 65001`; modern terminal client-side; `ssh -t` (not a bare exec) |
| Moonlight black screen | Active display present? (dummy plug seated / monitor on) · console at the lock screen? · Sunshine service running? |
| Stream lags/artifacts | `tailscale ping` says relay ⇒ fix connectivity first · bitrate vs home upload · Sunshine web UI → Troubleshooting → logs (encoder errors live here) |
| winget fails over SSH | It's MSIX activation, not UAC (§2 #5) → scheduled-task one-shot (`-User "bndit"`) → GitHub-release installer with checksum |
| Convert wedged (remote) | §6 drill: progress file → `nvidia-smi` → stall policy → kill → verify `.gpu-lock` gone |
| Sunshine won't pair | Web UI reachable at :47990? PIN tab used within timeout? TCP 47989 rule enabled? |

---

## 8. Coexistence + accounting laws (standing, same force as the projection law)

1. **Never stream while a convert runs.** Marker owns the card (S45: 9.4 GB of 10). The widget ⏻ /
   an empty drop queue is the pre-stream check. Streaming *is* GPU work under the existing
   "never convert while gaming" law — it cuts both ways.
2. **The console seat is singular.** Sunshine mirrors and controls the active console session. If
   `comed` is signed in at the console, a remote connect intrudes on *his* seat — `query user`
   first, coordinate always, and the desktop-machine rules for him apply (answer on facts, don't
   kill Rab's jobs on third-party request, tell him when a stop wasn't his fault).
3. **Remote sessions are ledgered like local ones.** Same MUSTER, same two clocks, machine field
   `Desktop (via SSH)`. The OpenSSH event log independently corroborates *that* a remote session
   happened; the ledger records *what it did*. Discrepancy between them = incident, Rab captures
   evidence (the S45-era rule, extended).
4. **Secrets never transit the repo or memory.** Sunshine creds, key passphrases, fingerprints'
   private halves — password manager only. (Fingerprints themselves — the public hashes — are fine
   to record.)

---

## 9. Done-when (the whole build)

- [ ] Gate 1: `sshd` Running + Automatic, allow-any rule disabled, scoped rule live, fingerprints recorded
- [ ] Gate 2: key login proven, password auth refused, scp round-trip byte-identical, ACL allows ThinkPad→22
- [ ] Gate 3: `claude` CLI installed; one MUSTER-clean SSH Claude session; one queued remote drop converted + shipped
- [ ] Gate 4: Sunshine service up, installer rules disabled, scoped rules live, web creds in password manager
- [ ] Gate 5: pairing done, in-home stream clean, out-of-home stream **direct** (not DERP) at a sustainable bitrate
- [ ] §8 laws acknowledged in memory (segment note) + the event-log third clock spot-checked once
