# ===========================================================
# GHOSH_ROBOTICS :: AUTO-HEAL + DOCKER + GITHUB + TELEGRAM + SCHEDULER + AUTO-UPDATE (v10.3)
# ===========================================================

$ErrorActionPreference = "Stop"

# --- CONFIGURATION ---
$container      = "confident_kepler"
$dockerhubUser  = "dainkthief"
$dockerhubRepo  = "ghosh_robotics_backend"
$dockerhubTag   = "latest"
$repoPath       = "C:\Users\ADMIN\Documents\ZBOTv2.1"
$scriptPath     = "C:\GHOSH_ROBOTICS\docker_log_push.ps1"
$logDir         = "$repoPath\logs"
$localErrorLog  = "C:\GHOSH_ROBOTICS\autoheal_error.log"

# --- TELEGRAM SETTINGS ---
$telegramToken  = "8222543553:AAH-_rEWroqdEicXs24sDwxo829EZRYoooU"
$telegramChatId = "7660068167"
$telegramUrl    = "https://api.telegram.org/bot$telegramToken/sendMessage"

function Send-Telegram($msg) {
    try { Invoke-RestMethod -Uri $telegramUrl -Method POST -Body @{ chat_id = $telegramChatId; text = $msg } | Out-Null }
    catch { Write-Host "[Telegram Error] $($_.Exception.Message)" }
}

# ===========================================================
# 0. SELF-UPDATE SECTION
# ===========================================================
try {
    $rawUrl = "https://raw.githubusercontent.com/dainkthief/ZBOTv2.1/main/docker_log_push.ps1"
    $latest = "$env:TEMP\docker_log_push_latest.ps1"
    Invoke-WebRequest -Uri $rawUrl -OutFile $latest -UseBasicParsing

    $localHash  = (Get-FileHash -Algorithm SHA256 $scriptPath).Hash
    $remoteHash = (Get-FileHash -Algorithm SHA256 $latest).Hash

    if ($localHash -ne $remoteHash) {
        Copy-Item $latest $scriptPath -Force
        Send-Telegram "🔄 Auto-Heal script updated from GitHub repo."
    } else {
        Write-Host "No update needed."
    }
    Remove-Item $latest -Force
} catch {
    Write-Host "Auto-update skipped: $($_.Exception.Message)"
}

# ===========================================================
# 1. DOCKER HEALTH
# ===========================================================
try {
    $status = docker inspect -f "{{.State.Status}}" $container 2>$null
    if ($status -ne "running") {
        Send-Telegram "⚠️ Container $container not running. Restarting..."
        Restart-Service docker -Force
        Start-Sleep -Seconds 15
        docker start $container | Out-Null
        Send-Telegram "✅ Container $container restarted successfully."
    }
} catch {
    $msg = "❌ Docker/container error: $($_.Exception.Message)"
    Add-Content -Path $localErrorLog -Value $msg
    Send-Telegram $msg
}

# ===========================================================
# 2. EXPORT LOGS
# ===========================================================
try {
    if (!(Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
    $logFile = "$logDir\docker_backend_$(Get-Date -Format 'yyyyMMdd_HHmm').log"
    docker logs $container > $logFile 2>&1
    Send-Telegram "🧾 Logs exported from $container"
} catch {
    $err = "❌ Log export failed: $($_.Exception.Message)"
    Add-Content -Path $localErrorLog -Value $err
    Send-Telegram $err
}

# ===========================================================
# 3. GIT SYNC + PUSH
# ===========================================================
try {
    Set-Location $repoPath
    git fetch origin main
    git rebase origin/main 2>&1 | Out-Null
    git add logs
    git commit -m "Auto log push $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" --allow-empty | Out-Null
    git push origin main 2>&1 | Out-String | Tee-Object -Variable PushResult | Out-Null
    Send-Telegram "✅ Logs pushed successfully to GitHub (main)."
} catch {
    $err = "❌ Git push error: $($_.Exception.Message)"
    Add-Content -Path $localErrorLog -Value $err
    Send-Telegram $err
}

# ===========================================================
# 4. TRIGGER GITHUB WORKFLOW
# ===========================================================
try {
    $token = $env:GITHUB_TOKEN
    if (-not $token) { $token = "ghp_your_token_here" }
    $workflowUrl = "https://api.github.com/repos/dainkthief/ZBOTv2.1/actions/workflows/blank.yml/dispatches"
    $payload = @{ ref = "main" } | ConvertTo-Json
    Invoke-RestMethod -Uri $workflowUrl -Method POST -Headers @{
        Authorization = "token $token"
        Accept        = "application/vnd.github+json"
        "User-Agent"  = "Auto-Heal"
    } -Body $payload
    Send-Telegram "🚀 GitHub workflow triggered successfully."
} catch {
    $msg = "⚠️ Workflow trigger failed: $($_.Exception.Message)"
    Add-Content -Path $localErrorLog -Value $msg
    Send-Telegram $msg
}

# ===========================================================
# 5. DOCKER IMAGE BACKUP
# ===========================================================
try {
$backupTag = "${dockerhubUser}/${dockerhubRepo}:${dockerhubTag}"
    $dockerToken = $env:DOCKERHUB_TOKEN
    if (-not $dockerToken) {
        Send-Telegram "⚠️ No DOCKERHUB_TOKEN found. Skipping push."
    } else {
        docker commit $container $backupTag | Out-Null
        docker login -u $dockerhubUser -p $dockerToken | Out-Null
        docker push $backupTag | Out-Null
        Send-Telegram "☁️ Image pushed to Docker Hub ($backupTag)"
    }
} catch {
    $msg = "❌ Docker image backup failed: $($_.Exception.Message)"
    Add-Content -Path $localErrorLog -Value $msg
    Send-Telegram $msg
}

# ===========================================================
# 6. FINAL MESSAGE
# ===========================================================
Send-Telegram "✅ Auto-Heal v10.3 cycle complete on $(hostname) at $(Get-Date -Format 'HH:mm:ss')"
Write-Host "Cycle complete at $(Get-Date -Format 'HH:mm:ss')"
