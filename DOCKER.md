# Docker Networking Guide

## The Two-Network Problem

Lyra Secretary and OpenClaw run as **separate Docker Compose stacks**, each with its own default network:

| Stack            | Default Network              | Services              |
|------------------|------------------------------|-----------------------|
| Lyra Secretary   | `lyrasecretaryv01_default`   | `backend`, `redis`    |
| OpenClaw         | `openclaw_default`           | `openclaw-gateway`, `openclaw-cli` |

By default, containers in different networks **cannot reach each other**. The OpenClaw agent needs to call `http://backend:8000` to use the Lyra API, so we need to bridge the two networks.

## Solution: External Network Bridge

### Option A: docker-compose.yml (permanent)

Add the Lyra network as an external network in OpenClaw's `docker-compose.yml`:

**1. Add `networks` to the `openclaw-gateway` service (not `openclaw-cli`):**

```yaml
services:
  openclaw-gateway:
    # ... existing config ...
    networks:
      - default
      - lyrasecretaryv01_default
```

**2. Declare the external network at the root level of the file:**

```yaml
networks:
  default:
  lyrasecretaryv01_default:
    external: true
```

> **Why only the gateway?** The `openclaw-cli` service uses `network_mode: "service:openclaw-gateway"`, which means it shares the gateway's network stack automatically. Adding `networks` to the CLI would conflict with `network_mode`.

**3. Restart OpenClaw:**

```bash
docker-compose up -d
```

### Option B: Manual connect (temporary, lost on restart)

```bash
docker network connect lyrasecretaryv01_default openclaw-openclaw-gateway-1
```

This is useful for testing but will not persist across container restarts.

## Verifying the Connection

**1. Make sure Lyra backend is running:**

```bash
docker-compose -f /path/to/lyra-secretary/docker-compose.yml up -d
```

**2. Verify from inside the OpenClaw container:**

```bash
docker exec openclaw-openclaw-gateway-1 curl -s http://backend:8000/v1/health
```

Expected output:

```json
{"status":"ok","service":"lyra-secretary"}
```

If you get `Could not resolve host: backend`, the network bridge is not connected.

## The `--allow-unconfigured` Flag

When using OpenClaw skills, the agent needs permission to execute tools that aren't part of its core tool definitions. The `--allow-unconfigured` flag (or equivalent config) tells OpenClaw to allow `exec` calls to arbitrary commands, including `curl` calls to the Lyra backend.

Without this flag, OpenClaw may refuse to execute the `curl` commands defined in the Lyra Secretary skill. Refer to the [OpenClaw documentation](https://github.com/openclaw/openclaw) for how to configure this in your setup.

## Network Diagram

```
┌─────────────────────────────────────────────────┐
│              lyrasecretaryv01_default            │
│                                                  │
│  ┌──────────┐    ┌───────┐                       │
│  │ backend  │    │ redis │                       │
│  │ :8000    │    │ :6379 │                       │
│  └──────────┘    └───────┘                       │
│       ▲                                          │
│       │ http://backend:8000                      │
│       │                                          │
│  ┌────┴──────────────┐                           │
│  │ openclaw-gateway  │ ◄── also on               │
│  │ :18789            │    openclaw_default        │
│  └───────────────────┘                           │
└─────────────────────────────────────────────────┘
```

The gateway container has a foot in both networks, enabling it to resolve `backend` via Docker DNS within `lyrasecretaryv01_default`.
