# Python-community launch channels for PyFFmpegCore

Research checked **2026-08-25**. Web discovery was limited to five searches;
all rule claims below are grounded in pages operated by the community or
publisher being described.

## Recommendation

1. **Post to `python-announce-list` when the real beta artifact is public.** It
   is the clearest Python-specific release channel: its stated purpose is
   Python announcements, and its current archive contains first-public-beta
   announcements from project authors.
2. **Use r/Python's current monthly Showcase Thread, not a standalone post.**
   The current rules explicitly prohibit standalone showcase posts and redirect
   them to the monthly thread or a daily thread.
3. **Use r/madeinpython for a detailed standalone showcase.** Its rules are
   purpose-built for things made in Python and explicitly invite creators to
   share them.
4. **Treat Python Weekly as earned editorial coverage, not a self-posting
   channel.** It curates an "Interesting Projects, Tools, and Libraries"
   section, but its current public site and sitemap expose no project-submission
   form or self-promotion rules.
5. **Do not cold-launch on Discussions on Python.org.** Its current guidelines
   say blatant self-promotion is removed, and its category list has no general
   project-announcement category.

## Release gate and the one use case to lead with

The best reproducible launch demonstration is `doctor` followed by
`smoke-test`. It needs no checkout and no personal media: the smoke test creates
synthetic media, runs a complete transform, probes the result, and cleans up.
It also exposes the important boundary honestly: Python 3.10-3.14 is supported,
while `ffmpeg` and `ffprobe` are explicit system dependencies.

Until a public PyPI artifact has passed the project's cross-platform install
gate, use the immutable source install already documented by the project and
call it a **source beta**, not a PyPI release:

```bash
pipx install git+https://github.com/OthmaneBlial/pyffmpegcore.git@2c1405a5a3f96b5fa30e713e51bfa61b5aa84834
pyffmpegcore doctor
pyffmpegcore smoke-test
```

The documented representative success path is:

```text
Smoke test: PASS
Synthetic input: mpeg4 320x180
Verified thumbnail: 160x90
Artifacts: cleaned up
```

At the actual public-beta launch, replace the Git install with the exact public
version only after it works from a clean environment, for example:

```bash
pipx install pyffmpegcore==0.2.0
pyffmpegcore doctor
pyffmpegcore smoke-test
```

Do not generalize the repository's dated fixture measurements into claims about
arbitrary user media. The defensible promise is that a reader can diagnose the
local FFmpeg stack and run a synthetic end-to-end proof without supplying a
file.

Project proof links:

- Five-minute proof: <https://othmaneblial.github.io/pyffmpegcore/quickstart/>
- Measured fixtures and receipts: <https://othmaneblial.github.io/pyffmpegcore/evidence/>
- Source: <https://github.com/OthmaneBlial/pyffmpegcore>

## Channel cards

### 1. Python-announce-list — best Python-specific release announcement

