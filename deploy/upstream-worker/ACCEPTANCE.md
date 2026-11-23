# Dedicated worker / gateway deployment acceptance

Prepared 2026-11-23. **Not executed deployment instructions.** Read
[the current resource assessment and approval boundaries](../../docs/ORIGINAL_PHASE_2_READINESS.md)
first. Every install, group change, VM, unit/cgroup, TLS/trust configuration and
network launch below requires separate approval. No genuine provider credential,
original campaign or web enablement is part of these tests.

Use a new acceptance identifier/directory per test series. Retain commands,
versions, source/image hashes, safe responses, cgroup/daemon identity, timestamps,
request IDs, ModelUsage/grant/event/artifact hashes and packet results. Exclude
private environments, keys, raw scoped tokens and terminal/prompt logs from Git
and shared reports. A failed gate stops progression; never substitute weaker
isolation, fake a readiness flag or label an unexecuted step passed.

## 1. Resource and KVM gate — existing WSL, after explicit approval

Phase 2A's 128-MiB paused KVM initialization is now verified; its evidence remains
in ignored validation storage. It does not establish full-guest capacity or worker
isolation. Current preparation: [Phase 2B report](../../docs/ORIGINAL_PHASE_2B_READINESS.md).
Before either disk provisioning or full-guest startup, run the read-only check:

```bash
python3 deploy/upstream-worker/preflight_vm.py
```

Exit 0 requires Windows available RAM >=9 GiB, Windows commit headroom >=8 GiB,
WSL available memory >=8.5 GiB, and both physical Ubuntu-backing volume and Linux
filesystem free space >=90 GiB. These overlapping memory/disk pools are not added.
Missing counters/interop/backing metadata fail closed. `start-vm.sh` invokes the
same gate automatically; passing never substitutes for explicit approval. These
are startup samples, not a reservation or ongoing memory-pressure guarantee.

The assessment lists the exact QEMU package/group and diskless KVM probe commands.
Before installing, rerun Windows `Get-Counter` for Available Bytes, Committed Bytes
and Commit Limit, `Get-PSDrive C,D`, `wsl --list --verbose`, then native Linux `id`,
`free -b`, `df -B1 /`, `ls -l /dev/kvm`, and `command -v qemu-system-x86_64`.
Do not sum Linux memory with Windows memory. Do not start Desktop or stop apps
automatically; measure the operator's intended normal workload.

Require working KVM initialization, the reviewed Windows/WSL headroom floors,
at least approximately 90 GiB actual C: free, and no interference with the native
app. QEMU must run with KVM only. A second WSL distro is not a dedicated guest.

For a separately approved **new blank disk** (does not install an OS):

```bash
umask 077
VM_ROOT=/home/sonusunny/.local/share/reseon-worker-acceptance
test ! -L "$VM_ROOT"
install -d -m 0700 "$VM_ROOT"
test ! -e "$VM_ROOT/worker.qcow2"
qemu-img create -f qcow2 "$VM_ROOT/worker.qcow2" 64G
qemu-img info "$VM_ROOT/worker.qcow2"
```

Stop if the target exists. Select a verified official amd64 Ubuntu Server image
and record URL/checksum at provisioning time. Installing/staging the guest needs
its own approved session or offline media. Do not temporarily grant untrusted
research unrestricted internet, share workstation drives or pass a Desktop socket.

## 2. Native Linux guest and independent daemon

