#
# XFactor Bot - Zombie Process Cleanup Script (Windows)
# Cleans up any orphaned backend processes
#
# Usage: .\cleanup_zombies.ps1
#
# Run as Administrator for full cleanup capability
#

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "XFactor Bot - Zombie Process Cleanup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$foundProcesses = $false

# Function to kill processes by name
function Kill-ByName {
    param([string]$processName)
    
    $processes = Get-Process -Name $processName -ErrorAction SilentlyContinue
    
    if ($processes) {
        Write-Host "Found $processName processes:" -ForegroundColor Yellow
        $processes | ForEach-Object {
            Write-Host "  PID: $($_.Id) - $($_.ProcessName)" -ForegroundColor White
        }
        $script:foundProcesses = $true
        
        Write-Host "Killing processes..." -ForegroundColor Red
        $processes | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-Host "Done" -ForegroundColor Green
        Write-Host ""
    }
}

# Function to kill processes by port
function Kill-ByPort {
    param([int]$port)
    
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    
    if ($connections) {
        Write-Host "Found processes on port $port:" -ForegroundColor Yellow
        $connections | ForEach-Object {
            $proc = Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue
            if ($proc) {
                Write-Host "  PID: $($proc.Id) - $($proc.ProcessName)" -ForegroundColor White
            }
        }
        $script:foundProcesses = $true
        
        Write-Host "Killing processes..." -ForegroundColor Red
        $connections | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
        Write-Host "Done" -ForegroundColor Green
        Write-Host ""
    }
}

Write-Host "Checking for zombie XFactor processes..." -ForegroundColor Cyan
Write-Host ""

# Kill xfactor-backend processes
Kill-ByName "xfactor-backend"

# Kill python processes that might be running the backend
$pythonProcs = Get-Process -Name "python*" -ErrorAction SilentlyContinue | 
    Where-Object { $_.MainWindowTitle -like "*xfactor*" -or $_.Path -like "*xfactor*" }

if ($pythonProcs) {
    Write-Host "Found XFactor Python processes:" -ForegroundColor Yellow
    $pythonProcs | ForEach-Object {
        Write-Host "  PID: $($_.Id)" -ForegroundColor White
    }
    $foundProcesses = $true
    $pythonProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "Done" -ForegroundColor Green
    Write-Host ""
}

# Kill processes on port 9876 (backend API)
Write-Host "Checking port 9876 (Backend API)..." -ForegroundColor Cyan
Kill-ByPort 9876

# Kill processes on port 5173 (Vite dev server)
Write-Host "Checking port 5173 (Vite Dev Server)..." -ForegroundColor Cyan
Kill-ByPort 5173

# Kill processes on port 3000 (alternate frontend)
Write-Host "Checking port 3000 (Alternate Frontend)..." -ForegroundColor Cyan
Kill-ByPort 3000

# Kill XFactor Bot app if running
Kill-ByName "XFactor Bot"
Kill-ByName "xfactor-bot"

# Summary
Write-Host "==========================================" -ForegroundColor Cyan
if ($foundProcesses) {
    Write-Host "Cleanup completed! All zombie processes killed." -ForegroundColor Green
} else {
    Write-Host "No zombie processes found. System is clean." -ForegroundColor Green
}
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verify ports are free
Write-Host "Verifying ports are free..." -ForegroundColor Cyan

$port9876 = Get-NetTCPConnection -LocalPort 9876 -ErrorAction SilentlyContinue
if ($port9876) {
    Write-Host "Warning: Port 9876 is still in use" -ForegroundColor Red
} else {
    Write-Host "Port 9876: Free" -ForegroundColor Green
}

$port5173 = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
if ($port5173) {
    Write-Host "Note: Port 5173 is in use (dev server may be running)" -ForegroundColor Yellow
} else {
    Write-Host "Port 5173: Free" -ForegroundColor Green
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Cyan

