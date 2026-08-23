#requires -Version 7.0

param(
    [Parameter(Mandatory = $true)]
    [string] $RuntimePath,

    [Parameter(Mandatory = $true)]
    [string] $AttemptRoot,

    [Parameter(Mandatory = $true)]
    [string] $ExpectedRuntimeSha256
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$RuntimePath = (Resolve-Path -LiteralPath $RuntimePath).Path
$AttemptRoot = (Resolve-Path -LiteralPath $AttemptRoot).Path
$ExpectedRuntimeSha256 = $ExpectedRuntimeSha256.ToUpperInvariant()

function Write-Utf8Json {
    param(
        [Parameter(Mandatory = $true)] [string] $Path,
        [Parameter(Mandatory = $true)] $Value
    )

    $json = $Value | ConvertTo-Json -Depth 30
    [System.IO.File]::WriteAllText($Path, "$json`n", $Utf8NoBom)
}

function Assert-WithinAttempt {
    param([Parameter(Mandatory = $true)] [string] $Path)

    $full = [System.IO.Path]::GetFullPath($Path)
    $prefix = $AttemptRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) +
        [System.IO.Path]::DirectorySeparatorChar
    if (-not $full.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Probe output escaped Attempt root: $full"
    }
    return $full
}

$requiredSegment = [System.IO.Path]::Combine(
    "docs", "workstreams", "huangyi", "open-source-agent-harness-research",
    "validation", "attempts"
)
if ($AttemptRoot.IndexOf(
        $requiredSegment,
        [System.StringComparison]::OrdinalIgnoreCase
    ) -lt 0) {
    throw "AttemptRoot is outside the approved Huang Yi validation workstream"
}

$runtimeHash = (Get-FileHash -LiteralPath $RuntimePath -Algorithm SHA256).Hash.ToUpperInvariant()
if ($runtimeHash -ne $ExpectedRuntimeSha256) {
    throw "Runtime hash mismatch: expected $ExpectedRuntimeSha256, got $runtimeHash"
}

$codexCommonDataRoot = [Environment]::GetFolderPath(
    [Environment+SpecialFolder]::CommonApplicationData
)
if ([string]::IsNullOrWhiteSpace($codexCommonDataRoot)) {
    throw "Unable to resolve the system application-data directory"
}
$codexSystemConfigRoot = Join-Path $codexCommonDataRoot "OpenAI\Codex"
$systemConfigPaths = @(
    "config.toml",
    "requirements.toml",
    "managed_config.toml"
) | ForEach-Object { Join-Path $codexSystemConfigRoot $_ }
$presentSystemConfigs = @($systemConfigPaths | Where-Object { Test-Path -LiteralPath $_ })
if ($presentSystemConfigs.Count -gt 0) {
    throw "System Codex configuration exists; probe stopped before execution"
}

$rawRoot = Assert-WithinAttempt (Join-Path $AttemptRoot "raw")
$schemaRoot = Assert-WithinAttempt (Join-Path $rawRoot "generated-schema")
$stdoutRoot = Assert-WithinAttempt (Join-Path $rawRoot "stdout")
$stderrRoot = Assert-WithinAttempt (Join-Path $rawRoot "stderr")
$networkRoot = Assert-WithinAttempt (Join-Path $rawRoot "network")
$tempRoot = Assert-WithinAttempt (Join-Path $rawRoot "temp-home")
$sanitizedRoot = Assert-WithinAttempt (Join-Path $AttemptRoot "sanitized")

foreach ($path in @(
    $schemaRoot, $stdoutRoot, $stderrRoot, $networkRoot, $tempRoot, $sanitizedRoot
)) {
    [System.IO.Directory]::CreateDirectory($path) | Out-Null
}