Only **inside the new dedicated guest**, use [README guest preparation](README.md#guest-only-preparation-after-approval):

```bash
uname -r
ps -p 1 -o comm=
findmnt -t 9p,virtiofs,drvfs
sudo apt-get update
sudo apt-get install --no-install-recommends docker.io python3-venv git openssh-server ca-certificates openssl
```

Require a non-Microsoft/non-WSL kernel, PID1 systemd, and no workstation shares.
The empty `findmnt` case may exit nonzero; inspect the result rather than ignoring
unexpected mounts. Review package changes before accepting them. Stop/disable
default docker/docker.socket/containerd **in this blank guest only** if installed;
use the existing `agsci-daemon.service`, private socket/data/exec roots and group.
Do not install/reconfigure Docker in normal WSL or Windows.

Use the README's exact account/directory/install commands for agsci-worker and
the three supplied service/slice files. Keep campaigns=0, agent.env empty and
credentials fake. Stage only a reviewed source archive and pinned agent image.
The earlier published checkpoint 4672bf10ed7d994aedbd87412f22588cb764fce2
includes TLS launcher support but predates the resource preflight. Use the reviewed
Phase 2B follow-up checkpoint containing `preflight_vm.py` and the gated launcher,
not that older archive. Historical hash mappings are in
`docs/GH013_HISTORY_REPAIR.md`. Pin and record the full accepted source archive
before deployment. `git archive`
from the accepted commit avoids `.env`, databases, caches and untracked evidence;
review its listing and SHA-256. Do not claim an older archive includes TLS flags.

Guest startup/identity checks:

```bash
sudo /usr/bin/dockerd --validate --config-file=/etc/agsci-worker/daemon.json
sudo systemd-analyze verify /etc/systemd/system/agsci-research.slice /etc/systemd/system/agsci-daemon.service /etc/systemd/system/agsci-upstream-worker.service
sudo systemctl daemon-reload
sudo systemctl start agsci-daemon.service
export DOCKER_HOST=unix:///run/agsci-docker.sock
docker info --format '{{.Name}} {{.OperatingSystem}} {{.DockerRootDir}} {{.CgroupDriver}} {{.CgroupVersion}}'
docker ps -aq
sudo systemctl show agsci-daemon.service -p MainPID -p ControlGroup -p CPUQuotaPerSecUSec -p MemoryMax -p MemorySwapMax -p TasksMax
```

Pass: independent native daemon, `/var/lib/agsci-docker`, systemd/cgroup2, empty
successful container listing, separate process/socket/exec/data roots. Record
socket owner/mode and daemon config hash. Reject Docker Desktop identity/labels,
default `/var/run/docker.sock`, `/var/lib/docker`, Microsoft kernel or a renamed
Desktop socket. The normal Desktop daemon remains untouched.

## 3. Effective CPU, memory and PID limits

```bash
sudo systemctl start agsci-upstream-worker.service
sudo systemctl show agsci-research.slice -p ControlGroup -p CPUQuotaPerSecUSec -p MemoryMax -p MemorySwapMax -p TasksMax
sudo systemctl show agsci-upstream-worker.service -p MainPID -p ControlGroup
cat /sys/fs/cgroup/agsci.slice/agsci-research.slice/cpu.max
cat /sys/fs/cgroup/agsci.slice/agsci-research.slice/memory.max
cat /sys/fs/cgroup/agsci.slice/agsci-research.slice/memory.swap.max
cat /sys/fs/cgroup/agsci.slice/agsci-research.slice/pids.max
```

Require finite effective values matching 200% CPU, 4 GiB, no swap, 1024 PIDs, and
worker/controller membership below that actual hierarchy. Dockerd's separate
limits are 100%, 768 MiB, no swap and 512 PIDs. Config files alone are insufficient.

The authenticated capability probe runs a uniquely named pinned-image container
with no network, read-only FS, dropped capabilities, host cgroup namespace and
finite limits; it verifies container membership and removal. Record returned
checks and exact image content ID. Independently inspect a harmless test container
while alive using `docker inspect` HostConfig CPU/memory/PIDs and its cgroup files.
Override the image entrypoint with `/bin/sh`; never invoke an agent for resource
testing. Any stress test must have an explicit `timeout 15`, `--cpus=1`,
`--memory=128m --memory-swap=128m --pids-limit=32 --network=none --pull=never`,
and an operator-selected pinned image. Use bounded CPU work, one deliberate OOM
allocation, and at most 40 subprocess attempts, not an unbounded fork bomb.
Record throttling/OOM/PID rejection and verify removal by exact container ID.
No stress or container has been launched by this preparation task.

## 4. Authenticated management and verified TLS

Generate only a fresh **transport** token using README's private-file procedure.
It is not a provider key. For an early credential-free probe, the documented
authenticated SSH tunnel and explicit loopback HTTP client are acceptable lab
tools, but OriginalController requires HTTPS for submission readiness.

For the approved HTTPS stage, create a worker server certificate/key privately
inside the guest, with SAN for the actual tunnel hostname/IP, and copy only its
public CA/certificate to the trusted host. Install the private key owner-only for
agsci-worker. No `verify=False`, `curl -k` or global trust-store change.
An approved guest systemd drop-in can replace only ExecStart:

```ini
[Service]
ExecStart=
ExecStart=/opt/agsci-worker/venv/bin/python -m src.research_platform.upstream_worker --host 127.0.0.1 --port 8801 --tls-cert /etc/agsci-worker/worker.crt --tls-key /etc/agsci-worker/worker.key
```

Use `sudo systemctl edit agsci-upstream-worker.service`, review it, then approved
daemon-reload/restart. This uses the existing launcher and retains controller_lock;
do not replace it with bare `uvicorn --factory`. Connect through SSH loopback
forwarding as in README. From the trusted host:

```python
import ssl, httpx
from dotenv import dotenv_values
from src.research_platform.upstream_execution import UpstreamWorkerClient
config = dotenv_values('/private/acceptance/client.env')  # HTTPS URL + transport token
context = ssl.create_default_context(cafile='/private/acceptance/worker-ca.crt')
with httpx.Client(verify=context, trust_env=False, follow_redirects=False) as transport:
    client = UpstreamWorkerClient(config, client=transport)
    print(client.capabilities())  # Safe check booleans; no tokens
```

Pass: valid TLS hostname/CA and transport token; missing/wrong token=401,
wrong CA/hostname fails TLS, non-loopback plain HTTP rejected, no redirect.
Send the existing bounded `dry_run` request: expect preview only, no Job,
agent process or model request. Actual submit must remain 409 with campaigns off.
Expected real worker: infrastructure_ready=true after accepted checks,
campaigns_enabled=false, ready=false, nested_call_budget_enforced=false.

## 5. Trusted gateway/key boundary and mock TLS fixture

Trusted backend/controller/gateway writers share **one Linux host/local SQLite**.
For acceptance use NEW Linux-native temporary state, not the Windows research DB
or a DrvFs/SMB database. The disposable guest has no host filesystem, ledger or
real-key mount. Verify this from guest root and a privileged test container.

Private real-key loading remains a later authorization. For initial tests inspect
owner/mode/symlink rejection using fake files and the existing loader checks;
never start the production key loader against a real provider with a dummy key.
Require private absolute regular key file, root/current-user owner, mode 0600,
no symlink; escrow separate from ArtifactStore, no raw tokens in DB/events/logs.

After approval, create **test-only** TLS files in a private trusted-host directory:

```bash
umask 077
install -d -m 0700 /home/sonusunny/.local/state/reseon-acceptance-tls
cd /home/sonusunny/.local/state/reseon-acceptance-tls
test ! -e mock.key && test ! -e mock.crt
openssl req -x509 -newkey rsa:2048 -nodes -days 7 -subj '/CN=Reseon mock acceptance' \
  -addext 'subjectAltName=IP:10.0.2.100,IP:127.0.0.1,DNS:localhost' \
  -keyout mock.key -out mock.crt
chmod 600 mock.key
```

The leaf is a local test trust anchor only. Copy the public mock.crt into the
guest/test image using existing CA derivative instructions; never copy mock.key.

For a concrete mock gateway server, run the following from the reviewed repository
on the **trusted** Linux host, in an approved local test session. It imports the
existing tested synthetic seed/response and uses only httpx.MockTransport. It
cannot dispatch to Google; no real key or research .env is loaded. Keep this
fixture separate from the production gateway launcher. A new state directory is
mandatory on the first run; restarting reuses its original ledger/grant.

```python
import asyncio, json, os, stat, sys
from pathlib import Path
import httpx, uvicorn
sys.path.insert(0, 'tests/research_platform')
from test_model_gateway import seed, KEY, MODEL, ANSWER
from src.research_platform.database import Database
from src.research_platform.model_gateway import GatewaySettings, create_gateway_app, issue_grant

root = Path('/home/sonusunny/.local/state/reseon-gateway-acceptance-a')
fresh = not root.exists()
if fresh:
    root.mkdir(mode=0o700, parents=True)
assert not root.is_symlink() and stat.S_IMODE(root.stat().st_mode) == 0o700
db = Database('sqlite:///' + str(root / 'ledger.db'))
if fresh:
    db.migrate()
    run_id = seed(db, max_llm_calls=20, max_input_tokens=120000, max_output_tokens=16000)
    grant_id, token = issue_grant(db, run_id, allowed_models=[MODEL], ttl_seconds=900, max_output_tokens=128)
    fd = os.open(root / 'client.env', os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write('TOKEN=' + token + '\nRUN_ID=' + run_id + '\nMODEL=' + MODEL + '\n')
    (root / 'manifest.json').write_text(json.dumps({'run_id':run_id,'grant_id':grant_id,'fixture':True}))
else:
    assert json.loads((root / 'manifest.json').read_text())['fixture'] is True
async def fake_provider(request):
    assert request.url.host == 'generativelanguage.googleapis.com'
    assert request.headers['x-goog-api-key'] == KEY  # Fixed fake test key only.
    fd = os.open(root / 'dispatch.jsonl', os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'ab') as stream:
        stream.write(b'{"fixture_dispatch":true}\n')
        stream.flush()
        os.fsync(stream.fileno())
    await asyncio.sleep(0.005)
    return httpx.Response(200, json=ANSWER)
upstream = httpx.AsyncClient(transport=httpx.MockTransport(fake_provider), trust_env=False)
app = create_gateway_app(db, GatewaySettings(enabled=True, provider_key=KEY), client=upstream)
uvicorn.run(app, host='127.0.0.1', port=int(os.environ.get('FIXTURE_PORT','8843')),
            ssl_certfile='/home/sonusunny/.local/state/reseon-acceptance-tls/mock.crt',
            ssl_keyfile='/home/sonusunny/.local/state/reseon-acceptance-tls/mock.key',
            access_log=False, proxy_headers=False, limit_concurrency=16)
```

Do not run it against any existing research state. Expired/exhausted fixture runs
remain expired/exhausted; use an explicitly new root for a new series, never reset
the ledger. Review permissions of all private state files before exposing the
guest gateway path. No genuine generation result can be inferred from ANSWER.

## 6. Host-controlled single egress path

Baseline `start-vm.sh` intentionally has **no guest gateway forward**. Confirm its
all-egress-denied baseline first. After separate network approval install host
socat with `sudo apt-get install --no-install-recommends socat`.
The prepared `python -m src.research_platform.gateway_network` output is a
specification, not deployment. Use its exact single guestfwd destination; never
append unrestricted NAT or a host network bridge.

An approved bounded alternative launch, only after a provisioned private disk and
mock gateway exist, is:

```bash
python3 deploy/upstream-worker/preflight_vm.py &&
sudo systemd-run --unit=reseon-worker-vm --collect \
  -p User=sonusunny -p Group=sonusunny -p SupplementaryGroups=kvm \
  -p CPUQuota=400% -p MemoryMax=8G -p MemorySwapMax=0 -p TasksMax=128 \
  -p LimitNOFILE=256 -p LimitCORE=0 -p UMask=0077 \
  /usr/bin/qemu-system-x86_64 -name reseon-original-acceptance -enable-kvm -cpu host \
  -smp 4 -m 6144 \
  -drive file=/home/sonusunny/.local/share/reseon-worker-acceptance/worker.qcow2,if=virtio,format=qcow2 \
  -nic 'user,model=virtio-net-pci,restrict=on,hostfwd=tcp:127.0.0.1:2222-:22,guestfwd=tcp:10.0.2.100:8843-cmd:/usr/bin/socat STDIO TCP4:127.0.0.1:8843' \
  -display none -serial none -monitor none -no-reboot
```

Verify the unit's effective CPU/memory/PID/FD limits and that its QEMU **and spawned
socat children** remain in that cgroup. Bound the mock gateway separately, e.g.
CPUQuota=100%, MemoryMax=512M, MemorySwapMax=0, TasksMax=64, LimitNOFILE=256;
measure whether these limits suffice. No global firewall change is proposed.
Resource-limit failures stop the test, not expand limits silently.

From guest normal user, guest root, an ordinary container and a privileged
`--network=host` test container, verify ONLY 10.0.2.100:8843 is reachable with
correct CA/credential. Use no real key. Test the following with 2-second socket
timeouts, no HTTP/TLS/API payloads to external services:

- Direct provider DNS names and **current** provider IPv4/IPv6 addresses resolved
  separately on the trusted host: TCP 443 must fail. Record the address snapshot.
- Other external IPv4/IPv6 TCP ports 80/443, 1.1.1.1:443, metadata 169.254.169.254:80,
  QEMU host 10.0.2.2 ports 22/8843/2375/2376 and arbitrary alternate gateway ports.
- DNS TCP/UDP to 10.0.2.3 and external resolvers must not yield a usable answer;
  raw IP probes must still fail when DNS is unavailable. Test UDP explicitly,
  not just TCP. Packet capture/rule review must explain refusals/timeouts.
- No accessible host Docker/SSH/API/metadata services beyond the explicit SSH
  ingress and gateway path; no host file shares or devices. Guest root attempts
  to alter guest firewall/routes cannot change the external QEMU policy.
- HTTP CONNECT, arbitrary gateway paths, query credentials and cross-run tokens
  cannot turn the gateway into a proxy. Wrong CA/hostname and expired certificates
  fail TLS; valid CA + wrong token fails authentication without a ledger row.

Example raw TCP check, run in each stated context, with the reviewed provider
address list substituted separately (no provider HTTP request):

```python
import socket
for host, port in [('10.0.2.2',8843), ('1.1.1.1',443), ('169.254.169.254',80)]:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
        connection.settimeout(2)
        result = connection.connect_ex((host,port))
        assert result != 0, ('Unexpected egress',host,port)
```

A finite set of failures alone is not proof: record QEMU arguments, host-side
policy ownership, packet observations, all network families/protocols and the
successful single allowed path. No packet test in this section has run yet.
Reference: [QEMU restrict/forward semantics](https://www.qemu.org/docs/master/system/invocation.html).

## 7. Actual HTTP 20/21-call accounting and restart

Use only the synthetic fixture above. Copy its **fake scoped** client.env and
public CA into a private guest test directory, never the real host .env. With
the gateway's 900-second fixture grant still valid, run this in the guest:

```python
from dotenv import dotenv_values
import httpx
config=dotenv_values('/private/acceptance/client.env')
path=f"https://10.0.2.100:8843/runs/{config['RUN_ID']}/v1beta/models/{config['MODEL']}:generateContent"
with httpx.Client(verify='/private/acceptance/mock.crt', trust_env=False, timeout=5) as client:
    for index in range(21):
        response=client.post(path, headers={'x-goog-api-key':config['TOKEN'],
                                          'x-reseon-request-id':f'{index:032x}'},
                             json={'contents':[{'parts':[{'text':'fixture only'}]}],
                                   'generationConfig':{'maxOutputTokens':128}})
        assert response.status_code == (200 if index<20 else 403)
        print(index+1, response.status_code)  # Never print token or body.
```

Pass: exactly 20 ModelUsage rows and 20 mock dispatch lines, 21st HTTP403
`budget_exhausted`, remaining_calls=0, cost null. Audit reserved events must link
request ID ↔ usage ID ↔ grant ID ↔ run. Repeating a request ID returns 409 with no
second row/dispatch. Restart the fixture against the **same** directory, repeat
request 21 and a duplicate ID: still 403/409, still 20 rows/dispatches, no refunds.
After expiry expect 401 instead; do not misclassify that as a 20-call proof.

Use a **new** fixture series for 40 concurrent attempts: ThreadPoolExecutor(10)
and fresh IDs must produce exactly 20 HTTP200 and 20 HTTP403. For independent
gateway-instance validation, restart the same fixture script with FIXTURE_PORT=8844
on the trusted host and alternate loopback clients between 8843 and 8844; both
share only this local ledger and the mock dispatch file. Never publish 8844 to
the guest or create a second egress path. Expect 20 rows/dispatches total.

Run existing named tests for expiry/revocation/run/model binding, controller lease,
gateway disconnect/uncertainty, SSE interruption, concurrency, unknown monetary
cap and historical preservation. They supplement, not replace, actual HTTP/VM
checks. A fresh explicit grant with TTL=1 can validate expiry in a separate
synthetic run; revoke a fresh grant using existing revoke_grant and expect 401
without a new row. Never mutate or delete charged rows to make assertions pass.

## 8. Cancellation, cleanup, recovery, artifacts and sign-off

Campaigns remain off. Use an operator-created **synthetic journal** in a fresh
UUID job directory, labelled fixture, and a harmless bounded sleep container
with an explicitly verified job-owned bind path, never an original CLI. Keep the
worker stopped while creating this isolated fixture. On service restart a
running journal must become cleanup_unverified and fence new submissions.

Stop the worker, verify `populated 0` and a successful empty dedicated Docker
listing, then use the README's exact offline `systemd-run ... upstream_worker
--recover UUID` command outside the research slice. It must mark only this
journal interrupted/cleanup_verified, never resume. Repeat with a remaining
container or populated cgroup: recovery must refuse and preserve uncertainty.
No wildcard rm/prune; only verified fixture-owned container IDs may be removed.
Test lock exclusion while the service runs. An unreachable daemon is not empty.

Controller cancellation/restart/grant interactions use the existing mock HTTP
tests until campaign activation is separately approved. Test lost cancel replies:
grants revoke first; run remains paused with cancel intent and unverified cleanup.
Pause/resume retains deadline and all ModelUsage; no ambiguous submit auto-replay.
These are not claims that a real original campaign cancellation has passed.

For artifact HTTP acceptance, create explicitly labelled fixture final_manifest
and pipeline journal content under a fresh worker UUID. With transport auth,
retrieve only allowlisted names and compare SHA-256/length to private source.
Unknown name, path traversal, symlink, missing auth and oversized content must
fail. Inspect sanitized pipeline events: no token/private log contents. Import
via the existing controller mock completion interface into a new test ledger,
verify content-addressed hashes and lifecycle artifact IDs, and repeat collection
after a simulated disconnect: no new campaign submission or usage refund.
Do not call fixture artifacts scientific results or overwrite actual evidence.

ISSUE-01 acceptance needs native guest/daemon/cgroups/authentication/dry-run and
actual cleanup/restart receipts. ISSUE-02 additionally needs trusted persistence,
mock TLS/packet/ledger acceptance and separately authorized genuine Gemini
free-policy/credential/generation verification. Keep nested enforcement false
until reviewed deployment proof is represented safely; do not edit a boolean
to bypass OriginalController. ISSUE-03 remains disabled until both gates pass.

Rollback: revoke synthetic grants, stop only new fixture/gateway/forwarder units,
verify dedicated cleanup, shut down the guest gracefully via its authenticated
SSH admin session, then stop its QEMU unit if still active. Retain disk, journals,
ledgers and uncertainty. Preserve Desktop, normal WSL, native environments and all
release tags. KVM/package/TLS/data-cutover rollback requires operator review as
described in the readiness report; do not erase state or use apt autoremove.
