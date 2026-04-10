import os

# ---------------------------------------------------------------------------
# Palavras-chave buscadas no DJEN a cada execução
# Adicione nomes de partes, CPF, CNPJ, número de processo, etc.
# ---------------------------------------------------------------------------
KEYWORDS = [
    "Exemplo Empresa Ltda",
    "12.345.678/0001-99",
]

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
# Remetente e senha vêm de variáveis de ambiente para não expor credenciais.
# No GitHub Actions configure os Secrets: EMAIL_FROM e EMAIL_PASSWORD.
EMAIL_FROM     = os.getenv("EMAIL_FROM", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

# Destinatário pode ficar aqui ou também vir de variável de ambiente.
EMAIL_TO      = os.getenv("EMAIL_TO", "destinatario@email.com")
EMAIL_SUBJECT = "DJEN – Novas publicações encontradas"

SMTP_HOST = "smtp.office365.com"
SMTP_PORT = 587

# ---------------------------------------------------------------------------
# DJEN API
# Endpoint público do CNJ para consulta de publicações.
# Documentação: https://comunicaapi.pje.jus.br/swagger-ui.html
# ---------------------------------------------------------------------------
DJEN_API_URL = "https://comunicaapi.pje.jus.br/api/v1/publicacao"
