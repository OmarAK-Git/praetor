#Requires -Version 5.1
<#
.SYNOPSIS
  Validate committed fixture manifest checksums and optionally ingest fixtures into Splunk HEC.

.DESCRIPTION
  TASK-033 Splunk demo harness. Always validates fixture paths + sha256 from
  tests/fixtures/fixture_manifest.yaml. With -SplunkHost and -HecToken, posts
  flattened JSON events with WinEventLog source values expected by compiled SPL.
#>
[CmdletBinding()]
param(
    [switch]$ValidateOnly,
    [string]$RepoRoot = "",
    [string]$SplunkHost = "",
    [string]$HecToken = "",
    [string]$Index = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    param([string]$Override)
    if ($Override) { return (Resolve-Path $Override).Path }
    return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Test-FixtureManifest {
    param(
        [string]$Root,
        [switch]$RequireFiles
    )

    $manifestPath = Join-Path $Root "tests/fixtures/fixture_manifest.yaml"
    if (-not (Test-Path $manifestPath)) {
        throw "fixture manifest not found: $manifestPath"
    }

    $raw = Get-Content -Path $manifestPath -Raw -Encoding UTF8
    $manifest = ConvertFrom-Yaml $raw
    if (-not $manifest.fixtures) {
        throw "fixture manifest missing fixtures list"
    }

    foreach ($entry in $manifest.fixtures) {
        $rel = [string]$entry.path
        if (-not $rel) { throw "fixture entry missing path" }
        $fixturePath = Join-Path $Root ($rel -replace "^fixtures/", "tests/fixtures/")
        if ($RequireFiles -and -not (Test-Path $fixturePath)) {
            throw "fixture file missing: $fixturePath"
        }
        if (-not (Test-Path $fixturePath)) {
            throw "fixture file missing: $fixturePath"
        }
        $expected = [string]$entry.sha256
        if (-not $expected) { throw "fixture entry missing sha256 for $rel" }
        $hash = (Get-FileHash -Path $fixturePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($hash -ne $expected.ToLowerInvariant()) {
            throw (
                "checksum mismatch for ${rel}: expected $expected actual $hash"
            )
        }
        Write-Verbose "validated $rel ($hash)"
    }

    Write-Host "Validated $($manifest.fixtures.Count) fixture(s) from fixture_manifest.yaml"
}

function ConvertTo-SplunkEvent {
    param([hashtable]$Event)

    $repoRoot = Get-RepoRoot -Override $RepoRoot
    $python = (Get-Command python -ErrorAction Stop).Source
    $flattenScript = Join-Path $repoRoot "tools/fixture_events.py"
    $json = $Event | ConvertTo-Json -Depth 20 -Compress
    $flatJson = $json | & $python $flattenScript flatten
    if ($LASTEXITCODE -ne 0) {
        throw "flatten_fixture_event failed for record_id=$($Event.record_id)"
    }
    return ($flatJson | ConvertFrom-Json)
}

function Send-SplunkEvents {
    param(
        [string]$Root,
        [string]$HostUrl,
        [string]$Token,
        [string]$TargetIndex
    )

    if (-not $HostUrl -or -not $Token) {
        throw "Splunk ingest requires -SplunkHost and -HecToken"
    }

    $manifestPath = Join-Path $Root "tests/fixtures/fixture_manifest.yaml"
    $manifest = ConvertFrom-Yaml (Get-Content -Path $manifestPath -Raw -Encoding UTF8)
    $headers = @{
        Authorization = "Splunk $Token"
    }
    $uri = ($HostUrl.TrimEnd("/") + "/services/collector/event")

    $sent = 0
    foreach ($entry in $manifest.fixtures) {
        $fixturePath = Join-Path $Root (($entry.path -replace "^fixtures/", "tests/fixtures/"))
        $payload = Get-Content -Path $fixturePath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($event in $payload.events) {
            $splunkEvent = ConvertTo-SplunkEvent -Event $event
            $body = @{
                index = $TargetIndex
                sourcetype = "_json"
                source = [string]$splunkEvent.source
                time = [double][DateTimeOffset]::Parse([string]$splunkEvent["@timestamp"]).ToUnixTimeSeconds()
                event = $splunkEvent
            } | ConvertTo-Json -Depth 20 -Compress

            Invoke-RestMethod -Method Post -Uri $uri -Headers $headers -Body $body -ContentType "application/json" | Out-Null
            $sent++
        }
    }

    Write-Host "Ingested $sent event(s) into Splunk index '$TargetIndex'"
}

# Minimal YAML loader for the fixture manifest (mapping-only, no anchors).
function ConvertFrom-Yaml {
    param([string]$InputObject)
    $lines = $InputObject -split "`r?`n"
    $root = @{ fixtures = @() }
    $current = $null
    foreach ($line in $lines) {
        if ($line -match '^\s*-\s+path:\s*(.+)$') {
            $current = @{ path = $Matches[1].Trim().Trim('"').Trim("'") }
            $root.fixtures += $current
            continue
        }
        if ($null -ne $current -and $line -match '^\s+sha256:\s*(.+)$') {
            $current.sha256 = $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    if ($root.fixtures.Count -eq 0) {
        throw "failed to parse fixture manifest YAML"
    }
    return $root
}

$rootPath = Get-RepoRoot -Override $RepoRoot
Test-FixtureManifest -Root $rootPath -RequireFiles

if ($ValidateOnly) {
    Write-Host "ValidateOnly complete - fixture paths and checksums OK"
    exit 0
}

if (-not $SplunkHost -or -not $HecToken) {
    throw 'Provide -SplunkHost and -HecToken for ingest, or use -ValidateOnly'
}

Send-SplunkEvents -Root $rootPath -HostUrl $SplunkHost -Token $HecToken -TargetIndex $Index
