# Overview

## Purpose

<why this exists, in the frame's one-idea sentence plus one paragraph>

## Actors

| actor | trusted? | what it may do | what it may never do |
|---|---|---|---|
| <name> | yes/no | <...> | <...> |

## Boundary

<Inside: ... Outside: ... Crossing: request/response/event, and direction.>

## Invariants

1. <must always be true> → `check: <how it is verified>`

## Non-goals

| non-goal | reason |
|---|---|
| <...> | <...> |

## Constraints

<platform, cost, environment, owner decisions — each with its source>

## Success criteria

| criterion | measurement |
|---|---|
| <observable outcome> | <command / query and expected value> |

## Surface inventory

Derived from the live system, not from memory. Every row maps to exactly one
flow or to an explicit out-of-scope reason.

| surface | declared at | flow |
|---|---|---|
| `CLI verb --x` | `cmd/x.go` | FLOW-01 |
| `GET /v1/...` | router table | FLOW-02 |
| `<cron job>` | unit list | FLOW-03 |
