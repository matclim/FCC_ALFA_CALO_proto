# Getting a Key4hep environment

Everything in this PoC needs DD4hep, Geant4, ROOT and `ddsim`. Those come from
the Key4hep stack, which is distributed over CVMFS. If `ls /cvmfs` says "No such
file or directory", you have no stack and nothing here will build.

Three ways to fix that, easiest first.

---

## 1. Use lxplus (simplest, if you have a CERN account)

```bash
ssh -X yourname@lxplus.cern.ch
# copy the PoC directory over, e.g.
#   scp -r grainita_poc yourname@lxplus.cern.ch:~/
cd grainita_poc
source build.sh
```

lxplus has CVMFS mounted and runs AlmaLinux 9, which is a supported Key4hep
platform. Nothing else to install. Note your AFS/EOS quota if you start
generating many simulation files.

If you are working on ALFA you will want a CERN account anyway — the e-group
`fcc-ped-detectorconcepts-alfa` and the FCC Indico both need one.

---

## 2. Container with CVMFS inside (best if you have Docker or Podman)

Key4hep publishes images that already contain a CVMFS client. They need
`--privileged` (CVMFS mounts a FUSE filesystem) and one mandatory step inside
the container: running `/mount.sh` to actually mount CVMFS.

```bash
docker run -it --privileged \
  -v "$(pwd)":/work \
  -w /work \
  ghcr.io/key4hep/key4hep-images/alma9-cvmfs:latest \
  /bin/bash

# then, INSIDE the container:
/mount.sh                      # mandatory, mounts /cvmfs
ls /cvmfs/sw.hsf.org/          # should now list key4hep
source build.sh
```

Podman works the same way. Substitute `ubuntu24-cvmfs` or `alma10-cvmfs` if you
prefer a different base.

Caveats worth knowing:

- The first `source` of the Key4hep setup script over a cold CVMFS cache is
  slow — several minutes is normal. It is fast afterwards.
- `--privileged` is a real privilege grant. If that is not acceptable, the
  narrower form is
  `--device /dev/fuse --cap-add SYS_ADMIN --security-opt apparmor:unconfined`.
- These images are built for CI, not for interactive development, so an editor
  or debugger you want may be missing. Build your own image `FROM` one of them
  if that bites.
- Bind-mount your work directory (`-v`) so your build survives the container
  exiting.

---

## 2b. Arch Linux: mount CVMFS on the host, run Key4hep in a container

On Arch these are two separate problems and it is worth keeping them apart.

**Mounting CVMFS on Arch works fine.** The CernVM-FS documentation itself
points at the AUR package (maintained by Frank Siegert and Wainer Vandelli):

```bash
paru -S cvmfs        # or yay, or makepkg from the AUR
```

Arch-specific configuration, which differs from the Debian/RHEL instructions
below:

- **Do not use autofs.** It is unreliable on Arch and the package's own
  post-install message recommends `systemd.automount` instead. Add to
  `/etc/fstab`:

  ```
  sw.hsf.org           /cvmfs/sw.hsf.org           cvmfs noauto,x-systemd.automount,x-systemd.requires=network-online.target,x-systemd.idle-timeout=5min,x-systemd.device-timeout=10 0 0
  sw-nightlies.hsf.org /cvmfs/sw-nightlies.hsf.org cvmfs noauto,x-systemd.automount,x-systemd.requires=network-online.target,x-systemd.idle-timeout=5min,x-systemd.device-timeout=10 0 0
  ```

- Enable FUSE for non-root use in `/etc/fuse.conf`:

  ```
  user_allow_other
  ```

- Write `/etc/cvmfs/default.local` as in section 3 below, then
  `sudo systemctl daemon-reload` and `ls /cvmfs/sw.hsf.org/key4hep/`.

- **If mounts hang, suspect curl.** curl 8.16 introduced a regression that
  deadlocks CVMFS. Fixed in 8.17. On a rolling distro this is the kind of thing
  that bites months later after an unrelated `pacman -Syu`, so it is worth
  remembering the symptom.

