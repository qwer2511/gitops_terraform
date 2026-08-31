# ServerOps Toolkit

Linux server health-check and troubleshooting toolkit for repetitive operations work.

## Features

- System: uptime, load, memory, disk, failed systemd units
- Network: interfaces, default route, DNS, neighbors, ping targets
- Services: `systemctl is-active`
- TCP port checks
- MariaDB/MySQL service, listener and `mysqladmin ping`
- Error-pattern log scanning
- Old IP/reference search under configured paths
- Interactive number-based operations menu
- Text/JSON diagnostic reports
- Read-only v0.1 design

## Requirements

Linux, Python 3.8+, and common Linux utilities (`ip`, `ss`, `systemctl`; `ping`/`mysqladmin` optional).

## Quick start

```bash
cd serverops-toolkit
cp serverops.example.json serverops.json
python3 serverops.py all
```

Interactive menu:

```bash
python3 serverops.py -c serverops.json menu
```

Find references to an old server IP:

```bash
python3 serverops.py -c serverops.json ip-scan 10.112.58.218
```

Create a report:

```bash
python3 serverops.py -c serverops.json report --format text
python3 serverops.py -c serverops.json report --format json -o report.json
```

## Commands

```text
all       Full diagnosis
system    CPU/load, memory, disk, uptime, failed units
network   Interfaces, routing, DNS, ARP/neighbor, ping
services  Configured systemd services
ports     Configured TCP endpoints
mariadb   MariaDB/MySQL checks
logs      Configured log scans
ip-scan   Search files for an old IP/text
menu      Interactive menu
report    Full diagnosis + report file
```

## Configuration

Use `serverops.example.json` as a template. Real `serverops.json` should not be committed because it may contain internal IPs/hostnames.

Do not store database passwords in JSON. `mysqladmin` should use the server's normal client authentication such as socket auth or `~/.my.cnf`.

## Exit codes

- `0`: healthy/no warnings
- `1`: warning found
- `2`: failure found
- `64`: configuration error

## Safety

v0.1 is diagnostic/read-only. It intentionally does not restart services, modify firewall rules, or rewrite configuration files. Production reports can contain sensitive hostnames, IPs, paths or log content, so review them before sharing.

## Roadmap

- Richer terminal UI
- SSH multi-server inventory/checks
- Safe service actions with confirmations/audit log
- Configuration backup/diff
- HTML dashboard/report
