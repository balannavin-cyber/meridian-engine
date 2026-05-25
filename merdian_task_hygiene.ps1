# merdian_task_hygiene.ps1
# Ships TD-061 (pythonw.exe migration) + TD-063 (MultipleInstances=IgnoreNew)
# end-to-end across all MERDIAN_* Task Scheduler tasks.
#
# Run as Administrator from any directory.
#
#   .\merdian_task_hygiene.ps1 -List               # list all MERDIAN_* tasks + current state
#   .\merdian_task_hygiene.ps1 -DryRun             # preview changes, no writes
#   .\merdian_task_hygiene.ps1 -Backup             # write XML backups, no changes
#   .\merdian_task_hygiene.ps1 -Apply              # backup + apply changes
#   .\merdian_task_hygiene.ps1 -Verify             # post-apply verification
#   .\merdian_task_hygiene.ps1 -Rollback <stamp>   # restore from a backup folder

param(
    [switch]$List,
    [switch]$DryRun,
    [switch]$Backup,
    [switch]$Apply,
    [switch]$Verify,
    [string]$Rollback = $null,
    [string]$BackupDir = "C:\GammaEnginePython\task_backups",
    [string]$TaskNamePattern = "MERDIAN_*"
)

$ErrorActionPreference = "Stop"

function Get-MerdianTasks {
    Get-ScheduledTask | Where-Object { $_.TaskName -like $TaskNamePattern }
}

function Get-TaskState {
    param($t)
    $exe = if ($t.Actions[0].Execute) { $t.Actions[0].Execute } else { "<none>" }
    $mi  = if ($t.Settings.MultipleInstances) { $t.Settings.MultipleInstances } else { "<default Parallel>" }
    [pscustomobject]@{
        TaskName = $t.TaskName
        Execute = $exe
        MultipleInstances = $mi
        IsPython = ($exe -match "python(?!w)\.exe$")
        IsPythonw = ($exe -match "pythonw\.exe$")
        IsBat = ($exe -match "\.bat$" -or $exe -match "cmd\.exe")
    }
}

function Patch-TaskXml {
    param(
        [string]$xmlText,
        [bool]$migrateExe,
        [bool]$setIgnoreNew
    )
    $xml = [xml]$xmlText
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace("t", $xml.DocumentElement.NamespaceURI)
    $changed = @()

    if ($setIgnoreNew) {
        $mi = $xml.SelectSingleNode("//t:Settings/t:MultipleInstancesPolicy", $ns)
        if ($mi) {
            if ($mi.InnerText -ne "IgnoreNew") {
                $mi.InnerText = "IgnoreNew"
                $changed += "MultipleInstances -> IgnoreNew"
            }
        } else {
            $settings = $xml.SelectSingleNode("//t:Settings", $ns)
            if ($settings) {
                $newMi = $xml.CreateElement("MultipleInstancesPolicy", $xml.DocumentElement.NamespaceURI)
                $newMi.InnerText = "IgnoreNew"
                # Insert near the top of Settings for visibility (order is flexible)
                $settings.AppendChild($newMi) | Out-Null
                $changed += "MultipleInstances ADDED IgnoreNew"
            }
        }
    }

    if ($migrateExe) {
        $cmd = $xml.SelectSingleNode("//t:Actions/t:Exec/t:Command", $ns)
        if ($cmd -and $cmd.InnerText -match "python(?!w)\.exe$") {
            $oldExe = $cmd.InnerText
            $cmd.InnerText = $oldExe -replace "python\.exe$", "pythonw.exe"
            $changed += "Execute: $oldExe -> $($cmd.InnerText)"
        }
    }

    return @{ Xml = $xml.OuterXml; Changes = $changed }
}

# ---------------- LIST ----------------
if ($List) {
    $tasks = Get-MerdianTasks
    Write-Host "Found $($tasks.Count) tasks matching $TaskNamePattern" -ForegroundColor Cyan
    $tasks | ForEach-Object { Get-TaskState $_ } | Format-Table -AutoSize
    return
}

# ---------------- ROLLBACK ----------------
if ($Rollback) {
    $folder = Join-Path $BackupDir "backup_$Rollback"
    if (-not (Test-Path $folder)) {
        Write-Host "Backup folder not found: $folder" -ForegroundColor Red
        exit 1
    }
    $files = Get-ChildItem $folder -Filter *.xml
    Write-Host "Restoring $($files.Count) tasks from $folder" -ForegroundColor Yellow
    foreach ($f in $files) {
        $name = $f.BaseName
        try {
            Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
            Register-ScheduledTask -Xml (Get-Content $f.FullName -Raw) -TaskName $name -Force | Out-Null
            Write-Host "  [$name] restored" -ForegroundColor Green
        } catch {
            Write-Host "  [$name] FAILED: $_" -ForegroundColor Red
        }
    }
    return
}

