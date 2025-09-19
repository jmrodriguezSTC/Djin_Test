# Script de PowerShell (wsus_info.ps1)
# Establece el manejo de errores para que los errores de terminación se consideren fatales
$ErrorActionPreference = "Stop"

try {
    # Importa el módulo de WSUS.
    Import-Module UpdateServices
    
    # Obtiene información de las actualizaciones y la convierte a JSON.
    $updates = Get-WsusUpdate -Approval Unapproved | Select-Object Title, KnowledgebaseArticles, RevisionNumber

    # Convierte el objeto a JSON y lo imprime.
    $json_output = $updates | ConvertTo-Json
    Write-Host $json_output

}
catch {
    # Si hay un error, imprime un objeto JSON con el mensaje de error.
    # Esto asegura que la salida SIEMPRE sea JSON.
    $error_info = @{
        "status"  = "error";
        "message" = $_.Exception.Message;
    }
    Write-Host ($error_info | ConvertTo-Json)
}