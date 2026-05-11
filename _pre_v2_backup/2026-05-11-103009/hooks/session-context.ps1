$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
try {
    $branch = (git branch --show-current 2>$null).Trim()
    if (-not $branch) { throw "not a repo" }
    $dirty = (git status --porcelain 2>$null | Where-Object { $_ } | Measure-Object).Count
    $lastCommit = (git log -1 --oneline 2>$null).Trim()
    Write-Output "--- Session Context ---"
    Write-Output "Branch: $branch"
    Write-Output "Dirty files: $dirty"
    Write-Output "Last commit: $lastCommit"
    Write-Output "-----------------------"
} catch {
    Write-Output "Not in a git repository."
}
exit 0
