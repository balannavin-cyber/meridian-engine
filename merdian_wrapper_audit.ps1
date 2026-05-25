# merdian_wrapper_audit.ps1
# TD-061 wrapper-level migration. Most MERDIAN_* tasks are wrapped by
# .bat / .cmd / .ps1 files; the python.exe invocation lives INSIDE the
# wrapper, not in the Task Scheduler action. This script discovers those
# wrappers, audits them for python.exe, and (with -Apply) migrates to
# pythonw.exe while preserving file encoding byte-for-byte.
#
# Run as Administrator from C:\GammaEnginePython (or wherever the wrappers live).
#
#   .\merdian_wrapper_audit.ps1 -List       # show wrapper files per task
#   .\merdian_wrapper_audit.ps1 -DryRun     # show python.exe lines in each wrapper
#   .\merdian_wrapper_audit.ps1 -Apply      # patch wrappers in place (.bak backups)
#   .\merdian_wrapper_audit.ps1 -Rollback   # restore from .bak backups

param(
    [switch]$List,
    [switch]$DryRun,
    [switch]$Apply,
    [switch]$Rollback,
    [string]$TaskNamePattern = "MERDIAN_*"
)

$ErrorActionPreference = "Stop"

function Resolve-WrapperFiles {
    param($task)

    $exe = $task.Actions[0].Execute
    $argline = $task.Actions[0].Arguments
    $wrappers = @()

    if ([string]::IsNullOrEmpty($exe)) { return $wrappers }
    $exeLower = $exe.ToLower()

    # Direct python invocation -- handled by merdian_task_hygiene.ps1
    if ($exeLower -match 'pythonw?\.exe$') { return $wrappers }

    # Direct .bat / .cmd action
    if ($exe -match '\.(bat|cmd)$') {
        $wrappers += $exe
        return $wrappers
    }

    # cmd.exe / cmd wrapper -- bat path lives in Arguments
    if ($exeLower -match '(^|\\)cmd(\.exe)?$') {
        if ($argline -match '/[cCkK]\s+"?([^"]+\.(?:bat|cmd))"?') {
            $wrappers += $matches[1].Trim()
        } else {
            $wrappers += "<UNRESOLVED cmd args: $argline>"
        }
        return $wrappers
    }

    # powershell.exe wrapper -- .ps1 path or inline -Command
    if ($exeLower -match '(^|\\)powershell(\.exe)?$') {
        # Pattern A: -File <ps1>
        if ($argline -match '-File\s+"?([^"]+\.ps1)"?') {
            $wrappers += $matches[1].Trim()
            return $wrappers
        }
        # Pattern B: inline -Command containing nested Start-Process cmd /c <bat>
        # Matches: 'Start-Process cmd -ArgumentList '/c C:\path\to\thing.bat ...'
        if ($argline -match "/[cC]\s+([A-Za-z]:[\\/][^\s'<>|]+\.(?:bat|cmd))") {
            $wrappers += $matches[1].Trim()
            return $wrappers
        }
        # Pattern C: inline -Command running python directly in the task action itself
        # e.g. ...; python <script>.py ... or ...; python.exe <script>.py ...
        # This is NOT a wrapper-file edit -- it's a task Arguments edit.
        if ($argline -match '-Command\b[^"]*"[^"]*\bpython(?:\.exe)?\b\s+[^"]*\.py') {
            $wrappers += "<TASK-ACTION-INLINE-PYTHON: edit task Arguments, not a wrapper file>"
            return $wrappers
        }
        # Pattern D: anything else inline -Command -- punt to manual review
        if ($argline -match '-Command\s+(.+)$') {
            $wrappers += "<INLINE-COMMAND (manual review): $argline>"
            return $wrappers
        }
        $wrappers += "<UNRESOLVED powershell args: $argline>"
        return $wrappers
    }

    return $wrappers
}

function Find-PythonInvocations {
    param([string]$filePath)

    if (-not (Test-Path $filePath)) {
        return @{ Found = $false; Hits = @(); Reason = "file not found" }
    }
    $hits = @()
    $i = 0
    foreach ($line in Get-Content $filePath) {
        $i++
        # Match python.exe but NOT pythonw.exe (negative re-check)
        if ($line -match '\bpython\.exe\b') {
            $hits += [pscustomobject]@{ Line = $i; Text = $line.TrimEnd() }
        }
    }
    return @{ Found = $true; Hits = $hits; Reason = "" }
}

