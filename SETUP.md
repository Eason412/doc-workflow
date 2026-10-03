# Agent Setup

This manual covers local installation from a stable checkout of Doc Workflow. Each directory under `skills/` is a complete Skill with its own `SKILL.md`, references, and any supporting scripts. The POSIX installer discovers all Skill directories and links them into both Codex and Claude Code; it has no per-Skill selection parameter, so a single Skill or a single host uses the manual path at the end of step 3. Other hosts that support `SKILL.md` can load a complete Skill directory using their own installation mechanism.

The agent must inspect the environment before changes, present the dry-run result, and obtain user approval before applying links. Existing authorization covers only the operations it explicitly includes. Dependency installation, configuration changes, and host restarts also require approval before execution unless already authorized. No account login, paid API call, or project-document conversion is part of installation.

## 📍 1. Repository location

The user selects a stable location. The author's convention is `~/Projects/opensource/<repo>`, making `~/Projects/opensource/doc-workflow` the example below. An existing checkout should be reused after inspection; an occupied path must not be overwritten.

A new checkout needs Git. Check it first with `command -v git` (PowerShell: `Get-Command git`); if Git is missing, obtain approval to install it or use a locally supplied copy. Then, after permission to create the checkout at the selected location:

```sh
mkdir -p "$HOME/Projects/opensource"
git clone https://github.com/Eason412/doc-workflow.git "$HOME/Projects/opensource/doc-workflow"
cd "$HOME/Projects/opensource/doc-workflow"
```

On native Windows, in PowerShell:

```powershell
New-Item -ItemType Directory -Path (Join-Path $HOME 'Projects/opensource') -Force | Out-Null
git clone https://github.com/Eason412/doc-workflow.git (Join-Path $HOME 'Projects/opensource/doc-workflow')
Set-Location (Join-Path $HOME 'Projects/opensource/doc-workflow')
```

Native Windows then skips the POSIX steps 3–4 and uses step 5. If cloning fails, report the result and use an available local copy; do not assume the remote exists. Reading a locally supplied Skill directory does not need Git.

Read [AGENTS.md](AGENTS.md) (Chinese), [scripts/link-skills.sh](scripts/link-skills.sh), and the relevant Skill entry points before installation. The success criterion is a stable checkout containing the four `skills/<name>/SKILL.md` files and the linking script. Commands below run from that checkout; substitute the selected path if different.

## 🧰 2. Dependency inventory

Only prepare tools for the functions that will be used. The agent records what is present and obtains approval for any missing software installation. Package-manager commands depend on the actual OS and available package manager; this repository supplies no universal dependency installer.

| Function | Required tools | Source |
| --- | --- | --- |
| POSIX linking | POSIX `sh`, `mkdir`, `date`, `basename`, `dirname`, `readlink`, `rm`, `mv`, `ln` | [Linking script](scripts/link-skills.sh) |
| Writing, translation, wording edits | An agent able to read the Skill and input files | Skill entry points (Chinese): [project-docs](skills/project-docs/SKILL.md), [translate](skills/translate/SKILL.md), [trim-hedging](skills/trim-hedging/SKILL.md) |
| README link checks | uv, Python ≥ 3.10, `markdown-it-py>=3` | [Checker inline metadata](skills/project-docs/scripts/check_readme.py) |
| Markdown-to-PDF conversion | uv, Python ≥ 3.10, `pymupdf>=1.24`, Pandoc, Chrome / Chromium / Edge | [Converter](skills/md-export/scripts/md_to_pdf.py) |
| Chinese and English PDF text | Installed fonts covering the document's characters | [Print styles](skills/md-export/assets/print.css) |
| Optional font diagnosis | `pdffonts` | [Troubleshooting](skills/md-export/references/qa.md) (Chinese) |

PDF inputs for translation require the host's PDF reading capability; the translation Skill specifies no separate PDF extraction package or translation service. Git is additionally required when the checker uses `--require-tracked`.

For a POSIX environment, the following commands inspect available executables without installing anything:

```sh
command -v sh
command -v git
command -v uv
command -v pandoc
```

