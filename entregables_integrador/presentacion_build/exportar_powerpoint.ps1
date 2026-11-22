param([string]$Revision = 'v1')
$ErrorActionPreference = 'Stop'
$taskDir = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$pptxPath = Join-Path $taskDir "validated\$Revision\final.pptx"
$pdfPath = Join-Path $taskDir "validated\$Revision\final.pdf"
$renderDir = Join-Path $taskDir "office-$Revision"
New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
$powerpoint = New-Object -ComObject PowerPoint.Application
$deck = $null
try {
    $deck = $powerpoint.Presentations.Open($pptxPath, -1, 0, 0)
    $deck.SaveAs($pdfPath, 32)
    $deck.Export($renderDir, 'PNG', 1600, 900)
    Write-Output "PDF exportado: $pdfPath"
    Write-Output "Láminas: $($deck.Slides.Count)"
} finally {
    if ($null -ne $deck) { $deck.Close(); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($deck) }
    $powerpoint.Quit()
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($powerpoint)
}