function Patch-WrapperFile {
    param([string]$filePath)

    if (-not (Test-Path $filePath)) {
        return @{ OK = $false; Reason = "file not found" }
    }
    $bytes = [System.IO.File]::ReadAllBytes($filePath)
    if ($bytes.Length -eq 0) {
        return @{ OK = $true; Reason = "empty file" }
    }
    # Round-trip via iso-8859-1 to preserve every byte for non-ASCII safe edit.
    # python.exe / pythonw.exe are pure ASCII, so single-byte re-encoding is safe.
    $latin1 = [System.Text.Encoding]::GetEncoding('iso-8859-1')
    $text = $latin1.GetString($bytes)
    $original = $text

    $text = [regex]::Replace($text, '\bpython\.exe\b', 'pythonw.exe')

    if ($text -eq $original) {
        return @{ OK = $true; Reason = "no changes" }
    }

    Copy-Item -Path $filePath -Destination "$filePath.bak" -Force
    $newBytes = $latin1.GetBytes($text)
    [System.IO.File]::WriteAllBytes($filePath, $newBytes)
    return @{ OK = $true; Reason = "patched" }
}

function Restore-WrapperFile {
    param([string]$filePath)
    $bak = "$filePath.bak"
    if (-not (Test-Path $bak)) {
        return @{ OK = $false; Reason = "no .bak found" }
    }
    Copy-Item -Path $bak -Destination $filePath -Force
    Remove-Item $bak -Force
    return @{ OK = $true; Reason = "restored" }
}

# ---------- Main ----------

$tasks = Get-ScheduledTask | Where-Object { $_.TaskName -like $TaskNamePattern } | Sort-Object TaskName
if ($tasks.Count -eq 0) {
    Write-Host "No tasks matching $TaskNamePattern" -ForegroundColor Yellow
    exit 1
}

if (-not ($List -or $DryRun -or $Apply -or $Rollback)) {
    Write-Host "Usage:"
    Write-Host "  .\merdian_wrapper_audit.ps1 -List       # show wrapper files per task"
    Write-Host "  .\merdian_wrapper_audit.ps1 -DryRun     # show python.exe lines in each wrapper"
    Write-Host "  .\merdian_wrapper_audit.ps1 -Apply      # patch wrappers (.bak backups)"
    Write-Host "  .\merdian_wrapper_audit.ps1 -Rollback   # restore .bak backups"
    return
}

# ---------- LIST ----------
if ($List) {
    Write-Host "Wrapper files referenced by $($tasks.Count) MERDIAN_* tasks:" -ForegroundColor Cyan
    foreach ($t in $tasks) {
        $wrappers = Resolve-WrapperFiles $t
        $exe = $t.Actions[0].Execute
        Write-Host "[$($t.TaskName)]" -ForegroundColor White
        Write-Host "  Execute: $exe" -ForegroundColor DarkGray
        if ($t.Actions[0].Arguments) {
            Write-Host "  Args   : $($t.Actions[0].Arguments)" -ForegroundColor DarkGray
        }
        if ($wrappers.Count -eq 0) {
            if ($exe -match 'pythonw\.exe$') {
                Write-Host "  -> direct pythonw.exe (already migrated)" -ForegroundColor Green
            } elseif ($exe -match 'python\.exe$') {
                Write-Host "  -> direct python.exe (use merdian_task_hygiene.ps1 -Apply)" -ForegroundColor Yellow
            } else {
                Write-Host "  -> no Python involvement detected" -ForegroundColor DarkGray
            }
        } else {
            foreach ($w in $wrappers) {
                if ($w -like '<*') {
                    Write-Host "  -> $w" -ForegroundColor Magenta
                } elseif (-not (Test-Path $w)) {
                    Write-Host "  -> $w  (NOT FOUND on disk)" -ForegroundColor Red
                } else {
                    Write-Host "  -> $w" -ForegroundColor Cyan
                }
            }
        }
    }
    return
}

