# Dedicated original worker: Phase 1 deployment

Status: repository preparation, not an installed or verified VM. Nothing in this
directory is an instruction to enable original campaigns. ISSUE-02 remains open;
ISSUE-03 web launch must continue to return HTTP 409. Do not supply real provider
credentials or set `RESEARCH_UPSTREAM_CAMPAIGNS_ENABLED=1` during Phase 1.

## Boundary and proposed local VM

Run the controller **natively in a disposable Ubuntu Server VM**. Give that guest
its own root filesystem, kernel, Docker daemon, Unix socket, data root and private
job/credential storage. No workstation drives, Docker Desktop socket, clipboard,
USB devices or agent profiles are shared. A second WSL distribution alone is not
this VM boundary. The normal Desktop daemon is not accepted, even through a
renamed socket. Operator attestation still matters; these checks are not a VM
escape or production-security certification.

The proposed free local route is QEMU/KVM under the existing WSL2 Ubuntu, with a
**separate Linux guest**, 4 virtual CPUs, 6 GiB RAM and a private 64 GiB sparse disk.
KVM nested acceleration must first be verified after approved installation/access
changes; `/dev/kvm` existing does not prove it can initialize. Do not fall back
silently to slow software emulation or disable the Windows hypervisor/WSL. An
independent VM on another Linux host is an alternative if nested KVM fails.

The inspected laptop has 18 logical CPUs and about 23.4 GiB visible physical RAM,
but only about 7.1 GiB Windows RAM was free. Prefer at least 9 GiB free before a
6 GiB guest while retaining Windows, WSL and Docker Desktop headroom. Do not stop
other applications or change their allocations automatically. The research slice
below caps the controller plus containers at 2 CPUs, 4 GiB RAM, no swap and 1024
PIDs. The dedicated daemon has separate finite limits. These are lab starting
limits, not evidence that a large original research campaign will fit.

QEMU's `restrict=on` user network blocks guest-to-host and external traffic, with
only explicit loopback SSH forwarding. It is suitable for these credential-free
checks. Guest packages/source/image must be staged **before** this restricted
Phase 1 boot using an approved provisioning session or offline media. Do not add
shared host directories to work around staging. Later provider egress needs its
own ISSUE-02 design and approval.