# ---------------- DEFAULT: require a flag ----------------
if (-not ($List -or $DryRun -or $Backup -or $Apply -or $Verify -or $Rollback)) {
    Write-Host "Usage: see header. Examples:" -ForegroundColor Yellow
    Write-Host "  .\merdian_task_hygiene.ps1 -List"
    Write-Host "  .\merdian_task_hygiene.ps1 -DryRun"
    Write-Host "  .\merdian_task_hygiene.ps1 -Apply"
    Write-Host "  .\merdian_task_hygiene.ps1 -Verify"
    exit 0
}

$tasks = Get-MerdianTasks
if ($tasks.Count -eq 0) {
    Write-Host "No tasks matching $TaskNamePattern" -ForegroundColor Yellow
    exit 1
}

# ---------------- DRYRUN ----------------
if ($DryRun) {
    Write-Host "DRY RUN -- no changes" -ForegroundColor Yellow
    foreach ($t in $tasks) {
        $xmlText = Export-ScheduledTask -TaskName $t.TaskName
        $r = Patch-TaskXml -xmlText $xmlText -migrateExe $true -setIgnoreNew $true
        $state = Get-TaskState $t
        Write-Host "[$($t.TaskName)]" -ForegroundColor Cyan
        Write-Host "  current: Execute=$($state.Execute)  MI=$($state.MultipleInstances)"
        if ($r.Changes.Count -eq 0) {
            Write-Host "  no changes needed" -ForegroundColor Green
        } else {
            $r.Changes | ForEach-Object { Write-Host "  -> $_" -ForegroundColor Yellow }
        }
        if ($state.IsBat) {
            Write-Host "  ! action is .bat/cmd -- pythonw migration must be inside the .bat" -ForegroundColor Magenta
        }
    }
    return
}

# ---------------- BACKUP / APPLY ----------------
if ($Backup -or $Apply) {
    if (-not (Test-Path $BackupDir)) {
        New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
    }
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $thisBackup = Join-Path $BackupDir "backup_$stamp"
    New-Item -ItemType Directory -Path $thisBackup -Force | Out-Null
    Write-Host "Backup folder: $thisBackup" -ForegroundColor Green

    foreach ($t in $tasks) {
        $xml = Export-ScheduledTask -TaskName $t.TaskName
        $xml | Out-File -FilePath (Join-Path $thisBackup "$($t.TaskName).xml") -Encoding utf8
    }
    Write-Host "Backed up $($tasks.Count) task XMLs." -ForegroundColor Green
    Write-Host "Rollback later with:  .\merdian_task_hygiene.ps1 -Rollback $stamp" -ForegroundColor Cyan

    if ($Backup -and -not $Apply) { return }
}

if ($Apply) {
    $applied = 0
    $skipped = 0
    $failed = 0
    foreach ($t in $tasks) {
        $xmlText = Export-ScheduledTask -TaskName $t.TaskName
        $r = Patch-TaskXml -xmlText $xmlText -migrateExe $true -setIgnoreNew $true
        $state = Get-TaskState $t

        if ($r.Changes.Count -eq 0) {
            Write-Host "[$($t.TaskName)] no changes needed" -ForegroundColor DarkGray
            $skipped++
            continue
        }

        try {
            Register-ScheduledTask -Xml $r.Xml -TaskName $t.TaskName -Force | Out-Null
            Write-Host "[$($t.TaskName)]" -ForegroundColor Green
            $r.Changes | ForEach-Object { Write-Host "  $_" }
            $applied++
        } catch {
            Write-Host "[$($t.TaskName)] FAILED: $_" -ForegroundColor Red
            $failed++
        }
        if ($state.IsBat) {
            Write-Host "  ! action is .bat -- only MultipleInstances was changed; review the .bat for python.exe" -ForegroundColor Magenta
        }
    }
    Write-Host ""
    Write-Host "Summary: applied=$applied  no-change=$skipped  failed=$failed" -ForegroundColor Cyan
}

# ---------------- VERIFY ----------------
if ($Verify) {
    $bad = @()
    $batWarn = @()
    foreach ($t in $tasks) {
        $state = Get-TaskState $t
        $okExe = $state.IsPythonw -or (-not $state.IsPython -and -not $state.IsBat)
        $okMi  = $state.MultipleInstances -eq "IgnoreNew"
        if ($state.IsBat) {
            $batWarn += "[$($t.TaskName)] action is .bat -- manual review needed"
            if (-not $okMi) {
                $bad += "[$($t.TaskName)] MI=$($state.MultipleInstances) (need IgnoreNew)"
            }
            continue
        }
        if (-not ($okExe -and $okMi)) {
            $bad += "[$($t.TaskName)] Execute=$($state.Execute)  MI=$($state.MultipleInstances)"
        }
    }
    if ($batWarn.Count -gt 0) {
        Write-Host "Bat-file actions (manual review for python -> pythonw):" -ForegroundColor Magenta
        $batWarn | ForEach-Object { Write-Host "  $_" }
    }
    if ($bad.Count -eq 0) {
        Write-Host "VERIFY PASS -- all $($tasks.Count) MERDIAN_* tasks have pythonw.exe (or .bat) + IgnoreNew" -ForegroundColor Green
    } else {
        Write-Host "VERIFY FAIL:" -ForegroundColor Red
        $bad | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        exit 1
    }
}
