---
hide:
  - toc
  - navigation
  - path
---

<div class="pfc-home">
  <section class="pfc-hero" aria-labelledby="pfc-hero-title">
    <div class="pfc-hero__copy">
      <p class="pfc-eyebrow">Local media automation / signal online</p>
      <h1 id="pfc-hero-title">FFmpeg jobs you can <span>explain.</span></h1>
      <p class="pfc-hero__lede">
        Preflight the machine. Preview the exact plan. Run a maintained workflow.
        Keep a privacy-redacted receipt. PyFFmpegCore turns fragile media commands
        into repeatable operations for the terminal, Python, and CI.
      </p>
      <div class="pfc-actions">
        <a class="pfc-button" href="quickstart/">Prove it in five minutes</a>
        <a class="pfc-button pfc-button--ghost" href="recipes/">Pick a real recipe</a>
      </div>
    </div>
    <div class="pfc-hero__console">
      <div class="pfc-terminal" aria-label="Successful PyFFmpegCore smoke test">
        <div class="pfc-terminal__bar">
          <span>Proof channel / local</span>
          <span class="pfc-terminal__status">● ready</span>
        </div>
        <div class="pfc-terminal__body">
          <p class="pfc-prompt">$ pyffmpegcore doctor</p>
          <p class="pfc-output">FFmpeg: found / capabilities indexed</p>
          <p class="pfc-output">FFprobe: found / probe channel ready</p>
          <br>
          <p class="pfc-prompt">$ pyffmpegcore smoke-test</p>
          <p class="pfc-output">Smoke test: PASS</p>
          <p class="pfc-output--muted">Synthetic input: mpeg4 320x180</p>
          <p class="pfc-output--muted">Verified thumbnail: 160x90</p>
          <br>
          <p class="pfc-output--cyan">No personal media. Artifacts cleaned.</p>
          <button class="pfc-copy" type="button" data-pfc-copy aria-label="Copy the immutable evaluation install command" aria-live="polite">Copy immutable install</button>
        </div>
      </div>
    </div>
  </section>

  <noscript><span class="pfc-noscript">JavaScript is optional. Use the install command in the five-minute guide.</span></noscript>

  <section class="pfc-metrics" aria-label="Supported environments and privacy properties">
    <div class="pfc-metric"><strong>3</strong><span class="pfc-metric__label">operating systems</span></div>
    <div class="pfc-metric"><strong>5</strong><span class="pfc-metric__label">Python versions</span></div>
    <div class="pfc-metric"><strong>0</strong><span class="pfc-metric__label">default telemetry</span></div>
    <div class="pfc-metric"><strong>1</strong><span class="pfc-metric__label">shared typed engine</span></div>
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
        These are reproducible runs against generated first-party fixtures, with the
        commands, probes, receipts, and checksums published for inspection.
      </p>
    </div>
    <div class="pfc-proof-grid">
      <article class="pfc-proof">
        <span class="pfc-proof__label">Web video / size change</span>
        <strong>−19.4%</strong>
        <p>688,662-byte MOV to a 555,083-byte browser-compatible H.264 MP4.</p>
        <a href="evidence/#web-compatible-video">Inspect the evidence →</a>
      </article>
      <article class="pfc-proof">
        <span class="pfc-proof__label">Exact-size / output</span>
        <strong>248,417 B</strong>
        <p>A 4,042,503-byte source compressed below a strict 256 KiB target.</p>
        <a href="evidence/#exact-size-compression">Inspect the evidence →</a>
      </article>
      <article class="pfc-proof">
        <span class="pfc-proof__label">Podcast / measured loudness</span>
        <strong>−16.2 LUFS</strong>
        <p>A −22.0 LUFS WAV normalized toward the declared −16.0 LUFS speech target.</p>
        <a href="evidence/#podcast-loudness">Inspect the evidence →</a>
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
