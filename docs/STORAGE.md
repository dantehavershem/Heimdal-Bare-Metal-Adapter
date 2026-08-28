# External storage

Recommended VM disk: 60 GB. Keep large media outside the VM.

Example host layout:

```
/srv/baremetal-adapter/storage/iso
/srv/baremetal-adapter/storage/golden-images
/srv/baremetal-adapter/storage/drivers
/srv/baremetal-adapter/storage/output
```

Each directory can be a mount point backed by SMB/NFS. Docker bind-mounts the common storage root into API and worker containers as `/storage`.

Example Windows share:

```
\\FILE01\DeploymentMedia -> /srv/baremetal-adapter/storage/iso
```

Use `scripts/mount-smb.sh` for a simple laboratory mount. In production, configure persistent mounts with systemd mount units or `/etc/fstab` and a protected credentials file.