Sources: [QEMU networking and acceleration](https://www.qemu.org/docs/master/system/invocation.html),
[WSL nested virtualization settings](https://learn.microsoft.com/en-us/windows/wsl/wsl-config),
[systemd resource controls](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html),
[Docker daemon separation](https://docs.docker.com/engine/daemon/).
The full [Hyper-V role is unavailable on Windows Home](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/get-started/Install-Hyper-V).
The Windows Hypervisor Platform API is a different feature; no Windows feature
change is needed for the proposed nested Linux/KVM route.

## Approval required before host work

These commands are a reviewable proposal; **none was executed by this change**.
Inside the existing WSL Ubuntu, approval would permit:

```bash
sudo apt-get update
sudo apt-get install --no-install-recommends qemu-system-x86 qemu-utils
sudo usermod -aG kvm sonusunny
```

Re-enter the Ubuntu login/session to apply the group; do not run `wsl --shutdown`
while Docker/Desktop/native jobs are active. Then verify KVM access and QEMU's
accelerator initialization before creating/booting a guest. Do not `chmod 666`
`/dev/kvm`. If the `kvm` group/package/device differs, stop and inspect instead of
guessing. Guest image download, verification, disk creation and provisioning also
need approval; no existing disk or VM is overwritten. Use an Ubuntu Server 24.04
LTS amd64 guest with cgroup v2/systemd and Python 3.12, a local administrator with
SSH public-key authentication, password/remote-root login disabled, and a serial
console. Select and verify the official image/checksum at provisioning time.

After an approved guest disk exists, the checked-in launcher is explicit:

```bash
bash deploy/upstream-worker/start-vm.sh --start-approved-vm /absolute/private/path/worker.qcow2
```

It does not install packages, create a disk, change permissions or expose the
worker API. If KVM is unavailable it stops. Shut down gracefully inside the
guest, or use QEMU monitor `system_powerdown`; avoid forced kills and disk removal.

## Guest-only preparation after approval

**Do not run the following on the workstation or its normal WSL distribution.**
First confirm the dedicated guest: `uname -r` is not Microsoft/WSL, PID 1 is
systemd, and no Desktop socket/context or workstation mounts are present.

1. Stage the current reviewed **working-tree source**, not merely `git archive
   HEAD` (the current platform code includes uncommitted files). Include `src`,
   `configs`, required `apps` backend packages, examples, these deployment files,
   `pyproject.toml`, `uv.lock`, README and license. Explicitly exclude `.env`, any
   private `*.env`, `.git`, `.venv`, `node_modules`, build outputs, results and
   `.research-platform`. Review the archive listing before sending it over SSH.
   Record its SHA-256 and extract only into the guest's new
   `/opt/agsci-worker/repository`. This VM copy is necessary isolation, not a
   second workstation checkout. Do not share the live source directory by mount.
2. Install guest-only Docker Engine/CLI, Python/venv, Git and the locked project
   dependencies from reviewed package sources. For example, in the blank Ubuntu
   guest: `sudo apt-get update` and
   `sudo apt-get install --no-install-recommends docker.io python3-venv git`.
   A separately staged/reviewed uv executable can install the checked-in lockfile:

   ```bash
   cd /opt/agsci-worker/repository
   sudo env UV_PROJECT_ENVIRONMENT=/opt/agsci-worker/venv uv sync --locked --extra platform --no-dev
   ```

   This is not a request to reinstall any host Python or Docker component.
3. In this **new guest only**, stop/disable the default `docker.service`,
   `docker.socket` and `containerd.service` if package installation enabled them.
   The custom dockerd manages its own containerd under its private exec root;
   do not connect it to Desktop or the default host containerd socket.
4. Create the private guest service account and directories, then stage files:

   ```bash
   sudo useradd --system --user-group --home-dir /var/lib/agsci-worker --shell /usr/sbin/nologin agsci-worker
   sudo install -d -m 0750 -o root -g agsci-worker /etc/agsci-worker
   sudo install -d -m 0700 -o agsci-worker -g agsci-worker /var/lib/agsci-worker/jobs
   sudo install -d -m 0700 -o root -g root /var/lib/agsci-docker
   sudo install -m 0644 deploy/upstream-worker/daemon.json /etc/agsci-worker/daemon.json
   sudo install -m 0600 deploy/upstream-worker/worker.env.example /etc/agsci-worker/worker.env
   sudo install -m 0600 -o agsci-worker -g agsci-worker deploy/upstream-worker/agent.env.example /etc/agsci-worker/agent.env
   sudo install -m 0644 deploy/upstream-worker/agsci-research.slice deploy/upstream-worker/agsci-daemon.service deploy/upstream-worker/agsci-upstream-worker.service /etc/systemd/system/
   ```

   Use fresh paths; if an account/file already exists, inspect and preserve it
   rather than overwriting it with this example. Keep the repository and venv
   administrator-owned and readable/executable by the service, not writable by it.
5. Generate a transport token (not a provider key) privately in `worker.env`:

   ```bash
   sudo /opt/agsci-worker/venv/bin/python - <<'PY'
   import secrets
   from pathlib import Path
   p = Path('/etc/agsci-worker/worker.env')
   text = p.read_text()
   assert 'RESEARCH_UPSTREAM_WORKER_TOKEN=\n' in text, 'Existing token: preserve it'
   p.write_text(text.replace('RESEARCH_UPSTREAM_WORKER_TOKEN=\n', 'RESEARCH_UPSTREAM_WORKER_TOKEN=' + secrets.token_urlsafe(48) + '\n'))
   p.chmod(0o600)
   PY
   ```

   Keep `agent.env` empty and campaigns disabled. Copy only the transport token
   to a separate private client configuration using the administrator's secure
   channel; never commit, print, paste into research input or log either secret.
6. Preload a reviewed agent image into **this daemon**, not Desktop. Inspect the
   source image's immutable ID, then use `docker save`, SSH transfer and
   `DOCKER_HOST=unix:///run/agsci-docker.sock docker load` in an approved staging
   session. Only the image tar is transferred; no socket/credential mount is
   provided. Do not let a research request pull or build images. Record the
   loaded content ID and preferably use an immutable digest in worker.env.

## Startup and authenticated capability check

In the guest, after file review and image staging:

```bash
sudo /usr/bin/dockerd --validate --config-file=/etc/agsci-worker/daemon.json
sudo systemd-analyze verify /etc/systemd/system/agsci-research.slice /etc/systemd/system/agsci-daemon.service /etc/systemd/system/agsci-upstream-worker.service
sudo systemctl daemon-reload
sudo systemctl start agsci-daemon.service
# Preload the image now if not already staged.
sudo systemctl start agsci-upstream-worker.service
```

The slice name has hierarchical semantics: `agsci-research.slice` lives at
`/sys/fs/cgroup/agsci.slice/agsci-research.slice`, not directly under the root.
The service controller and Docker containers must both appear below that path.
Dockerd itself has finite service limits outside the research slice, so an empty
research slice can be verified while the daemon stays available for inspection.

Open a local authenticated SSH tunnel (example from WSL):

```bash
ssh -N -p 2222 -o ExitOnForwardFailure=yes -L 127.0.0.1:8801:127.0.0.1:8801 VM_ADMIN@127.0.0.1
```

Use `client.env.example` as a separate private configuration (mode 0600) in the
caller environment, with only this guest's transport token. Use the existing
`UpstreamWorkerClient` to read capabilities; keep secret values out of arguments:

```python
from dotenv import dotenv_values
from src.research_platform.upstream_execution import UpstreamWorkerClient
client = UpstreamWorkerClient(dotenv_values('/private/path/client.env'))
try:
    print(client.capabilities())
finally:
    client.close()
```

Without a token, `/v1/capabilities` returns 401. Direct non-loopback HTTP is
rejected by the client. For a remote deployment without SSH, configure a verified
HTTPS endpoint; do not expose plain HTTP or Docker TCP. Phase 1's expected
result is `infrastructure_ready=true`, `campaigns_enabled=false`, `ready=false`
and `nested_call_budget_enforced=false`. A missing Gemini key is expected and
does not prevent credential-free infrastructure probes. Presence checks never
prove provider credentials valid; no real provider request is authorized here.

`POST /v1/dry-run` previews the existing strict request with `runtime_seconds=60`,
one cycle/evaluation and `--dry-run`; it does **not** execute the original CLI or
create a job. The existing request schema includes `nested_budget_policy` and
`nested_budget_approved` acknowledgement fields. Supplying them for an
execution-disabled preview does not approve a real campaign or solve ISSUE-02.
The execution routes still return 409 while campaigns are disabled. Every
capability probe is networkless, credential-free and time/CPU/memory/PID-bounded,
and its uniquely named container's removal is verified. Never accept a nonempty
dedicated daemon as ready or run cleanup against Desktop.

## Shutdown, cleanup and recovery

Stop the worker before the daemon; preserve job data and private logs:

```bash
sudo systemctl stop agsci-upstream-worker.service
cat /sys/fs/cgroup/agsci.slice/agsci-research.slice/cgroup.events
DOCKER_HOST=unix:///run/agsci-docker.sock docker ps -aq
```

`populated 0` and an empty successful Docker listing are required. An unreachable
daemon is **not** proof of cleanup. No worker recovery command automatically
deletes containers, kills processes, refunds budget or resumes research. If a
listing is nonempty, inspect exact container IDs and bind mounts privately and
remove only verified job-owned containers after explicit operator review. Unknown
ownership, corrupted journals or unbounded processes require investigation or
rebuilding the disposable guest; never use blanket `docker rm` or `docker prune`.

An interrupted job becomes `cleanup_unverified` on service restart and fences all
new jobs/probes. Main-process locking prevents a second controller or offline
recovery while the first controller holds the private root. Once the service is
stopped, cgroup empty and the dedicated daemon verified empty, an administrator
can explicitly reconcile **one** journal without executing anything:

```bash
sudo systemd-run --unit=agsci-offline-recovery --wait --collect --pipe --uid=agsci-worker --gid=agsci-worker \
  -p EnvironmentFile=/etc/agsci-worker/worker.env -p WorkingDirectory=/opt/agsci-worker/repository \
  /opt/agsci-worker/venv/bin/python -m src.research_platform.upstream_worker --recover CANONICAL_RUN_UUID
```

Recovery runs outside the research slice, verifies policy/daemon/cgroup again,
marks only the selected journal `interrupted` with verified cleanup, and never
resumes it. Other interrupted journals stay fenced. An invalid journal is not
silently ignored. If a capability-probe container remains, capability checks
refuse another probe until the dedicated daemon has been explicitly cleared.

After cleanup verification, stop `agsci-daemon.service` and shut down the guest
gracefully when not needed. A boot/service restart is not a cleanup receipt.
Private `attempt-*.log` files may contain prompts/provider responses; do not
publish them. API diagnostics expose only check booleans and classified errors;
access logging is disabled and core dumps are disabled in the service units.
