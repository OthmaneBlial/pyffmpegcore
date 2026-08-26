# FFmpeg and media-automation launch channels

Checked: 2026-08-25. This review used four web searches and only first-party
community pages, official help/rules pages, and official FFmpeg pages.

## Recommendation at a glance

1. **Release day: r/ffmpeg's pinned “My FFmpeg app or Service” thread.** It is
   the most targeted permitted showcase, but the project must be listed as a
   comment in that thread, not as a separate promotional post.
2. **Release day: r/Python's current monthly Showcase Thread.** PyFFmpegCore is
   a Python library/CLI with enough reusable architecture to fit, but current
   rules redirect showcases into the recurring thread rather than standalone
   posts.
3. **Later: Show HN.** It is a strong developer-tool venue once a public,
   no-signup install works, but Hacker News currently asks new or unfamiliar
   accounts to participate in the community before posting a Show HN.
4. **Do not announce in FFmpeg support channels or Q&A sites.** Use them only to
   solve a real user's concrete problem, within scope, and disclose maintainer
   affiliation wherever PyFFmpegCore is mentioned.

No channel should be used until the public beta artifact installs successfully
and the exact commands in the proposed demo pass from a clean environment.

## Project-showcase venues

### 1. r/ffmpeg — pinned “My FFmpeg app or Service” thread

**Fit:** highest topical relevance; explicitly accepts apps, scripts, libraries,
web apps, and services that use FFmpeg for a significant part of their
functionality.

**Current rules:** projects may be listed in a comment in the pinned thread
“and only here.” The required fields are title, first-release date, URL, type,
a description shorter than 200 words, optional showcase links, technical FFmpeg
details, license, pricing model, and the organization/person behind the project.
Posts must be in English. Incomplete, misleading, or incorrectly formatted
entries may be removed; the moderators invite a draft by modmail when unsure.

**Self-promotion/disclosure:** self-promotion is allowed only through the pinned
thread. The required `Organization` field provides explicit affiliation
disclosure. Use `Organization: Othmane Blial — maintainer` and state that the
project is MIT-licensed and free. Do not create a parallel launch post in the
main feed.

**Suggested angle:** “a local Python/CLI task runner that preflights the actual
FFmpeg build, exposes the deterministic argument plan before execution, refuses
implicit overwrites, and emits a validation-ready receipt.” Include the
synthetic proof below as `Showcase`, and explain that FFmpeg/FFprobe remain
system dependencies and perform all media work locally.

**Official community sources:**

- Pinned project-listing instructions:
  https://www.reddit.com/r/ffmpeg/comments/1tjk08g/my_ffmpeg_app_or_service/
- Current subreddit metadata/sidebar, which directs product/code/service posts
  to that pinned thread:
  https://www.reddit.com/r/ffmpeg/about.json?raw_json=1

### 2. r/Python — current monthly Showcase Thread

**Fit:** strong fit for Python developers who may maintain scripts, CLI jobs, or
CI media workflows.

**Current rules:** standalone showcase posts are currently prohibited. Projects
belong in the monthly Showcase Thread or an appropriate daily thread. The
showcase format still expects a real description and source-code link rather
than a bare promotional URL.

**Self-promotion/disclosure:** the recurring thread explicitly permits authors
to show projects. Open with “I built and maintain PyFFmpegCore” to remove any
ambiguity. Link to the source repository, not only the documentation or a
landing page. Do not frame the comment as a support request.

**Suggested opening line:** `PyFFmpegCore: inspectable FFmpeg plans and receipts for Python, CLI, and CI`

**Official community sources:**

- Current r/Python rules: https://www.reddit.com/r/Python/about/
- Current monthly Showcase Thread:
  https://www.reddit.com/r/Python/comments/1vfemi1/showcase_thread/

### 3. Hacker News — Show HN (conditional, not a cold-account release-day post)

**Fit:** useful for feedback from developers who build CLI tools and automation,
provided the beta can be installed and exercised immediately.

**Current rules:** Show HN is for something the author made that readers can run
or otherwise try. Early-stage work is acceptable, but it must be non-trivial and
ready to use. Avoid signup/email gates, landing-page-only submissions, and
fundraisers. The title must begin with `Show HN`. The author should be present to
answer questions, and must not ask friends to upvote or comment.

**Current launch constraint:** the official temporary restriction page says new
or unfamiliar users should first learn the community and contribute, then post
an occasional Show HN. Therefore, use this only from an account with genuine
prior participation; otherwise defer it rather than trying to route around the
restriction.

**Self-promotion/disclosure:** Show HN is inherently first-party, but the post
should still say “I built PyFFmpegCore” and explain why. Link directly to the
repository/quickstart where the public version-pinned install is visible. Do not
ask for stars, votes, or coordinated comments.

**Suggested title:** `Show HN: PyFFmpegCore – preflight, explain, run, and receipt for FFmpeg jobs`

**Official sources:**