On Windows, the equivalents are `Get-Command git`, `Get-Command uv`, and `Get-Command pandoc`. A missing optional tool is recorded against the corresponding function rather than treated as a failure of text-only Skills.

uv supplies the Python environment and resolves the scripts' inline dependencies; no global Python package installation is needed. Pandoc must support the converter's `--embed-resources` option. The browser must support its headless printing arguments; neither tool has a pinned minimum version in this repository. Browser detection covers common macOS and Windows locations and Linux executable names; an explicit executable can be passed with `--chrome`.

The font stack includes Times New Roman, Songti SC, PingFang SC, Noto Serif CJK SC, and Microsoft YaHei, with separate monospace fallbacks. These are alternatives, not a requirement to install every listed font. TeX is not required. Success means the chosen functions have their actual dependencies available or have clearly recorded missing prerequisites.

## 🔍 3. POSIX installation preview

On macOS or Linux, from the repository root:

```sh
scripts/link-skills.sh --dry-run
```

The only documented option is `--dry-run`. The script resolves the repository from its own location and targets:

| Host | Skill directory | Backup directory |
| --- | --- | --- |
| Codex | `${CODEX_HOME:-$HOME/.codex}/skills` | `${CODEX_HOME:-$HOME/.codex}/skills-backup` |
| Claude Code | `$HOME/.claude/skills` | `$HOME/.claude/skills-backup` |

An already-correct symbolic link is skipped when its stored target exactly matches the absolute source path. A different symbolic link is removed and replaced. An existing real directory or file is moved into the sibling `skills-backup/` directory as `<name>-<YYYYMMDDHHMMSS>` before link creation. The script installs every directory under `skills/` into both host directories, even if only one host is currently used. Finally, a symbolic link in either host directory that points into this checkout's `skills/` but no longer resolves, left by a renamed or removed Skill, is removed and reported as `pruned`.

If `CODEX_HOME` is set, inspect and confirm it before preview; the same value must be used for application. Empty or unset `CODEX_HOME` selects `$HOME/.codex`.

Success means the preview lists the expected source and destination paths, replacements, and backups without changing them; backup names take their timestamp from the actual run. Present this concrete plan to the user and wait for approval before step 4.

For a single Skill or a single host, skip the script and link by hand. Set `name` and `target` to the chosen Skill and host directory, inspect the destination, and present the result before changing anything:

```sh
name=project-docs
target="$HOME/.claude/skills"   # or "${CODEX_HOME:-$HOME/.codex}/skills"
ls -ld "$target/$name" 2>/dev/null || echo "free    $target/$name"
```

After approval, clear the destination the same way the script does, then link and verify. An old symbolic link is removed; a real directory goes to the sibling `skills-backup/`:

```sh
mkdir -p "$target"
if [ -L "$target/$name" ]; then rm "$target/$name"
elif [ -e "$target/$name" ]; then
  backup="$(dirname "$target")/skills-backup"; mkdir -p "$backup"
  mv "$target/$name" "$backup/$name-$(date +%Y%m%d%H%M%S)"
fi
ln -s "$PWD/skills/$name" "$target/$name"
readlink "$target/$name" && test -f "$target/$name/SKILL.md"
```

Success means `readlink` prints the repository Skill path and `SKILL.md` is readable through the link. On native Windows, the equivalent single entry is `New-Item -ItemType Junction -Path <target>\<name> -Target <checkout>\skills\<name>` after the same inspection and approval; step 5 covers all Skills.

## 🔗 4. POSIX link application

After approval, in the same environment and repository root:

```sh
scripts/link-skills.sh
```

Do not move or remove the checkout after installation: the installed entries point into it. Changes made inside `skills/<name>/` are immediately visible through the links. The script keeps already-correct links and replaces other entries according to the preview policy.

A nonzero script exit must be reported; final link inspection determines which entries were installed.

Inspect the resulting targets:

```sh
(
for target in "${CODEX_HOME:-$HOME/.codex}/skills" "$HOME/.claude/skills"; do
  for name in project-docs translate trim-hedging md-export; do
    test -L "$target/$name" || exit 1
    test "$(readlink "$target/$name")" = "$(pwd -P)/skills/$name" || exit 1
    test -f "$target/$name/SKILL.md" || exit 1
  done
done
) && echo "all links ok"
scripts/link-skills.sh --dry-run
```

