---
hide:
  - toc
  - navigation
  - path
---

<div data-md-component="skip">
  <a href="#pfc-hero-title" class="md-skip">Skip to content</a>
</div>

<div class="pfc-home">
  <section class="pfc-hero" aria-labelledby="pfc-hero-title">
    <div class="pfc-hero__copy">
      <p class="pfc-eyebrow">Local media automation / signal online</p>
      <h1 id="pfc-hero-title">FFmpeg jobs you can <span>explain.</span></h1>
      <div class="pfc-actions">
        <a class="pfc-button" href="quickstart/">Five-minute start</a>
        <a class="pfc-button pfc-button--ghost" href="terminal-demo/">Watch 0.3.1 proof</a>
        <a class="pfc-button pfc-button--ghost" href="recipes/">Browse recipes</a>
      </div>
      <p class="pfc-hero__lede">
        Preflight the machine. Preview the exact plan. Run a maintained workflow.
        Keep a privacy-redacted receipt. PyFFmpegCore turns fragile media commands
        into repeatable operations for the terminal, Python, and CI.
      </p>
      <div class="pfc-install" aria-label="Install the current public beta">
        <div class="pfc-install__command">
          <span class="pfc-install__label">Current beta / 0.3.1</span>
          <code>pipx install "pyffmpegcore==0.3.1"</code>
        </div>
        <button class="pfc-copy" type="button" data-pfc-copy aria-live="polite">Copy install command</button>
        <p>Requires Python 3.10–3.14 and system <code>ffmpeg</code>/<code>ffprobe</code>. <a href="https://pypi.org/project/pyffmpegcore/0.3.1/">View package →</a></p>
      </div>
    </div>
    <div class="pfc-hero__console">
      <div class="pfc-terminal-transcript" role="group" aria-label="Excerpt from the verified public 0.3.1 terminal recording">
        <div class="pfc-terminal-transcript__bar"><span>PUBLIC RUN / 0.3.1</span><span>63.4 S</span></div>
        <pre><samp>PyFFmpegCore CLI 0.3.1

Smoke test: PASS
Preflight PASS — convert
Progress: 100% complete
Valid receipt: schema 1.0, 1 item(s)