function New-IsolatedStartInfo {
    param(
        [Parameter(Mandatory = $true)] [string[]] $Arguments,
        [Parameter(Mandatory = $true)] [string] $ScenarioHome,
        [switch] $Interactive
    )

    $scenarioHome = Assert-WithinAttempt $ScenarioHome
    $scenarioTemp = Assert-WithinAttempt (Join-Path $scenarioHome "temp")
    [System.IO.Directory]::CreateDirectory($scenarioTemp) | Out-Null

    $startInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $RuntimePath
    $startInfo.WorkingDirectory = "$env:SystemRoot\System32"
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.RedirectStandardInput = $Interactive.IsPresent

    foreach ($argument in $Arguments) {
        $startInfo.ArgumentList.Add($argument)
    }

    $startInfo.Environment.Clear()
    $startInfo.Environment["SystemRoot"] = $env:SystemRoot
    $startInfo.Environment["WINDIR"] = $env:WINDIR
    $startInfo.Environment["ComSpec"] = $env:ComSpec
    $startInfo.Environment["PATH"] = "$env:SystemRoot\System32;$env:SystemRoot"
    $startInfo.Environment["PATHEXT"] = ".COM;.EXE;.BAT;.CMD"
    $startInfo.Environment["CODEX_HOME"] = $scenarioHome
    $startInfo.Environment["CODEX_SQLITE_HOME"] = $scenarioHome
    $startInfo.Environment["TEMP"] = $scenarioTemp
    $startInfo.Environment["TMP"] = $scenarioTemp
    foreach ($proxyName in @(
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
        "http_proxy", "https_proxy", "all_proxy"
    )) {
        $startInfo.Environment[$proxyName] = "http://127.0.0.1:9"
    }
    $startInfo.Environment["NO_PROXY"] = ""
    $startInfo.Environment["no_proxy"] = ""
    return $startInfo
}

function Stop-ProbeProcess {
    param([Parameter(Mandatory = $true)] [System.Diagnostics.Process] $Process)

    if (-not $Process.HasExited) {
        $Process.Kill($true)
        $Process.WaitForExit(5000) | Out-Null
    }
}

function Invoke-IsolatedCommand {
    param(
        [Parameter(Mandatory = $true)] [string] $Scenario,
        [Parameter(Mandatory = $true)] [string[]] $Arguments,
        [Parameter(Mandatory = $true)] [string] $ScenarioHome,
        [int] $TimeoutMilliseconds = 20000
    )

    $stdoutPath = Assert-WithinAttempt (Join-Path $stdoutRoot "$Scenario.jsonl")
    $stderrPath = Assert-WithinAttempt (Join-Path $stderrRoot "$Scenario.log")
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = New-IsolatedStartInfo -Arguments $Arguments -ScenarioHome $ScenarioHome
    try {
        if (-not $process.Start()) {
            throw "Failed to start $Scenario"
        }
        $stdoutTask = $process.StandardOutput.ReadToEndAsync()
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if (-not $process.WaitForExit($TimeoutMilliseconds)) {
            Stop-ProbeProcess -Process $process
            throw "$Scenario exceeded ${TimeoutMilliseconds}ms"
        }
        $stdout = $stdoutTask.GetAwaiter().GetResult()
        $stderr = $stderrTask.GetAwaiter().GetResult()
        [System.IO.File]::WriteAllText($stdoutPath, $stdout, $Utf8NoBom)
        [System.IO.File]::WriteAllText($stderrPath, $stderr, $Utf8NoBom)
        if ($process.ExitCode -ne 0) {
            throw "$Scenario exited with code $($process.ExitCode)"
        }
        return [ordered]@{
            scenario = $Scenario
            exit_code = $process.ExitCode
            stdout_file = "raw/stdout/$Scenario.jsonl"
            stderr_file = "raw/stderr/$Scenario.log"
        }
    }
    finally {
        Stop-ProbeProcess -Process $process
        $process.Dispose()
    }
}

function Read-ResponseById {
    param(
        [Parameter(Mandatory = $true)] [System.Diagnostics.Process] $Process,
        [Parameter(Mandatory = $true)] [string] $ExpectedId,
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [System.Collections.Generic.List[string]] $Lines,
        [int] $TimeoutMilliseconds = 10000
    )

    $deadline = [System.DateTimeOffset]::UtcNow.AddMilliseconds($TimeoutMilliseconds)
    while ([System.DateTimeOffset]::UtcNow -lt $deadline) {
        $remaining = [Math]::Max(
            1,
            [int]($deadline - [System.DateTimeOffset]::UtcNow).TotalMilliseconds
        )
        $readTask = $Process.StandardOutput.ReadLineAsync()
        if (-not $readTask.Wait($remaining)) {
            throw "Timed out waiting for response id $ExpectedId"
        }
        $line = $readTask.GetAwaiter().GetResult()
        if ($null -eq $line) {
            throw "App Server closed stdout before response id $ExpectedId"
        }
        $Lines.Add($line)
        $message = $line | ConvertFrom-Json -Depth 50
        if ($null -ne $message.PSObject.Properties["id"] -and
            [string]$message.id -eq $ExpectedId) {
            return $message
        }
    }
    throw "Timed out waiting for response id $ExpectedId"
}