The subshell keeps a failed check from closing the Agent's shell.

Success means all eight entries point to the corresponding absolute repository directories, each entry exposes `SKILL.md`, and the second preview reports `ok` for every entry. Record any backup locations actually created; backups are retained for recovery.

## 🪟 5. Native Windows equivalent

The POSIX script is not a native PowerShell installer. For native Windows hosts, directory junctions created by `New-Item -ItemType Junction` provide the equivalent directory indirection. Junctions are suited to local directories and generally require neither Developer Mode nor elevation. Symbolic links created with `New-Item -ItemType SymbolicLink` can be used with Developer Mode enabled, or with the required elevated privilege; their privilege requirements and support for remote paths differ from junctions.

A WSL installation follows the POSIX steps inside WSL and installs into that environment's home directories. Its links do not install Skills for native Windows hosts. For native hosts, use a stable Windows checkout and native home paths. The Windows default directories are `$HOME\.codex\skills` and `$HOME\.claude\skills`; `CODEX_HOME` overrides the Codex base directory just as on POSIX.

The following PowerShell block provides a preview first. `$Repo` must identify the inspected stable checkout; `$Apply` remains `$false` until the user approves the printed plan. After approval, rerun the block with `$Apply = $true`. The block handles every Skill directory, skips an existing correct link or junction, replaces other links or junctions, and backs up real directories or files beside `skills`.

```powershell
$ErrorActionPreference = 'Stop'
$Repo = (Get-Location).Path   # run from the checkout root
$Apply = $false
$CodexBase = if ([string]::IsNullOrEmpty($env:CODEX_HOME)) {
    Join-Path $HOME '.codex'
} else {
    [IO.Path]::GetFullPath($env:CODEX_HOME)
}
$Targets = @(
    (Join-Path $CodexBase 'skills'),
    (Join-Path $HOME '.claude/skills')
)
$Stamp = Get-Date -Format 'yyyyMMddHHmmss'
$Sources = @(Get-ChildItem -LiteralPath (Join-Path $Repo 'skills') -Directory)

foreach ($Target in $Targets) {
    Write-Output "ensure  $Target"
    if ($Apply) {
        New-Item -ItemType Directory -Path $Target -Force | Out-Null
    }
    foreach ($Skill in $Sources) {
        $Source = $Skill.FullName
        $Dest = Join-Path $Target $Skill.Name
        $Entry = Get-Item -LiteralPath $Dest -Force -ErrorAction SilentlyContinue
        $IsLink = $null -ne $Entry -and
            (($Entry.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0)
        if ($IsLink) {
            $OldTarget = @($Entry.Target)[0]
            if ($OldTarget) {
                if (-not [IO.Path]::IsPathRooted($OldTarget)) {
                    $OldTarget = Join-Path $Target $OldTarget
                }
                $OldTarget = [IO.Path]::GetFullPath($OldTarget)
            }
            if ($OldTarget -eq $Source) {
                Write-Output "ok      $Dest"
                continue
            }
            Write-Output "relink  $Dest -> $Source"
            if ($Apply) {
                # Delete the link itself, without traversing its target.
                if (($Entry.Attributes -band [IO.FileAttributes]::Directory) -ne 0) {
                    [IO.Directory]::Delete($Dest)
                } else {
                    [IO.File]::Delete($Dest)
                }
            }
        } elseif ($null -ne $Entry) {
            $BackupRoot = Join-Path (Split-Path -Parent $Target) 'skills-backup'
            $Backup = Join-Path $BackupRoot ($Skill.Name + '-' + $Stamp)
            Write-Output "backup  $Dest -> $Backup"
            if ($Apply) {
                New-Item -ItemType Directory -Path $BackupRoot -Force | Out-Null
                if (Test-Path -LiteralPath $Backup) {
                    throw "Backup already exists: $Backup"
                }
                Move-Item -LiteralPath $Dest -Destination $Backup
            }
        }
        Write-Output "link    $Dest -> $Source"
        if ($Apply) {
            New-Item -ItemType Junction -Path $Dest -Target $Source | Out-Null
        }
    }
}
```

