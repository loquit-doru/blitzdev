# setup_foxmq.ps1 — Start the FoxMQ broker for local swarm development
#
# FoxMQ is a Rust MQTT 5.0 broker powered by Tashi Vertex BFT consensus.
# All swarm agents connect to this broker (localhost:1883) instead of
# direct ZMQ sockets. Vertex orders messages before delivery, so every
# agent sees the EXACT same event sequence.
#
# Usage (from flashforge/ root):
#   .\swarm\setup_foxmq.ps1
#
# Prerequisites:
#   foxmq.exe must be in the flashforge/ root directory.
#   If missing, download from:
#   https://github.com/tashigit/foxmq/releases/tag/v0.3.1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot   # flashforge/ root

$FoxmqBin  = Join-Path $Root "foxmq.exe"
$FoxmqDir  = Join-Path $Root "foxmq.d"
$KeyFile   = Join-Path $FoxmqDir "key_0.pem"
$AddrBook  = Join-Path $FoxmqDir "address-book.toml"

# ── 1. Check binary ────────────────────────────────────────────────────────────
if (-not (Test-Path $FoxmqBin)) {
    Write-Error "foxmq.exe not found at $FoxmqBin`nDownload from: https://github.com/tashigit/foxmq/releases/tag/v0.3.1"
    exit 1
}

# ── 2. Generate address book (single local node) if not present ───────────────
if (-not (Test-Path $KeyFile)) {
    Write-Host "Generating FoxMQ address book (single local node)..." -ForegroundColor Cyan
    Push-Location $Root
    & $FoxmqBin address-book from-range 127.0.0.1 19793 19793
    Pop-Location
    Write-Host "  → Created $KeyFile" -ForegroundColor Green
    Write-Host "  → Created $AddrBook" -ForegroundColor Green
} else {
    Write-Host "FoxMQ address book already present — skipping generation." -ForegroundColor Gray
}

# ── 3. Start broker ────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Starting FoxMQ broker..." -ForegroundColor Cyan
Write-Host "  MQTT  port : 1883  (agents connect here)"
Write-Host "  Vertex UDP : 19793 (BFT consensus)"
Write-Host "  Auth       : anonymous (--allow-anonymous-login)"
Write-Host ""
Write-Host "Press Ctrl+C to stop.`n" -ForegroundColor Yellow

Push-Location $Root
& $FoxmqBin run --secret-key-file="$KeyFile" --allow-anonymous-login
Pop-Location
