# CIRRUS Benchmark Suite

A benchmark suite using Playwright to record and report metrics on realtime performance of the CIRRUS viewer on Grand-Challenge.org

---
[![CI](https://github.com/DIAGNijmegen/rse-cirrus-benchmark-suite/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/DIAGNijmegen/rse-cirrus-benchmark-suite/actions/workflows/ci.yml/badge.svg?branch=main)

## Install

Install via uv:

```shell
uv install
uv run playwright install
```

Perhaps it is still required to install some missing depedencies to run the playwright browser. You can do so via:

```shell
sudo playwright install-deps
```

## Configuration

Benchmark is configured via the environment: use and `.env` file locally to configure things.

| ENV           | TYPE      | Description |
| ------------- | ------------- | ------------- |
| DEBUG | TRUE/FALSE | Allow for an execution with a head for viewing |
| GRAND_CHALLENGE_USERNAME | String | Username to start a session on Grand-Challenge.org |
| GRAND_CHALLENGE_PASSWORD | String | Password to start a session on Grand-Challenge.org |
| SESSION_CREATE_URL | String (url) | Overwrite to configure the session creation URL, defaults to using viewer 'cirrus-staging' |

Note: if the username or password is not provided and the DEBUG is enabled, the suite will prompt the user with a page to login on Grand-Challenge.org.

Example .env:

```
DEBUG=TRUE
GRAND_CHALLENGE_USERNAME="JOHN DOE"
GRAND_CHALLENGE_PASSWORD="PASSWORD1"
SESSION_CREATE_URL="https://grand-challenge.org/viewers/cirrus-core/sessions/create/"
```

## Run

After installing and/or configuring. Run the benchmark suite using:

```shell
uv run python cirrus_benchmark_suite/benchmark.py
```
