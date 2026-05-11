$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
try {
    $branch = (git branch --show-current 2>$null).Trim()
} catch {
    exit 0
}
if (-not $branch) { exit 0 }
if ($branch -match '(?i)^(main|master|release|prod)$') {
    [Console]::Error.WriteLine("BLOCKED: direct edits on protected branch '$branch' are not allowed. Switch to a feature branch first.")
    exit 2
}
exit 0
