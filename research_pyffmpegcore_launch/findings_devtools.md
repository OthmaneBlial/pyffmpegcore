# Developer-tool and CI launch channels for PyFFmpegCore

Research checked 2026-08-25. The channel rules below come only from the
channel operators' own pages. Suggested copy is deliberately narrower than the
product tagline: it leads with behavior that a reader can reproduce, not with
unbounded claims such as "safe", "production-ready", or "works everywhere".

## Executive recommendation

1. **Release day: Show HN, if the maintainer already has a participating HN
   account.** It is the best fit for a runnable, technically non-trivial beta and
   feedback thread. HN is currently restricting Show HN submissions from people
   who are not yet familiar with the community, so do not create or warm an
   account merely to launch.
2. **Release day or +1 day: one substantive DEV article.** Demonstrate a single
   end-to-end job—preflight, exact plan, run, probed output, redacted receipt—and
   disclose that the author built the project. The article must stand on its own;
   it cannot be a thin repository link.
3. **Release week: Product Hunt, as a secondary beta-feedback surface.** It has
   a broader early-adopter audience than the first two channels. Use a personal
   maker account and invite comments, never upvotes.
4. **After genuine Lobsters participation: Lobsters.** Its computing focus is
   excellent, but the invitation system and less-than-25%-self-promotion rule
   make it unsuitable as a cold acquisition channel.
5. **After deciding the Action packaging boundary: GitHub Marketplace.** This is
   high-intent, durable CI discovery rather than launch-day attention. GitHub's
   official guidance says to use a repository containing the metadata, code, and
   files necessary for the Action, preferably as one unit. PyFFmpegCore currently
   ships its root `action.yml` inside the broader package repository, so verify
   marketplace eligibility in the release UI or split the Action into a focused
   repository before announcing a listing.

Do **not** cold-post the beta on Discussions on Python.org. Its official
guidelines say blatant self-promotion is removed and may cause an immediate ban;
there is no general-purpose launch exception in those guidelines.

## Release gate before any launch post

The current README says PyFFmpegCore is pre-PyPI and gives a full-SHA Git source
install. That is honest, but it raises trial friction. For a "first public beta"
campaign, wait until the public PyPI artifact and documented cross-platform
install gate have actually passed, or label every post **source beta** and use
the immutable Git install verbatim. Never advertise a PyPI install before its
public endpoint succeeds.

Every post should point to a reproducible path and proof:

- repository: <https://github.com/OthmaneBlial/pyffmpegcore>
- five-minute proof: <https://othmaneblial.github.io/pyffmpegcore/quickstart/>
- measured fixtures and receipts: <https://othmaneblial.github.io/pyffmpegcore/evidence/>
- GitHub Action contract: <https://othmaneblial.github.io/pyffmpegcore/github-action/>
- live CI: <https://github.com/OthmaneBlial/pyffmpegcore/actions>

The strongest shared positioning is:

> PyFFmpegCore is an open-source FFmpeg task runner that checks local
> capabilities before mutation, shows the exact argument plan, runs maintained
> workflows, and records a privacy-redacted receipt. The beta includes generated
> fixtures and probes so its web-video, exact-size, and podcast results can be
> reproduced without personal media.

This states what the project does and how to challenge the claim. Mention the
boundary too: FFmpeg/ffprobe are explicit system dependencies; this is not a
hosted transcoder, hostile-media sandbox, arbitrary filter-graph builder, or
frame-processing library.

## Channel cards

### 1. Show HN — highest-priority technical feedback