**Running the stack natively on Arch is the part that does not work.** Key4hep
is built and distributed per-OS — `setup.sh` reads `/etc/os-release`, works out
a platform string like `x86_64-almalinux9-gcc14.2.0-opt`, and looks for that
directory on CVMFS. There is no Arch flavour, so it will not find one. Arch's
glibc is also far ahead of anything the stack was compiled against.

**So do this instead:** mount CVMFS on the host, and run an AlmaLinux 9
container that bind-mounts it. Apptainer is packaged for Arch and needs no root
at runtime:

```bash
sudo pacman -S apptainer

apptainer shell \
  -B /cvmfs \
  -B "$(pwd)":/work --pwd /work \
  docker://ghcr.io/key4hep/key4hep-images/alma9:latest

# inside the container:
source /cvmfs/sw.hsf.org/key4hep/setup.sh
source build.sh
```

Note this uses the plain `alma9` image, not `alma9-cvmfs` — CVMFS comes from
the host bind mount, so the container needs no CVMFS client, no `--privileged`,
and no `/mount.sh`.

This is the standard way people run HEP software on Arch, and it is genuinely
the nicest of the options in this file: the CVMFS cache lives on your host and
is shared across every container and every project, your files stay where they
are, and you get a correct Alma 9 userspace for the binaries. Cost is about
twenty minutes of setup, once.

If you would rather not install anything on the host, section 2's
`docker --privileged` + `alma9-cvmfs` + `/mount.sh` route works on Arch too. It
just re-downloads the CVMFS cache inside each container.

---

## 3. Install the CVMFS client locally (best long term, needs root)

Once done, `/cvmfs/sw.hsf.org` behaves like a normal read-only directory and
`source build.sh` works natively — no container, no ssh.

On Ubuntu/Debian:

```bash
wget https://ecsft.cern.ch/dist/cvmfs/cvmfs-release/cvmfs-release-latest_all.deb
sudo dpkg -i cvmfs-release-latest_all.deb
sudo apt-get update
sudo apt-get install cvmfs
```

On AlmaLinux/RHEL/Fedora, use the equivalent `cvmfs-release-latest.noarch.rpm`
and `dnf install cvmfs`.

Then configure it. Create `/etc/cvmfs/default.local`:

```
CVMFS_REPOSITORIES=sw.hsf.org,sw-nightlies.hsf.org,unpacked.cern.ch
CVMFS_CLIENT_PROFILE=single
CVMFS_QUOTA_LIMIT=20000
```

`CVMFS_QUOTA_LIMIT` is the local cache size in MB. 20 GB is comfortable for a
Key4hep stack; 10 GB is workable but you will re-fetch more often.

You also need a proxy setting. If you are not behind a site squid:

```
CVMFS_HTTP_PROXY=DIRECT
```

Direct access works but is slower and less polite to the servers. If your
institute runs a squid, use it instead.

Then:

```bash
sudo cvmfs_config setup
sudo cvmfs_config probe          # should report OK for each repository
ls /cvmfs/sw.hsf.org/key4hep/
```

If `probe` fails, `cvmfs_config chksetup` prints what is wrong. The usual
culprits are a missing `CVMFS_HTTP_PROXY` line or a firewall blocking outbound
HTTP to the Stratum-1 servers.

---

## What about building the stack from source?

You can — `key4hep-spack` supports it — but a full Spack build of Key4hep is
many hours to a day of compilation and tens of GB. It is the right answer if
you need a stack on a cluster with no CVMFS and no containers, and the wrong
answer for a proof of concept. Do not start here.

---

## Release vs nightlies

`build.sh` prefers `sw-nightlies.hsf.org` and falls back to `sw.hsf.org`
(stable releases). The upstream `qwert2333/DD4hep_Grainita` repo pins the
nightlies at `-r 2026-07-03`, so if you are trying to reproduce that work, use:

```bash
source /cvmfs/sw-nightlies.hsf.org/key4hep/setup.sh -r 2026-07-03
```

before running `build.sh`, which will then detect the already-configured
environment and skip its own sourcing. Pinning matters: the nightlies move, and
a geometry that built last month may not build against today's.