- **Official pages:** [list information](https://mail.python.org/mailman/listinfo/python-announce-list),
  [current archive](https://mail.python.org/archives/list/python-announce-list@python.org/),
  and a [current first-public-beta precedent](https://mail.python.org/archives/list/python-announce-list@python.org/thread/EPVVT6BLD4ZDF7ZUDG3JGJVZJONNDPUO/).
- **Is self-promotion allowed?** Yes, when it is an actual Python-related
  announcement. The list describes itself as an "Announcement-only list for the
  Python programming language." The August 20, 2026 archive entry is written by
  a maintainer announcing their own first public beta, with website, GitHub, and
  release links.
- **Access:** posting a new thread requires signing in with a python.org
  account. The list is also mirrored to the moderated
  `comp.lang.python.announce` Usenet group.
- **Title requirement:** no formal title template is published on the list-info
  page. `[ANN]` is a strong current convention, not a universal requirement.
  Recommended subject:
  `[ANN] PyFFmpegCore 0.2.0 beta - preflight, plans, and receipts for FFmpeg`.
- **Disclosure:** no separate disclosure syntax is published. State plainly in
  the first sentence that this is the first public beta of a project you
  maintain. Include the exact version, beta/API-stability status, MIT license,
  supported Python versions, explicit FFmpeg/FFprobe dependency, install
  command, source/docs/release links, and a focused request for installation or
  workflow feedback.
- **Best factual angle:** give the three-command `pipx install` / `doctor` /
  `smoke-test` path. It is more suitable for an announcement list than a long
  product story and lets readers verify the release immediately.
- **Do not post yet if:** the PyPI URL, tagged release, or clean install has not
  succeeded. In that case either wait or label the announcement as an immutable
  source beta and use the full Git SHA.

### 2. r/Python monthly Showcase Thread — release-week feedback

- **Official pages:** [current r/Python rules](https://www.reddit.com/r/Python/about/)
  and the [current monthly Showcase Thread](https://www.reddit.com/r/Python/comments/1vfemi1/showcase_thread/).
- **Is self-promotion allowed?** Yes, but currently **only inside the monthly
  Showcase Thread or a suitable daily thread**. Rule 1 says standalone showcase
  posts are no longer allowed. The current AutoModerator thread says to put all
  code, projects, and showcases there and that it recycles monthly.
- **Title requirement:** a thread comment has no submission title. Begin the
  comment with a descriptive first line such as
  `PyFFmpegCore 0.2.0 beta - inspect an FFmpeg plan before it writes, then keep a receipt`.
  Do not create a standalone post to obtain a larger title surface.
- **Required content:** write in English; link freely accessible source; explain
  how Python is relevant; and include a real textual description rather than a
  bare link. The rules require showcase sections named **What My Project Does**,
  **Target Audience**, and **Comparison**. Use those headings in the comment as
  the safest interpretation of the rule.
- **Disclosure:** there is no separate sponsor/author tag in the published
  rules. Open with `I built and maintain PyFFmpegCore` so readers do not have to
  infer the relationship. State `beta` and the system FFmpeg dependency.
- **Best factual angle:** show the no-personal-media smoke-test transcript, then
  explain the operational distinction in one paragraph: raw FFmpeg remains the
  right choice for a fully owned command; PyFFmpegCore adds capability
  preflight, deterministic argument plans, execution policy, output probing,
  and redacted receipts.
- **Feedback request:** ask one technical question, such as whether the
  diagnostic and receipt fields are sufficient to replace a local shell
  wrapper. Do not make the comment a star request.

### 3. r/madeinpython — detailed standalone project showcase

- **Official page:** [current community rules](https://www.reddit.com/r/madeinpython/about/).
- **Is self-promotion allowed?** Yes. Rule 1 says a creator's work can be
  anything they desire as long as it is made in Python; Rule 2 requires detailed
  posts.
- **Title requirement:** no mandatory prefix or title formula is published.
  Use a descriptive title, for example:
  `I built PyFFmpegCore, a Python runner that preflights FFmpeg jobs and records receipts`.
- **Disclosure:** no formal disclosure label is published. The first-person
  title and an opening `I built and maintain...` sentence provide clear author
  disclosure. Mark the version as beta and avoid `production-ready`, `safe for
  every file`, or other unbounded claims.
- **Best factual angle:** this audience permits more detail than the r/Python
  megathread. Show the three-command synthetic smoke test, then one short
  planned-vs-run example. Link source, docs, and the dated evidence page.
- **Fit caveat:** explain that the orchestration layer is Python but actual media
  encoding remains delegated to the user's installed FFmpeg/FFprobe. That keeps
  the post aligned with the community's "made in Python" rule without implying
  that PyFFmpegCore implements codecs.

### 4. Python Weekly — editorial target, not a guaranteed launch post

- **Official evidence:** the [August 6, 2026 issue](https://www.pythonweekly.com/p/python-weekly-issue-757-august-6-2026)
  has a recurring **Interesting Projects, Tools, and Libraries** section, and the
  [current sitemap](https://www.pythonweekly.com/sitemap.xml) lists subscription,
  author, and issue pages.
- **Is self-promotion allowed?** No public rule reviewed grants direct project
  posting or supplies a project-submission form. Treat inclusion as editorial
  selection, not as an owned channel.
- **Title/disclosure requirement:** none is publicly documented for project
  pitches. Do not invent an email address or promise coverage. If an editor
  publishes a current submission route, send a short factual tip that identifies
  the maintainer relationship, beta status, exact install, FFmpeg dependency,
  and evidence links.
- **Best factual angle:** `A Python CLI/library whose synthetic smoke test lets
  readers verify FFmpeg discovery, a complete transform, output probing, and
  cleanup without personal media.` This matches the newsletter's concise
  project summaries better than a broad product pitch.

## Channel to avoid for a cold launch

### Discussions on Python.org

- **Official pages:** [Community Guidelines](https://discuss.python.org/guidelines)
  and [current categories](https://discuss.python.org/categories).
- The guidelines say spam or blatant self-promotion will be removed; the fuller
  rule says it is removed "with extreme prejudice" and can lead to suspension
  or a ban. The current categories include Help, Ideas, Packaging, Developer
  Tools, and specialist areas, but no general project showcase or announcement
  category.
- Do not disguise a launch as a Packaging, Python Help, or Developer Tools
  discussion. Use the forum only when there is a genuine category-specific
  technical question that stands without asking readers to adopt
  PyFFmpegCore; privately message `@moderators` first if the boundary is unclear.

## Suggested order and evidence to retain

1. Publish and verify the exact beta artifact from clean Linux, macOS, and
   Windows environments; record the public package and release URLs.
2. Send one concise `python-announce-list` message with the exact version and
   reproducible smoke path.
3. Add a detailed comment to the current r/Python monthly Showcase Thread.
4. Publish the expanded standalone showcase on r/madeinpython without asking
   one community to boost another.
5. Monitor Python Weekly rather than counting it as a completed launch action.

For each actual publication, retain the URL, timestamp, exact release version
or SHA, exact copy, and technical feedback received. A channel is not "launched"
until the post is visibly public and its install command still works.
