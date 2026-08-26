# PyFFmpegCore public-beta launch runbook

This is the maintainer's source-backed distribution plan for the first public
beta. It optimizes for qualified installs, completed workflows, useful bug
reports, and repeatable proof. It does not authorize spam, coordinated voting,
or claims that the release evidence cannot support.

Channel rules were checked on 2026-08-25. Recheck them immediately before
posting; community policies change. The supporting research is in
[`research_pyffmpegcore_launch/`](research_pyffmpegcore_launch/).

## Hard launch gate

Do not announce a PyPI release until every item below is true:

- [x] `https://pypi.org/project/pyffmpegcore/` resolves publicly.
- [x] `pipx install "pyffmpegcore==0.2.2"` succeeds in a clean environment.
- [x] `pyffmpegcore doctor` and `pyffmpegcore smoke-test` pass after that install.
- [x] The signed `v0.2.2` tag and matching GitHub Release are public.
- [x] The release page exposes checksums, compatibility evidence, and PyPI
  attestations.
- [x] Linux, macOS, and Windows exact-artifact release jobs are green.
- [x] The real terminal demo uses the public artifact rather than the checkout.
- [x] Every link and command in the selected announcement copy is rechecked.

Until then, the repository may be described only as a **source beta**, using
the immutable source-install command already published in the README.

## One story, one reproducible proof

Lead with the operational problem, not a feature inventory:

> PyFFmpegCore is an open-source FFmpeg task runner that checks local
> capabilities before mutation, shows the exact argument plan, runs maintained
> workflows, and records a privacy-redacted receipt.

Then let readers challenge that statement without personal media:

```bash
pipx install "pyffmpegcore==0.2.2"
pyffmpegcore doctor
pyffmpegcore smoke-test
```

The boundary belongs beside the promise: FFmpeg and FFprobe are system
dependencies. PyFFmpegCore is not a hosted transcoder, hostile-media sandbox,
arbitrary filter-graph DSL, packet/frame API, or codec implementation.

Use these source-of-truth links in every announcement:

- repository: <https://github.com/OthmaneBlial/pyffmpegcore>
- five-minute proof: <https://othmaneblial.github.io/pyffmpegcore/quickstart/>
- measured fixture evidence: <https://othmaneblial.github.io/pyffmpegcore/evidence/>
- compatibility: <https://othmaneblial.github.io/pyffmpegcore/COMPATIBILITY/>
- release: `https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.2.2`
- package: `https://pypi.org/project/pyffmpegcore/0.2.2/`

## Release-day order

| Order | Channel | Why it fits | Readiness rule |
| --- | --- | --- | --- |
| 1 | `python-announce-list` | Official Python announcement surface | Real package, tag, and release must be public |
| 2 | r/ffmpeg project thread | Most focused FFmpeg showcase surface | Comment only in the dedicated pinned thread |
| 3 | r/Python Showcase Thread | Python feedback without a standalone promo post | Use the current monthly thread and required headings |
| 4 | r/madeinpython | Detailed standalone Python project showcase | Provide a substantial technical description |
| 5 | DEV Community | Durable technical walkthrough | Article must stand alone and disclose AI assistance |

Product Hunt is a secondary early-adopter surface, not a technical proof gate.
Show HN and Lobsters are conditional on genuine prior participation. GitHub
Marketplace is a later, high-intent discovery channel after the Action's
repository boundary passes the Marketplace release flow.

### 1. Python announce message

