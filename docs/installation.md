# Installation

## Requirements

- Python 3.10–3.14
- `ffmpeg` and `ffprobe` on `PATH`, or explicit binary paths
- `pipx` for the recommended isolated CLI install

Install FFmpeg using the package source you already trust for your operating system. PyFFmpegCore deliberately does not download or bundle it.

## macOS and Windows FFmpeg

On macOS, [Homebrew's `ffmpeg` formula](https://formulae.brew.sh/formula/ffmpeg)
provides both `ffmpeg` and `ffprobe`:

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

On Windows, the Microsoft WinGet repository currently lists the
[`Gyan.FFmpeg` 8.1.2 full build](https://github.com/microsoft/winget-pkgs/blob/master/manifests/g/Gyan/FFmpeg/8.1.2/Gyan.FFmpeg.installer.yaml).
Follow Microsoft's [WinGet install command](https://learn.microsoft.com/en-us/windows/package-manager/winget/install)
in PowerShell:

```powershell
winget install --id Gyan.FFmpeg --exact
```

Open a new PowerShell window after installation, then run:

```powershell
ffmpeg -version
ffprobe -version
```

If either executable is still missing, inspect the package's install location
and `PATH`, or pass trusted absolute binary paths as shown in
[troubleshooting](troubleshooting.md#ffmpeg-or-ffprobe-is-missing). The WinGet,
Fedora, Arch, and Homebrew package pages were checked on 24 September 2026.
The Windows, Fedora, and Arch installations were not run on this macOS host.
CI also installs FFmpeg separately on hosted macOS and Windows runners.

## Fedora Linux and Arch Linux

On Fedora 44, install the distribution's
[`ffmpeg-free` package](https://packages.fedoraproject.org/pkgs/ffmpeg/ffmpeg-free/)
with the documented [DNF `install` command](https://dnf.readthedocs.io/en/stable/command_ref.html#install-command):

```bash
sudo dnf install ffmpeg-free
```

Fedora's [Fedora 44 update file list](https://packages.fedoraproject.org/pkgs/ffmpeg/ffmpeg-free/fedora-44-updates.html)
includes both `ffmpeg` and `ffprobe`. This build deliberately supports fewer
codecs than some third-party FFmpeg builds.

On x86_64 Arch Linux, install the official
[`ffmpeg` package](https://archlinux.org/packages/extra/x86_64/ffmpeg/)
as described in the [ArchWiki installation section](https://wiki.archlinux.org/title/FFmpeg#Installation):

```bash
sudo pacman -S ffmpeg
```

The Arch [package file list](https://archlinux.org/packages/extra/x86_64/ffmpeg/files/)
also includes both executables. After installing PyFFmpegCore with `pipx` below,
check the selected build and a real synthetic workflow:

```bash
ffmpeg -version
ffprobe -version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

These Fedora and Arch install commands were checked against official package
pages on 24 September 2026; they were **not executed on those distributions**
in this audit. Encoder and filter availability depends on the installed FFmpeg
build. Inspect `pyffmpegcore doctor --json` before relying on a particular
workflow; PyFFmpegCore does not fetch missing codecs.

## Bash or zsh

Install the exact validated public release:

```bash
pipx install "pyffmpegcore==0.3.0"
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

A repository checkout also provides `./install.sh`.

`uv` users can install the same release as an isolated tool:

```bash
uv tool install "pyffmpegcore==0.3.0"
pyffmpegcore smoke-test
```

## PowerShell

```powershell
pipx install "pyffmpegcore==0.3.0"
pyffmpegcore --version
pyffmpegcore doctor
pyffmpegcore smoke-test
```

From a checkout, use `./install.ps1`; do not run the POSIX shell installer on Windows.

## Python project dependency

For a Python project dependency:

```bash
python -m pip install "pyffmpegcore==0.3.0"
```

Use an appropriate compatible-release constraint after validating future
versions against your own media workflows.

There is no Homebrew tap today. The project will add and maintain one only after
public demand justifies another release channel; Homebrew can still install the
external FFmpeg dependency.

## Verify the selected binaries

```bash
pyffmpegcore doctor --json
```

The report includes resolved paths, versions, build configuration, capability counts, selected workflow encoders/filters, and hardware accelerators. If a capability listing times out, `capabilities` is `null`, `capabilities_error` explains the failure, and `doctor` exits with code 3. Supplying an untrusted `--ffmpeg-path` or `--ffprobe-path` executes that binary; treat it like any other executable.