# ---------- DRYRUN ----------
if ($DryRun) {
    Write-Host "DRY RUN -- python.exe occurrences inside wrapper files (no changes)" -ForegroundColor Yellow
    $needPatch = 0
    $cleanCount = 0
    $unresolved = 0
    foreach ($t in $tasks) {
        $wrappers = Resolve-WrapperFiles $t
        if ($wrappers.Count -eq 0) { continue }
        Write-Host "[$($t.TaskName)]" -ForegroundColor White
        foreach ($w in $wrappers) {
            if ($w -like '<*') {
                Write-Host "  ! manual review: $w" -ForegroundColor Magenta
                $unresolved++
                continue
            }
            Write-Host "  $w" -ForegroundColor Cyan
            $r = Find-PythonInvocations $w
            if (-not $r.Found) {
                Write-Host "    (NOT FOUND on disk)" -ForegroundColor Red
                continue
            }
            if ($r.Hits.Count -eq 0) {
                Write-Host "    (no python.exe -- already clean or no python invocation)" -ForegroundColor DarkGray
                $cleanCount++
            } else {
                $needPatch++
                foreach ($h in $r.Hits) {
                    Write-Host "    L$($h.Line):  $($h.Text)" -ForegroundColor Yellow
                }
            }
        }
    }
    Write-Host ""
    Write-Host "Summary: wrappers needing patch=$needPatch  clean=$cleanCount  manual-review=$unresolved" -ForegroundColor Cyan
    return
}

# ---------- APPLY ----------
if ($Apply) {
    $patched = 0
    $clean = 0
    $skipped = 0
    $failed = 0
    $seen = @{}
    foreach ($t in $tasks) {
        $wrappers = Resolve-WrapperFiles $t
        foreach ($w in $wrappers) {
            if ($w -like '<*') {
                Write-Host "[$($t.TaskName)] SKIP (manual): $w" -ForegroundColor Magenta
                $skipped++
                continue
            }
            # Multiple tasks may reference the same wrapper -- patch once
            if ($seen.ContainsKey($w)) {
                Write-Host "[$($t.TaskName)] $w (already processed in this run)" -ForegroundColor DarkGray
                continue
            }
            $seen[$w] = $true

            $r = Patch-WrapperFile $w
            if (-not $r.OK) {
                Write-Host "[$($t.TaskName)] FAIL ${w}: $($r.Reason)" -ForegroundColor Red
                $failed++
            } elseif ($r.Reason -eq "no changes") {
                Write-Host "[$($t.TaskName)] clean ${w}" -ForegroundColor DarkGray
                $clean++
            } else {
                Write-Host "[$($t.TaskName)] PATCHED ${w} (.bak written)" -ForegroundColor Green
                $patched++
            }
        }
    }
    Write-Host ""
    Write-Host "Summary: patched=$patched  already-clean=$clean  skipped-manual=$skipped  failed=$failed" -ForegroundColor Cyan
    if ($patched -gt 0) {
        Write-Host "Rollback any time with: .\merdian_wrapper_audit.ps1 -Rollback" -ForegroundColor Cyan
    }
    return
}

# ---------- ROLLBACK ----------
if ($Rollback) {
    Write-Host "Restoring wrappers from .bak backups..." -ForegroundColor Yellow
    $restored = 0
    $missing = 0
    $seen = @{}
    foreach ($t in $tasks) {
        $wrappers = Resolve-WrapperFiles $t
        foreach ($w in $wrappers) {
            if ($w -like '<*') { continue }
            if ($seen.ContainsKey($w)) { continue }
            $seen[$w] = $true
            $r = Restore-WrapperFile $w
            if ($r.OK) {
                Write-Host "[$($t.TaskName)] restored $w" -ForegroundColor Green
                $restored++
            } else {
                Write-Host "[$($t.TaskName)] $w  ($($r.Reason))" -ForegroundColor DarkGray
                $missing++
            }
        }
    }
    Write-Host ""
    Write-Host "Summary: restored=$restored  no-bak=$missing" -ForegroundColor Cyan
    return
}