The official
[`python-announce-list`](https://mail.python.org/mailman/listinfo/python-announce-list)
exists for Python-related announcements. Posting requires a python.org account.

**Subject**

```text
[ANN] PyFFmpegCore 0.2.2 beta - preflight, plans, and receipts for FFmpeg
```

**Body draft — maintainer must verify and personalize before sending**

```text
I maintain PyFFmpegCore, and version 0.2.2 is its public beta.

PyFFmpegCore is an MIT-licensed Python library and CLI for maintained FFmpeg
workflows. It checks the installed FFmpeg capabilities before mutation, exposes
the exact argument plan, applies explicit overwrite/timeout/cancellation policy,
and can emit a privacy-redacted run receipt.

Try the no-personal-media proof:

    pipx install "pyffmpegcore==0.2.2"
    pyffmpegcore doctor
    pyffmpegcore smoke-test

Python 3.10-3.14 is tested. FFmpeg and FFprobe remain explicit system
dependencies. This beta is not a hosted transcoder, arbitrary filter-graph DSL,
or packet/frame API.

Source: https://github.com/OthmaneBlial/pyffmpegcore
Quickstart: https://othmaneblial.github.io/pyffmpegcore/quickstart/
Release: https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.2.2
Compatibility: https://othmaneblial.github.io/pyffmpegcore/COMPATIBILITY/

Feedback on clean installation, capability diagnostics, and receipt fields is
especially useful.
```

### 2. r/ffmpeg project-thread entry

The subreddit directs project promotion to its dedicated
[`My FFmpeg app or Service`](https://www.reddit.com/r/ffmpeg/comments/1tjk08g/my_ffmpeg_app_or_service/)
thread. Do not create a separate promotional post.

```text
Title: PyFFmpegCore
First release: 2026-08-26
URL: https://github.com/OthmaneBlial/pyffmpegcore
Type: Open-source Python library and CLI
Description: PyFFmpegCore is a local FFmpeg task runner that checks the actual
FFmpeg build before mutation, exposes the exact argument plan, applies explicit
execution policy, probes outputs, and emits privacy-redacted receipts. The beta
ships maintained workflows for web video, exact-size compression, audio,
subtitles, thumbnails, batches, and typed pipelines. A synthetic smoke test lets
readers verify the full path without uploading or supplying personal media.
FFmpeg and FFprobe remain system dependencies.
Showcase: https://othmaneblial.github.io/pyffmpegcore/evidence/
Technical FFmpeg details: Argument-vector execution, capability preflight,
ffprobe validation, progress parsing, and typed plans over local FFmpeg.
License: MIT
Pricing: Free
Organization: Othmane Blial - maintainer
```

### 3. r/Python Showcase Thread

Current r/Python rules route showcases into the monthly Showcase Thread rather
than standalone submissions. Locate the current thread on posting day.

```text
PyFFmpegCore 0.2.2 beta - inspect an FFmpeg plan before it writes, then keep a receipt

I built and maintain PyFFmpegCore.

What My Project Does

PyFFmpegCore is a Python library and CLI for maintained FFmpeg workflows. It
preflights the local FFmpeg capabilities, renders the deterministic argument
plan, executes with explicit policy, validates the output, and can save a
privacy-redacted receipt. `doctor` plus `smoke-test` proves the path using only
synthetic media.

Target Audience

Python developers maintaining media scripts, repeatable local jobs, or CI
pipelines. Version 0.2.2 is a beta; FFmpeg and FFprobe must be installed
separately.

Comparison

Raw FFmpeg remains the best choice when one fully owned command is enough.
PyFFmpegCore adds a typed operational layer: capability preflight, reviewable
plans, overwrite/timeout/cancellation policy, output probing, batches/pipelines,
and redacted receipts. It is not a graph-builder or frame-processing library.

Source: https://github.com/OthmaneBlial/pyffmpegcore
Five-minute proof: https://othmaneblial.github.io/pyffmpegcore/quickstart/

Would the current diagnostics and receipt fields be enough to replace one of
your shell wrappers? Concrete missing fields or failed installs are useful.
```

### 4. r/madeinpython

Use a detailed standalone post only while the community's current
[`made in Python` rules](https://www.reddit.com/r/madeinpython/about/) still
permit project showcases.

**Suggested title**

```text
I built PyFFmpegCore, a Python runner that preflights FFmpeg jobs and records receipts
```

Expand the r/Python body with one `--explain` plan excerpt and one validated
receipt excerpt. Explicitly say that Python owns orchestration while the
installed FFmpeg performs encoding. Do not ask for upvotes or stars.

### 5. DEV walkthrough

Publish a substantive article, not a repository-link announcement. DEV's
[editor guide](https://dev.to/p/editor_guide) permits up to four tags; use only
tags that exist in the editor. Its content policy requires disclosure when AI
helped create the article.

**Suggested title**

```text
How PyFFmpegCore turns FFmpeg jobs into reviewable plans and receipts
```

Recommended structure:

1. one fragile shell-command failure mode;
2. preflight, plan, run, probe, and receipt as one lifecycle;
3. the generated-fixture demo with exact commands and output;
4. why argument vectors, cleanup policy, and failure categories matter;
5. comparison with raw FFmpeg, graph builders, and PyAV;
6. beta limits and system dependencies;
7. one precise request for clean-install and workflow feedback.

## Conditional channels

### Show HN

Use only if the maintainer already satisfies the current
[Show HN participation restriction](https://news.ycombinator.com/showlim). The
submission must be something readers can run, the title must start `Show HN`,
and the author must remain available for discussion. Never coordinate votes or
comments.

Suggested title:

```text
Show HN: PyFFmpegCore - preflight, deterministic plans, and receipts for FFmpeg
```

HN currently forbids generated or AI-edited comments. This runbook therefore
does not provide a body draft: the maintainer must write the opening comment in
their own words, following the [Show HN guidelines](https://news.ycombinator.com/showhn.html).

### Product Hunt

Use a personal maker account, identify the beta and FFmpeg dependency, and ask
for technical trials or comments—never upvotes. The official launch guide
allows the maker to post their own product.

- name: `PyFFmpegCore`
- tagline: `Inspect FFmpeg workflows before running them, then keep the receipt`
- primary URL: <https://othmaneblial.github.io/pyffmpegcore/quickstart/>
- maker comment: real motivation, reproduced result, beta limits, and one
  feedback question

### Lobsters

Use only from a genuinely participating invited account whose submissions and
comments comply with the community's self-promotion ratio. Do not seek an
invitation just to launch. The [Lobsters guidelines](https://lobste.rs/about)
are the readiness gate.

### GitHub Marketplace

Treat the Action listing as durable CI discovery after the signed release. Use
GitHub's
[Marketplace publication flow](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace)
to validate the root `action.yml`. If the broad package repository makes the
Action boundary confusing or ineligible, move the Action into a focused
repository before listing it.

## Channels not to use for a cold launch

- Discussions on Python.org: no general project-announcement category and
  blatant self-promotion is removable/bannable.
- FFmpeg mailing lists and IRC: support and FFmpeg-development scopes exclude
  announcements for third-party wrappers.
- Stack Overflow and Super User: answer a real question completely and disclose
  affiliation when a project link is directly relevant; never seed launch Q&A.
- r/selfhosted: the local CLI beta is not a self-hosted service.
- Python Weekly: potential editorial discovery, but no documented public
  project-submission route was found. Do not invent one or promise coverage.

## Publication log

An unchecked draft is not distribution. Record only visibly public results:

| Channel | Public URL | Published UTC | Release | Exact copy archived | Technical feedback / issue |
| --- | --- | --- | --- | --- | --- |
| `python-announce-list` | — | — | — | — | — |
| r/ffmpeg project thread | — | — | — | — | — |
| r/Python Showcase Thread | — | — | — | — | — |
| r/madeinpython | — | — | — | — | — |
| DEV | — | — | — | — | — |

Track qualified outcomes separately from reach:

- clean public installs that reached `smoke-test: PASS`;
- completed real workflows and reused recipes;
- Action runs that produced downloadable receipt bundles;
- specific install, diagnostic, or compatibility failures;
- external issue/PR authors and repeat contributors;
- referrers, stars, and forks as secondary discovery signals.

The P5 distribution item in `ROADMAP.md` is complete only when at least one
real release post is public, recorded above, and still points to a working
artifact. Preparing this file alone does not complete it.