PASS — public install, preflight, plan,
progress, output, and receipt all verified.</samp></pre>
        <p>Accessible transcript excerpt from the <a href="assets/terminal-demo-v0.3.1.txt">recorded public PyPI run</a>.</p>
      </div>
    </div>
  </section>

  <noscript><span class="pfc-noscript">JavaScript is optional. Use the install command in the five-minute guide.</span></noscript>

  <section class="pfc-metrics" aria-label="Supported environments and privacy properties">
    <div class="pfc-metric"><strong>3</strong><span class="pfc-metric__label">operating systems</span></div>
    <div class="pfc-metric"><strong>5</strong><span class="pfc-metric__label">Python versions</span></div>
    <div class="pfc-metric"><strong>0</strong><span class="pfc-metric__label">default telemetry</span></div>
    <div class="pfc-metric"><strong>0.3.1</strong><span class="pfc-metric__label">signed public beta</span></div>
  </section>

  <section class="pfc-live-proof" aria-labelledby="live-proof-title">
    <div class="pfc-live-proof__signal" aria-hidden="true"><span>63.4</span><small>seconds</small></div>
    <div class="pfc-live-proof__copy">
      <p class="pfc-kicker">Public PyPI 0.3.1 recording / no staged output</p>
      <h2 id="live-proof-title">Watch a real 0.3.1 run.</h2>
      <p>The 63.4-second capture shows a fresh install, capability scan, synthetic smoke test, explained plan, progress, probed output, and validated receipt from the current signed public beta.</p>
      <div class="pfc-actions">
        <a class="pfc-button" href="terminal-demo/">Open the 0.3.1 terminal proof</a>
        <a class="pfc-button pfc-button--ghost" href="https://github.com/OthmaneBlial/pyffmpegcore/releases/tag/v0.3.1">Inspect the 0.3.1 release</a>
      </div>
    </div>
  </section>

  <section class="pfc-section" aria-labelledby="flow-title">
    <div class="pfc-section__head">
      <h2 id="flow-title">One job.<br>Four proofs.</h2>
      <p>
        Most wrappers start at execution. PyFFmpegCore starts one step earlier and
        leaves evidence one step later, so the same intent is reviewable before and
        after FFmpeg touches a file.
      </p>
    </div>
    <div class="pfc-flow">
      <article class="pfc-stage">
        <span class="pfc-stage__index">01 / Preflight</span>
        <h3>Know the machine</h3>
        <p>Resolve binaries, encoders, filters, muxers, protocols, streams, destination, and disk requirements.</p>
      </article>
      <article class="pfc-stage">
        <span class="pfc-stage__index">02 / Plan</span>
        <h3>See the exact work</h3>
        <p>Inspect a deterministic argument vector and human explanation without mutating the filesystem.</p>
      </article>
      <article class="pfc-stage">
        <span class="pfc-stage__index">03 / Run</span>
        <h3>Control failure</h3>
        <p>Use explicit overwrite, timeout, cancellation, cleanup, progress, and stable exit-code policies.</p>
      </article>
      <article class="pfc-stage">
        <span class="pfc-stage__index">04 / Receipt</span>
        <h3>Keep the evidence</h3>
        <p>Record redacted plans, tool versions, probes, elapsed results, and output facts without uploading media.</p>
      </article>
    </div>
  </section>

  <section class="pfc-section" aria-labelledby="proof-title">
    <div class="pfc-section__head">
      <h2 id="proof-title">Measured.<br>Not mocked.</h2>
      <p>
        The 19 September replay used generated first-party fixtures. A separate
        public-domain Xiph clip confirms the exact-size result. Commands, probes,
        receipts, checksums, and limits are open for inspection.
      </p>
    </div>
    <div class="pfc-proof-grid">
      <article class="pfc-proof">
        <span class="pfc-proof__label">Web video / compatibility cost</span>
        <strong>+78.2%</strong>
        <p>2,141,004-byte VP9 WebM to a 3,814,506-byte H.264/AAC MP4. Wider playback compatibility can increase size.</p>
        <a href="evidence/#replay-on-19-september-2026">Inspect the replay →</a>
      </article>
      <article class="pfc-proof">
        <span class="pfc-proof__label">Exact-size / public-domain video</span>
        <strong>1 MiB target</strong>
        <p>An 8,147,493-byte Xiph VP9 clip reached 1,035,870 bytes with a 7% reserve. The default 5% missed by 7,803 bytes.</p>
        <a href="evidence/#public-domain-exact-size-check-on-24-september-2026">Inspect the exact-size check →</a>
      </article>
      <article class="pfc-proof">
        <span class="pfc-proof__label">Podcast / measured loudness</span>
        <strong>−16.2 LUFS</strong>
        <p>A −22.0 LUFS WAV normalized toward the declared −16.0 LUFS speech target.</p>
        <a href="evidence/#replay-on-19-september-2026">Inspect the replay →</a>
      </article>
    </div>
  </section>

  <section class="pfc-section" aria-labelledby="lanes-title">
    <div class="pfc-section__head">
      <h2 id="lanes-title">Choose your lane.</h2>
      <p>Start from the outcome you need. Every lane reaches the same planner, preflight, runner, and receipt model.</p>
    </div>
    <div class="pfc-lanes">
      <article class="pfc-lane">
        <h3>One useful file</h3>
        <p>Convert a web video, fit an upload limit, normalize speech, burn subtitles, extract audio, or make thumbnails.</p>
        <a href="recipes/">Open the recipe index →</a>
      </article>
      <article class="pfc-lane">
        <h3>Repeatable pipeline</h3>
        <p>Validate, visualize, run, cache, and resume strict JSON or TOML DAGs without embedding raw shell strings.</p>
        <a href="pipelines/">Build a pipeline →</a>
      </article>
      <article class="pfc-lane">
        <h3>Automation surface</h3>
        <p>Use the same typed engine from Python, a digest-pinned GitHub Action, or the multi-architecture container.</p>
        <a href="reference/python-api/">Open the Python API →</a>
      </article>
    </div>
  </section>

  <section class="pfc-section" aria-label="Tool selection guidance">
    <div class="pfc-callout">
      <h2>Know when not to use it.</h2>
      <div>
        <p>
          Raw FFmpeg is better when you already own the exact argument vector.
          Graph builders are better for arbitrary filter graphs. PyAV is better for
          direct packet and frame access. PyFFmpegCore owns the repeatable task layer:
          diagnostics, plans, execution policy, and proof.
        </p>
        <a href="comparison/">Read the factual comparison →</a>
      </div>
    </div>
  </section>
</div>
