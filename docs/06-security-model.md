# 06 — Security Model

Be explicit about what this design protects against and what it doesn't — that's the difference
between a security model and wishful thinking.

## What it protects against

- **Network exposure**: no port is opened on any router or public interface. All traffic rides
  the Tailscale WireGuard tunnel between devices already authenticated into your tailnet.
- **Credential management burden**: no SSH keys to generate, copy, or rotate by hand, and no
  passwords stored anywhere. Tailscale SSH authenticates using the tailnet node identity, which is
  itself gated by your Tailscale account login (and 2FA, if you enable it on your Tailscale
  account).
- **Privilege escalation**: the ACL in [`02-tailscale-setup.md`](02-tailscale-setup.md) explicitly
  restricts SSH `users` to a non-root account. Even if the Windows app were fully compromised, the
  attacker can only do what your unprivileged Linux user can do — no `sudo`, no root shell.
- **Unbounded writes**: the allocator only ever writes inside `~/file-portal/...`. It does not
  accept arbitrary destination paths from the Windows side — the widget only ever sends a
  *category* name, and the category → directory mapping lives solely in `rules.toml` on the Linux
  box. A compromised or buggy widget cannot direct a write outside that tree.

## What it does NOT protect against

- **A compromised Tailscale account.** If someone gets into your Tailscale account, they can add
  themselves to your tailnet (or already-present devices stay trusted). Use 2FA on your Tailscale
  account; this project doesn't add anything on top of Tailscale's own account security.
- **A genuinely malicious file.** The allocator validates size and matches extensions for routing
  purposes — it does not scan content, so don't treat "allocated" as "trusted." If you're pulling
  files from any source you don't fully control, antivirus/sandboxing is still your job.
- **Local compromise of either machine.** If malware is already running as your user on Windows or
  Linux, this design doesn't add a privilege boundary — by design, file-portal itself only ever
  needs the privileges your normal user account already has, so there is no extra privilege to
  steal, but there's also no extra protection beyond your normal account's existing boundary.

## Defense-in-depth ideas if you outgrow this

- Move the ACL `dst`/`users` rule to a dedicated low-privilege Linux account scoped only to
  `~/file-portal`, instead of your everyday login.
- Add a `tailscale serve`-fronted status endpoint with its own auth if you build the richer
  feedback loop mentioned in [`08-roadmap.md`](08-roadmap.md), rather than exposing anything new.
- Turn on Tailscale's [device posture / key expiry](https://tailscale.com/kb/1028/key-expiry)
  settings so a stolen laptop's tailnet access expires automatically.
