$tasks = @(
    "MERDIAN_Market_Tape_1M",
    "MERDIAN_Option_Snapshot_Intraday",
    "MERDIAN_State_Stack_5M"
)

foreach ($task in $tasks) {
    $state = (Get-ScheduledTask -TaskName $task).State

    if ($state -ne "Running") {
        Write-Output "$(Get-Date) - Restarting $task"
        Start-ScheduledTask -TaskName $task
    }
}