For Developer Mode symbolic links, change only `-ItemType Junction` in the final creation command to `-ItemType SymbolicLink`. This is a PowerShell adaptation, not an additional option of `link-skills.sh`. It also refuses a pre-existing backup name; the POSIX script has no corresponding explicit collision check.

Verification uses the same `$Targets` and `$Sources` variables:

```powershell
foreach ($Target in $Targets) {
    foreach ($Skill in $Sources) {
        $Dest = Join-Path $Target $Skill.Name
        Get-Item -LiteralPath $Dest -Force |
            Select-Object FullName, LinkType, Target
        if (-not (Test-Path -LiteralPath (Join-Path $Dest 'SKILL.md') -PathType Leaf)) {
            throw "Missing SKILL.md: $Dest"
        }
    }
}
```

Success means every entry is a junction or symbolic link targeting the matching repository Skill, each `SKILL.md` is readable, and another preview prints `ok` for all entries. Native Windows execution must be verified on Windows; a review of this block alone is not an installation result.

## ✅ 6. Skill discovery

After link inspection, start a new host session and confirm that each installed Skill is discoverable and that its references can be read. Perform any host-specific reload or restart only with existing authorization or user approval. No universal reload command is supplied by this repository.

For hosts other than the two targeted by the installer, use the host's documented Skill location and preserve the full selected Skill directory. Success means the host can read the intended `SKILL.md` and its referenced files. Report host discovery separately from filesystem link validation.

## 🧪 7. Optional function checks

The link checker can validate this checkout without changing documents:

```sh
uv run --no-project skills/project-docs/scripts/check_readme.py --repo . --json
uv run --no-project skills/project-docs/scripts/check_readme.py --repo . --file README.en.md --json
uv run --no-project skills/project-docs/scripts/check_readme.py --repo . --file SETUP.md --json
```

Success means each JSON report contains `"ok": true` and no issues. Add `--require-tracked` only when linked documents are expected to be in the Git index; an initial checkout without commits can omit it. The checker does not validate external links, heading anchors, command execution, business behavior, or writing quality. An uncached uv environment may require downloads, so a network-restricted run should use existing caches and offline mode.

For PDF functionality, after approval of a conversion using a disposable input and output:

```sh
uv run --no-project skills/md-export/scripts/md_to_pdf.py input.md --output output.pdf --paper-size A4 --orientation portrait
```

Replace `input.md` and `output.pdf` with agreed test paths; an existing output is replaced on successful conversion. A useful test input includes Chinese and English text, a relative image, a formula, a wide table, and a long code line. The JSON must report a readable PDF with nonzero pages and the requested dimensions. Inspect rendered images of the first page and pages containing images, formulas, and wide tables. Warnings and uninspected content remain explicit in the handover; static JSON validation alone does not establish visual fidelity. Full options and inspection requirements are in [md-export](skills/md-export/SKILL.md) (Chinese).

Text-only Skills need no package smoke test. Their success criterion is accessible instructions and a task outcome checked against the corresponding rules.

## 🔄 8. Updates and maintenance

The author edits `skills/<name>/` directly in the checkout, validates the affected Skill, and then commits and pushes. Linked installations use the same files. Adding, renaming or removing a Skill requires another `scripts/link-skills.sh --dry-run`, approval of new changes, and `scripts/link-skills.sh`; on native Windows, repeat the PowerShell preview and application. Moving the checkout requires relinking after a new preview.

Important writing-rule changes use a blind writing comparison: an evaluator sees only the instructions and writes from scratch; the result is then compared with an accepted draft. Project regression commands are in [AGENTS.md](AGENTS.md) (Chinese), and PR requirements are in [CONTRIBUTING.md](CONTRIBUTING.md) (Chinese). These maintenance operations are separate from installation authorization.

Success means the installed entries reference the maintained checkout and the affected checks have actual reported results. Backups are removed only under a separate, approved cleanup scope.
