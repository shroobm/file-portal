# 02 — Tailscale Setup

Everything else in this repo assumes both machines are already on the same tailnet with Tailscale
SSH enabled. Do this first.

## 1. Install Tailscale on both machines

- **Windows 10**: install from the [Tailscale website](https://tailscale.com/download) or
  `winget install tailscale.tailscale`. Sign in with your account when prompted.
- **Linux**: `curl -fsSL https://tailscale.com/install.sh | sh`, then `sudo tailscale up`.
  - Yes, bringing the Tailscale interface up itself requires `sudo` once, the same as any other
    network interface on Linux. That's a one-time admin action, separate from the "no sudo for
    file transfers" goal this project is about — after `tailscaled` is running, every file
    transfer and every allocator action runs as your normal user.

## 2. Confirm both devices see each other

On either machine:

```bash
tailscale status
```

You should see both devices listed with their tailnet IPs (`100.x.y.z`) and MagicDNS names
(e.g. `mybox.tailnet-name.ts.net`). Note the Linux box's MagicDNS name — you'll use it everywhere
instead of an IP.

## 3. Enable Tailscale SSH

Tailscale SSH replaces OpenSSH's own auth with tailnet-identity-based auth, so there's no key
management and no password prompt.

On the **Linux box**:

```bash
sudo tailscale up --ssh
```

This tells `tailscaled` to run its own SSH server on port 22 (or alongside your existing `sshd` —
Tailscale SSH listens only on the `tailscale0` interface, so it doesn't conflict with a regular
SSH server bound to your LAN interface).

## 4. Set the ACL to allow your Windows device to SSH in as yourself

In the [Tailscale admin console](https://login.tailscale.com/admin/acls), add an SSH rule. Example
(adjust user/host names to match your tailnet):

```json
{
  "ssh": [
    {
      "action": "accept",
      "src":    ["autogroup:member"],
      "dst":    ["tag:home-server"],
      "users":  ["autogroup:nonroot", "you"]
    }
  ]
}
```

Key points:
- `"users"` should **not** include `root` — restricting it to `autogroup:nonroot`/your own
  username is what enforces the "no sudo" guarantee at the policy level, not just by convention.
- Tag the Linux box (`tag:home-server` above) via `tailscale up --advertise-tags=tag:home-server`
  so the ACL rule is specific to it.

## 5. Test it from Windows

```powershell
tailscale ssh you@mybox
```

You should land in a shell with no password/key prompt. If this works, the hard part is done —
everything the widget does is built on top of this exact command.

## 6. No extra tools needed on either end

The widget streams each file straight through
`tailscale ssh <user>@<host> "mkdir -p … && cat > …"`, so the Linux box only needs coreutils
(`mkdir`, `cat`) — present on any distro — and the Windows side only needs the `tailscale` CLI it
already has. (Earlier revisions required `rsync` on the Linux box; that dependency is gone — see
`windows-widget/src-tauri/src/transfer.rs` for the rationale.)

## Next

[`03-windows-widget.md`](03-windows-widget.md) — what the widget does with this SSH connection.