- Show HN rules: https://news.ycombinator.com/showhn.html
- Current temporary account restriction: https://news.ycombinator.com/showlim
- General Hacker News submission rules:
  https://news.ycombinator.com/newsguidelines.html

## Support-only venues — do not use for a launch announcement

### Official FFmpeg mailing lists and IRC

- `ffmpeg-user` is for general questions about the FFmpeg command-line tools.
  The mailing-list FAQ narrows this to unscripted CLI use/compilation and says
  the lists cannot help with scripts or third-party tools. A PyFFmpegCore launch
  post therefore does not belong there.
- `libav-user` is for FFmpeg library/API questions, not Python wrapper promotion.
- `ffmpeg-devel` and `#ffmpeg-devel` are for development of FFmpeg itself.
  FFmpeg's contact page explicitly says software that uses FFmpeg is off-topic.
- `#ffmpeg` on Libera IRC is for FFmpeg user support/general questions. It is
  publicly logged, so never treat it as a casual promotional chat room.

There is no applicable self-promotion exception on these official pages. If a
real PyFFmpegCore bug is reduced to an FFmpeg CLI question, ask only the reduced
FFmpeg question, include the full command/log, and do not turn the thread into a
product announcement.

**Official sources:**

- FFmpeg channel scopes and mailing-list etiquette:
  https://ffmpeg.org/contact.html
- FFmpeg mailing-list FAQ, including the third-party-tool exclusion:
  https://ffmpeg.org/mailing-list-faq.html

### Super User and Stack Overflow `ffmpeg` Q&A

The FFmpeg site points users to Super User, whose `ffmpeg` tag is specifically
for FFmpeg CLI usage and asks for the actual command plus complete console
output. Its tag guidance routes FFmpeg API questions to Stack Overflow. These
are question-and-answer venues, not launch channels.

Both sites' official promotion policy says overt self-promotion may be flagged
as spam. A maintainer may mention a product in some answers only when it directly
solves the asker's problem, the answer is complete without relying on the link,
and the affiliation is disclosed in the post. Do not seed questions, paste the
same answer repeatedly, or make PyFFmpegCore the answer to every FFmpeg problem.

**Official sources:**

- Super User `ffmpeg` tag scope:
  https://superuser.com/questions/tagged/ffmpeg
- Super User promotion/disclosure rules:
  https://superuser.com/help/promotion
- Stack Overflow promotion/disclosure rules:
  https://stackoverflow.com/help/promotion
- Stack Overflow `ffmpeg` tag:
  https://stackoverflow.com/questions/tagged/ffmpeg

## Adjacent venue to skip for this beta

`r/selfhosted` is not a good primary fit for a local Python task runner. Its
rules require posts to concern self-hosting; non-self-hosted tools are limited
to a Wednesday exception, and projects younger than three months belong only in
the current New Project Megathread. Promoted apps must be production-ready and
documented. A first public beta described as a local CLI would strain that scope,
so do not use it unless a future release gains a genuine self-hosted workflow.

**Official community rules:**
https://www.reddit.com/r/selfhosted/about/rules/

## One reproducible launch use case

Use a **public artifact → synthetic media → explainable plan → validated
receipt** proof. It requires no repository checkout, account, network upload, or
personal media after installation, and it exercises the differentiating contract
instead of merely showing `--help`.

Replace `<version>` with the exact public beta version and run from a clean
environment with FFmpeg and FFprobe already installed:

```bash
pipx install "pyffmpegcore==<version>"
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test --keep-dir pyffmpegcore-demo
pyffmpegcore profile run web/mp4-compatible \
  --input pyffmpegcore-demo/synthetic-input.mp4 \
  --output pyffmpegcore-demo/web.mp4 \
  --explain
pyffmpegcore profile run web/mp4-compatible \
  --input pyffmpegcore-demo/synthetic-input.mp4 \
  --output pyffmpegcore-demo/web.mp4 \
  --receipt pyffmpegcore-demo/web.receipt.json
pyffmpegcore receipt validate pyffmpegcore-demo/web.receipt.json
```

**Local sequence check (2026-08-25):** the commands from `smoke-test` through
`receipt validate` passed from a temporary directory on macOS using the
checkout's virtual environment and Homebrew FFmpeg. The generated input was
MPEG-4 320x180, the planned profile required `libx264`, `aac`, and the MP4
muxer, the output probed as H.264/AAC MP4, and receipt schema 1.0 validated.
This confirms the proposed sequence, not the future public PyPI installation or
other operating systems.

Publish the terminal transcript or a short recording together with the exact
version and platform. The evidence to report is limited and verifiable:

- public version-pinned installation succeeded;
- `doctor` identified the local FFmpeg/FFprobe and capabilities;
- `smoke-test` generated and checked local synthetic media;
- `--explain` exposed the non-mutating plan before the write;
- the executed profile produced a probed output and a schema-valid receipt.

If any command fails on the clean launch machine, report the failure as a beta
limitation and do not advertise that platform as verified. Keep the maintainer
disclosure in every showcase: “I built and maintain PyFFmpegCore.”
