$data = [Console]::In.ReadToEnd() | ConvertFrom-Json
$cmd = $data.tool_input.command
if (-not $cmd) { exit 0 }

$patterns = @(
    'rm\s+-rf\s+/\*?(\s|$)',
    '(?i)DROP\s+(TABLE|DATABASE)\b',
    '(?i)\bgit\b.*\bpush\b.*(\s--force\b|\s-f\b)',
    '(?i)\bFormat-Volume\b',
    '(?i)(^|\s)shutdown(\s|$)'
)

foreach ($pattern in $patterns) {
    if ($cmd -match $pattern) {
        [Console]::Error.WriteLine("BLOCKED: dangerous command detected. Pattern: $pattern")
        exit 2
    }
}
exit 0