function Invoke-ProtocolScenario {
    param(
        [Parameter(Mandatory = $true)] [string] $Scenario,
        [Parameter(Mandatory = $true)] [string] $ScenarioHome,
        [Parameter(Mandatory = $true)] [ValidateSet("preinit", "handshake", "experimental-gate")]
        [string] $Mode
    )

    $args = @(
        "app-server", "--listen", "stdio://", "--strict-config",
        "-c", "analytics.enabled=false",
        "-c", "feedback.enabled=false",
        "-c", "otel.exporter=`"none`"",
        "-c", "otel.trace_exporter=`"none`"",
        "-c", "otel.metrics_exporter=`"none`"",
        "-c", "check_for_update_on_startup=false",
        "-c", "features.remote_control=false"
    )
    $stdoutPath = Assert-WithinAttempt (Join-Path $stdoutRoot "$Scenario.jsonl")
    $stderrPath = Assert-WithinAttempt (Join-Path $stderrRoot "$Scenario.log")
    $lines = [System.Collections.Generic.List[string]]::new()
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = New-IsolatedStartInfo -Arguments $args -ScenarioHome $ScenarioHome -Interactive
    try {
        if (-not $process.Start()) {
            throw "Failed to start $Scenario"
        }
        $stderrTask = $process.StandardError.ReadToEndAsync()
        if ($Mode -eq "preinit") {
            $process.StandardInput.WriteLine('{"method":"server/diagnostics","id":"rwb-preinit-1","params":{}}')
            $process.StandardInput.Flush()
            $response = Read-ResponseById -Process $process -ExpectedId "rwb-preinit-1" -Lines $lines
            $result = [ordered]@{
                scenario = $Scenario
                error_received = $null -ne $response.PSObject.Properties["error"]
                error_message = [string]$response.error.message
            }
        }
        else {
            $initialize = [ordered]@{
                method = "initialize"
                id = "rwb-init-1"
                params = [ordered]@{
                    clientInfo = [ordered]@{
                        name = "research_agent_workbench_readonly_probe"
                        title = "Research Agent Workbench Read-only Probe"
                        version = "0.1.0"
                    }
                    capabilities = [ordered]@{ experimentalApi = $false }
                }
            } | ConvertTo-Json -Compress -Depth 10
            $process.StandardInput.WriteLine($initialize)
            $process.StandardInput.Flush()
            $initializeResponse = Read-ResponseById -Process $process -ExpectedId "rwb-init-1" -Lines $lines
            if ($null -ne $initializeResponse.PSObject.Properties["error"]) {
                throw "Initialize failed: $($initializeResponse.error.message)"
            }
            $reportedHome = [System.IO.Path]::GetFullPath([string]$initializeResponse.result.codexHome)
            $expectedHome = [System.IO.Path]::GetFullPath($ScenarioHome)
            if (-not $reportedHome.Equals($expectedHome, [System.StringComparison]::OrdinalIgnoreCase)) {
                throw "App Server reported unexpected codexHome"
            }
            $process.StandardInput.WriteLine('{"method":"initialized"}')
            $process.StandardInput.Flush()

            if ($Mode -eq "handshake") {
                $process.StandardInput.WriteLine($initialize.Replace('rwb-init-1', 'rwb-init-duplicate'))
                $process.StandardInput.Flush()
                $duplicate = Read-ResponseById -Process $process -ExpectedId "rwb-init-duplicate" -Lines $lines
                $process.StandardInput.WriteLine('{"method":"rwb/readonly-probe-unsupported","id":"rwb-unknown-1","params":{}}')
                $process.StandardInput.Flush()
                $unknown = Read-ResponseById -Process $process -ExpectedId "rwb-unknown-1" -Lines $lines
                $result = [ordered]@{
                    scenario = $Scenario
                    initialized = $true
                    codex_home_matches_isolated_root = $true
                    result_keys = @($initializeResponse.result.PSObject.Properties.Name | Sort-Object)
                    platform_family = [string]$initializeResponse.result.platformFamily
                    platform_os = [string]$initializeResponse.result.platformOs
                    duplicate_initialize_rejected = $null -ne $duplicate.PSObject.Properties["error"]
                    duplicate_initialize_error_code = [int]$duplicate.error.code
                    duplicate_initialize_error = [string]$duplicate.error.message
                    unknown_method_rejected = $null -ne $unknown.PSObject.Properties["error"]
                    unknown_method_error_code = [int]$unknown.error.code
                    unknown_method_error_class = if (
                        ([string]$unknown.error.message).StartsWith(
                            "Invalid request: unknown variant",
                            [System.StringComparison]::Ordinal
                        )
                    ) { "unknown-variant" } else { "unexpected-error" }
                }
            }
            else {
                $process.StandardInput.WriteLine('{"method":"server/diagnostics","id":"rwb-experimental-1","params":{}}')
                $process.StandardInput.Flush()
                $gated = Read-ResponseById -Process $process -ExpectedId "rwb-experimental-1" -Lines $lines
                $result = [ordered]@{
                    scenario = $Scenario
                    initialized = $true
                    codex_home_matches_isolated_root = $true
                    experimental_api = $false
                    gated_method = "server/diagnostics"
                    gate_error_code = [int]$gated.error.code
                    gate_error = [string]$gated.error.message
                }
            }
        }

        $connections = @(
            Get-NetTCPConnection -OwningProcess $process.Id -ErrorAction SilentlyContinue |
                Select-Object State, LocalAddress, LocalPort, RemoteAddress, RemotePort
        )
        $networkPath = Assert-WithinAttempt (Join-Path $networkRoot "$Scenario.json")
        Write-Utf8Json -Path $networkPath -Value $connections
        $activeRemoteConnections = @(
            $connections | Where-Object {
                $_.RemotePort -gt 0 -and
                $_.RemoteAddress -notin @("0.0.0.0", "::", "127.0.0.1", "::1")
            }
        )
        $result["observed_tcp_connection_count"] = $connections.Count
        $result["observed_tcp_states"] = @(
            $connections | ForEach-Object { $_.State.ToString() } | Sort-Object -Unique
        )
        $result["observed_loopback_proxy_count"] = @(
            $connections | Where-Object {
                $_.RemoteAddress -in @("127.0.0.1", "::1") -and $_.RemotePort -eq 9
            }
        ).Count
        $result["observed_non_loopback_remote_count"] = $activeRemoteConnections.Count
        $process.StandardInput.Close()
        if (-not $process.WaitForExit(5000)) {
            Stop-ProbeProcess -Process $process
            throw "$Scenario did not exit after stdin closed"
        }
        while (-not $process.StandardOutput.EndOfStream) {
            $remainingLine = $process.StandardOutput.ReadLine()
            if ($null -ne $remainingLine) {
                $lines.Add($remainingLine)
            }
        }
        [System.IO.File]::WriteAllLines($stdoutPath, $lines, $Utf8NoBom)
        [System.IO.File]::WriteAllText(
            $stderrPath,
            $stderrTask.GetAwaiter().GetResult(),
            $Utf8NoBom
        )
        $result["exit_code"] = $process.ExitCode
        return $result
    }
    finally {
        Stop-ProbeProcess -Process $process
        $process.Dispose()
    }
}

function Get-MethodConstants {
    param([Parameter(Mandatory = $true)] [string] $Directory)

    $methods = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::Ordinal
    )
    function Visit-JsonNode {
        param($Node)
        if ($null -eq $Node -or $Node -is [string] -or $Node -is [ValueType]) {
            return
        }
        if ($Node -is [System.Collections.IEnumerable] -and
            $Node -isnot [System.Management.Automation.PSCustomObject]) {
            foreach ($item in $Node) { Visit-JsonNode $item }
            return
        }
        $propertiesProperty = $Node.PSObject.Properties["properties"]
        if ($null -ne $propertiesProperty) {
            $methodProperty = $propertiesProperty.Value.PSObject.Properties["method"]
            if ($null -ne $methodProperty) {
                $constProperty = $methodProperty.Value.PSObject.Properties["const"]
                if ($null -ne $constProperty -and $constProperty.Value -is [string]) {
                    $methods.Add([string]$constProperty.Value) | Out-Null
                }
                $enumProperty = $methodProperty.Value.PSObject.Properties["enum"]
                if ($null -ne $enumProperty) {
                    $enumValues = @($enumProperty.Value)
                    if ($enumValues.Count -eq 1 -and $enumValues[0] -is [string]) {
                        $methods.Add([string]$enumValues[0]) | Out-Null
                    }
                }
            }
        }
        foreach ($property in $Node.PSObject.Properties) {
            Visit-JsonNode $property.Value
        }
    }

    foreach ($file in Get-ChildItem -LiteralPath $Directory -Recurse -File -Filter "*.json") {
        Visit-JsonNode (Get-Content -LiteralPath $file.FullName -Raw | ConvertFrom-Json -Depth 100)
    }
    return @($methods | Sort-Object)
}

$baseConfigArgs = @(
    "app-server",
    "-c", "analytics.enabled=false",
    "-c", "feedback.enabled=false",
    "-c", "otel.exporter=`"none`"",
    "-c", "otel.trace_exporter=`"none`"",
    "-c", "otel.metrics_exporter=`"none`"",
    "-c", "check_for_update_on_startup=false",
    "-c", "features.remote_control=false",
    "generate-json-schema"
)

$stableSchema = Assert-WithinAttempt (Join-Path $schemaRoot "stable")
$experimentalSchema = Assert-WithinAttempt (Join-Path $schemaRoot "experimental")
foreach ($directory in @($stableSchema, $experimentalSchema)) {
    if ((Test-Path -LiteralPath $directory) -and
        @(Get-ChildItem -LiteralPath $directory -Force).Count -gt 0) {
        throw "Attempt is immutable; schema output already exists: $directory"
    }
    [System.IO.Directory]::CreateDirectory($directory) | Out-Null
}

$schemaHome = Assert-WithinAttempt (Join-Path $tempRoot "schema")
$commandResults = @()
$commandResults += Invoke-IsolatedCommand `
    -Scenario "schema-stable" `
    -ScenarioHome $schemaHome `
    -Arguments ($baseConfigArgs + @("--out", $stableSchema))
$commandResults += Invoke-IsolatedCommand `
    -Scenario "schema-experimental" `
    -ScenarioHome $schemaHome `
    -Arguments ($baseConfigArgs + @("--out", $experimentalSchema, "--experimental"))

$stableMethods = @(Get-MethodConstants -Directory $stableSchema)
$experimentalMethods = @(Get-MethodConstants -Directory $experimentalSchema)
$experimentalOnly = @($experimentalMethods | Where-Object { $_ -notin $stableMethods })

$preinitResult = Invoke-ProtocolScenario `
    -Scenario "protocol-preinit" `
    -ScenarioHome (Assert-WithinAttempt (Join-Path $tempRoot "preinit")) `
    -Mode "preinit"
$handshakeResult = Invoke-ProtocolScenario `
    -Scenario "protocol-handshake" `
    -ScenarioHome (Assert-WithinAttempt (Join-Path $tempRoot "handshake")) `
    -Mode "handshake"

if ("server/diagnostics" -in $experimentalOnly) {
    $experimentalGateResult = Invoke-ProtocolScenario `
        -Scenario "protocol-experimental-gate" `
        -ScenarioHome (Assert-WithinAttempt (Join-Path $tempRoot "experimental-gate")) `
        -Mode "experimental-gate"
}
else {
    $experimentalGateResult = [ordered]@{
        scenario = "protocol-experimental-gate"
        performed = $false
        capture_gap = "server/diagnostics was not proven experimental-only by generated schemas"
    }
}

$schemaBundles = @()
$keySchemaFiles = @()
foreach ($bundle in @(
    [ordered]@{ name = "stable"; root = $stableSchema },
    [ordered]@{ name = "experimental"; root = $experimentalSchema }
)) {
    $bundleRecords = @()
    $bundleBytes = 0
    foreach ($file in Get-ChildItem -LiteralPath $bundle.root -Recurse -File | Sort-Object FullName) {
        $relative = [System.IO.Path]::GetRelativePath($schemaRoot, $file.FullName).Replace("\", "/")
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        $bundleRecords += "$relative`t$hash`t$($file.Length)"
        $bundleBytes += $file.Length
        if ($file.DirectoryName -eq $bundle.root -and $file.Name -in @(
            "ClientRequest.json", "codex_app_server_protocol.schemas.json"
        )) {
            $keySchemaFiles += [ordered]@{
                path = $relative
                sha256 = $hash
                bytes = $file.Length
            }
        }
    }
    $bundleManifest = ($bundleRecords -join "`n") + "`n"
    $bundleDigestBytes = [System.Security.Cryptography.SHA256]::HashData(
        $Utf8NoBom.GetBytes($bundleManifest)
    )
    $schemaBundles += [ordered]@{
        name = $bundle.name
        file_count = $bundleRecords.Count
        total_bytes = $bundleBytes
        manifest_sha256 = [System.Convert]::ToHexString($bundleDigestBytes).ToLowerInvariant()
    }
}

$schemaSummary = [ordered]@{
    schema = "rwb.codex-app-server-schema-summary.v1"
    runtime = [ordered]@{
        version = (& $RuntimePath --version).Trim()
        sha256 = $runtimeHash.ToLowerInvariant()
    }
    stable_method_count = $stableMethods.Count
    experimental_method_count = $experimentalMethods.Count
    experimental_only_methods = $experimentalOnly
    bundles = $schemaBundles
    key_files = $keySchemaFiles
}
$protocolSummary = [ordered]@{
    schema = "rwb.codex-app-server-readonly-probe.v1"
    safety = [ordered]@{
        model_requests_sent = 0
        thread_methods_sent = 0
        turn_methods_sent = 0
        tool_methods_sent = 0
        proxy_fail_closed_guard = "127.0.0.1:9"
        os_network_block_proven = $false
        external_write_absence_proven = $false
    }
    preinitialize = $preinitResult
    handshake = $handshakeResult
    experimental_gate = $experimentalGateResult
}

Write-Utf8Json -Path (Assert-WithinAttempt (Join-Path $sanitizedRoot "schema-summary.json")) -Value $schemaSummary
Write-Utf8Json -Path (Assert-WithinAttempt (Join-Path $sanitizedRoot "protocol-summary.json")) -Value $protocolSummary
Write-Utf8Json -Path (Assert-WithinAttempt (Join-Path $sanitizedRoot "command-results.json")) -Value $commandResults

$tempArchive = Assert-WithinAttempt (Join-Path $rawRoot "temp-home.zip")
if (Test-Path -LiteralPath $tempArchive) {
    throw "Attempt is immutable; temp-home archive already exists: $tempArchive"
}
[System.IO.Compression.ZipFile]::CreateFromDirectory(
    $tempRoot,
    $tempArchive,
    [System.IO.Compression.CompressionLevel]::Optimal,
    $false
)
$archive = [System.IO.Compression.ZipFile]::OpenRead($tempArchive)
try {
    if ($archive.Entries.Count -eq 0) {
        throw "temp-home archive contains no entries"
    }
}
finally {
    $archive.Dispose()
}
$tempArchiveHash = (
    Get-FileHash -LiteralPath $tempArchive -Algorithm SHA256
).Hash.ToLowerInvariant()
$verifiedTempRoot = Assert-WithinAttempt $tempRoot
[System.IO.Directory]::Delete($verifiedTempRoot, $true)

[ordered]@{
    runtime_sha256 = $runtimeHash.ToLowerInvariant()
    stable_methods = $stableMethods.Count
    experimental_methods = $experimentalMethods.Count
    experimental_only_methods = $experimentalOnly.Count
    handshake_exit_code = $handshakeResult.exit_code
    temp_home_archive_sha256 = $tempArchiveHash
    raw_root = "raw/"
    sanitized_root = "sanitized/"
} | ConvertTo-Json -Depth 10