- **Official pages:** [Show HN Guidelines](https://news.ycombinator.com/showhn.html),
  [current Show HN restriction](https://news.ycombinator.com/showlim), and
  [HN Guidelines](https://news.ycombinator.com/newsguidelines.html).
- **Suggested title:** `Show HN: PyFFmpegCore – preflight, deterministic plans, and receipts for FFmpeg`
- **Primary link:** the GitHub repository, not the docs landing page. The source,
  install command, examples, tests, and limitations are inspectable together.
- **Required/wise disclosure:** say in the opening comment, "I built
  PyFFmpegCore"; explain the fragile-FFmpeg-command problem that motivated it,
  the operational layer it owns, and the beta status. Be present to answer
  questions. HN also currently bans generated or AI-edited comments, so write
  and post the thread in the maintainer's own words.
- **Title/link constraints:** the title must start `Show HN`; submit something
  people can run, not a blog post, signup page, newsletter, landing page, or
  fundraiser. Avoid uppercase, exclamation marks, superlatives, editorialized
  headlines, and gratuitous numbers. Submit the original source.
- **Anti-spam constraints:** the author must have worked on the project and be
  available to discuss it; HN should not be used primarily for promotion. Never
  ask friends or followers to submit, upvote, or comment, and do not delete and
  repost. Feature-only updates are normally not another Show HN.
- **Current access caveat:** HN's temporary restriction asks newcomers to learn
  and contribute to the community before posting an occasional Show HN. Treat
  this as a hard readiness gate, not something to route around.
- **Evidence-led thread shape:** show one 8–12 line terminal transcript from
  `doctor`/`smoke-test`, one planned-vs-run example, the exact evidence link, and
  three known non-goals. End with one focused question: whether CI users find the
  receipt and failure categories sufficient to replace bespoke shell wrappers.

### 2. DEV Community — release-day technical walkthrough

- **Official pages:** [DEV Editor Guide](https://dev.to/p/editor_guide),
  [DEV Terms, Content Policy](https://dev.to/terms#11-content-policy), and
  [DEV Code of Conduct](https://dev.to/code-of-conduct).
- **Suggested title:** `How PyFFmpegCore turns FFmpeg jobs into reviewable plans and receipts`
- **Primary link:** publish the complete walkthrough on DEV. Link or embed the
  repository and evidence inside it; do not post a link-only announcement.
- **Required/wise disclosure:** open with "I built PyFFmpegCore" and mark it as a
  beta. Cite the project evidence. DEV requires disclosure of AI assistance if
  AI helped create the article, and requires clear disclosure of affiliate links
  (none are needed here).
- **Title/link constraints:** DEV sets a normal article `title` field rather than
  a launch-title formula. Use at most four comma-separated tags; a sensible set
  is `python`, `opensource`, `ffmpeg`, `githubactions` if those tags exist in the
  editor. The editor supports a GitHub repository embed and a `canonical_url` if
  the article is also published elsewhere.
- **Anti-spam constraints:** posts must be on-topic, high-quality, substantial,
  and not primarily promotional or backlink-driven. Include enough commands,
  output, design trade-offs, and limitations to teach something without leaving
  DEV. Respectful participation and cited sources are part of the official Code
  of Conduct.
- **Evidence-led article shape:** fragile shell-string failure mode; the
  preflight/plan/run/receipt model; a generated-fixture demo; the exact probe and
  receipt fields; a short comparison with raw FFmpeg, graph builders, and PyAV;
  beta limitations; then repository and issue links.

### 3. Product Hunt — secondary early-adopter launch

- **Official pages:** [How to post a product](https://help.producthunt.com/en/articles/479557-how-to-post-a-product),
  [Product Hunt Launch Guide](https://www.producthunt.com/launch), and
  [posting-access rules](https://help.producthunt.com/en/articles/481909-how-can-i-get-access-to-post).
- **Product name:** `PyFFmpegCore` (name only; no description or emoji).
- **Suggested tagline:** `Inspect FFmpeg workflows before running them, then keep the receipt`
- **Primary link:** the direct product/docs URL, not a press article or launch
  blog. For this project the five-minute proof is the clearest trial path; add
  the GitHub repository separately where the form permits.
- **Required/wise disclosure:** Product Hunt recommends that makers post their
  own product. Use the maintainer's personal account and a maker comment that
  says what was built, what remains beta, that FFmpeg is a system dependency,
  and which result has been reproduced. Company/branded accounts cannot post,
  vote, or comment.
- **Title/link constraints:** use only the product name in the name field, a very
  short tagline, and only a few strongly related topics. A new personal account
  normally waits one week before posting (the official access page notes a
  newsletter route for immediate access); use that week to participate and
  prepare, not to manufacture engagement.
- **Anti-spam constraints:** sharing the launch link is allowed, but Product Hunt
  explicitly forbids directly asking people to upvote. Ask interested users to
  visit, try the beta, and leave a technical comment. Launch again only for a
  significant product iteration.
- **Evidence-led gallery/comment:** diagram the four-stage lifecycle; show the
  real web-video result and its evidence URL; show the Action's uploaded receipt
  bundle; include a clear "requires local FFmpeg" card. Optimize for qualified
  beta testers, not leaderboard rank.

### 4. Lobsters — excellent fit after community participation

- **Official page:** [Lobsters About and Guidelines](https://lobste.rs/about).
- **Suggested title:** `PyFFmpegCore: preflight, deterministic plans, and receipts for FFmpeg`
- **Primary link:** the GitHub repository or evidence page. Prefer the repository
  for the first submission because the code and non-goals are central.
- **Required/wise disclosure:** add a first comment stating that the submitter is
  the author, why the operational layer exists, and which parts need review.
- **Title/link constraints:** the official About page does not mandate a special
  launch prefix. A submission must fit predefined tags; likely candidates are
  `python`, `programming`, and/or `media` only if available at submission time.
  If no tag fits, the story is not on-topic and should not be submitted.
- **Anti-spam/access constraints:** Lobsters uses an invitation tree to combat
  spam. Its rule of thumb is that self-promotion remain below one quarter of a
  user's stories **and comments**; it rejects write-only product announcements
  and traffic extraction. Do not seek an invitation solely for this launch.
- **Evidence-led angle:** focus on the technical choices most likely to improve a
  reader's next program: argument vectors instead of shell strings, capability
  preflight, cancellation/cleanup policy, stable failure categories, redacted
  receipts, digest-pinned CI execution, and explicit non-goals.

### 5. GitHub Marketplace — durable CI discovery, conditional

- **Official pages:** [Publishing actions in GitHub Marketplace](https://docs.github.com/en/actions/how-tos/create-and-publish-actions/publish-in-github-marketplace)
  and [finding and using Marketplace actions](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/find-and-customize-actions).
- **Listing name/title:** keep the metadata name factual and unique. The current
  `action.yml` name, `PyFFmpegCore Pipeline`, is a reasonable candidate, subject
  to the Marketplace uniqueness check. Use a release title containing the beta
  version, not an unversioned "latest" claim.
- **Primary link:** the Marketplace listing links to its repository and provides
  install syntax. The listing should lead users to the Action contract and an
  immutable-ref example.
- **Required/wise disclosure:** the `author` field already identifies the
  maintainer. Do not describe the account as a "verified creator" unless GitHub
  actually awards that distinct partner badge.
- **Publishing constraints:** the Action must be public, have one root
  `action.yml`/`action.yaml`, use a unique metadata `name`, be published from a
  tagged release, pass metadata validation, select one primary and optionally
  one secondary category, and be published with 2FA after accepting the
  Marketplace Developer Agreement. GitHub says a focused Action repository
  should contain only the metadata, code, and files necessary for that Action.
- **Anti-spam/release constraints:** this is not a discussion feed, so there is
  no launch-post cadence to game. Publish only the real tagged Action and keep
  listing copy aligned with the tested contract. Users see the listing version
  and stars; do not imply GitHub review or endorsement—eligible Actions are
  published immediately without GitHub review.
- **PyFFmpegCore-specific gate:** before listing, use the release UI's validation
  against the current package repository. If it rejects or makes the Action
  boundary unclear, create a dedicated Action repository and keep the container
  image pinned by digest. Announce Marketplace availability only after the
  listing URL and copied workflow syntax work in a clean repository.

## Channel to avoid as a cold launch

### Discussions on Python.org

- **Official page:** [Community Guidelines](https://discuss.python.org/guidelines).
- The forum is for category-specific Python code, ideas, and questions. Its
  guidelines say spam and blatant self-promotion are removed "with extreme
  prejudice" and can cause a first-offense ban. Successful participation is
  described as long-term, constructive engagement, not a one-month launch
  tactic.
- Do not post an announcement under Packaging, Python Help, or another category
  merely to gain visibility. Use the forum only when a genuine category-specific
  discussion exists—for example, a packaging-standard problem that can be
  discussed without requiring readers to adopt PyFFmpegCore—and message
  `@moderators` privately if uncertain.

## Recommended sequence and success evidence

1. Publish the actual beta artifact and immutable release; verify install,
   `doctor`, and `smoke-test` from a clean Linux, macOS, and Windows environment.
2. Prepare one source-of-truth evidence bundle. Keep numbers tied to the dated,
   generated fixtures; never generalize one fixture's compression result.
3. Publish Show HN only if the account eligibility/participation gate is already
   met. Publish the DEV walkthrough the same day or next day, but do not ask one
   community to boost the other.
4. Use Product Hunt for a broader feedback pass. Invite trials and comments, not
   votes.
5. Submit to Lobsters only from a genuine participant whose self-promotion ratio
   remains compliant.
6. Publish the GitHub Marketplace listing after its repository boundary and
   clean-repository Action example are validated.

Record outcomes separately per channel: post/listing URL, publication time,
exact copy, release SHA/version linked, first-party trial failures, actionable
issues opened, and fixes shipped. Page views, votes, and stars can describe
reach, but the better beta signals are successful clean installs, completed
smoke tests, Action runs with uploaded evidence, and specific issue reports.
