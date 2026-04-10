import os

# ---------------------------------------------------------------------------
# Palavras-chave buscadas no DJEN a cada execucao
# ---------------------------------------------------------------------------
KEYWORDS = [
    "Lorena Zucatelli dos Santos",
    "Gilberto Alvares dos Santos",
    "Vinicius Fregonazzi Tavares",
    "Tecbras Empreendimentos Ltda",
    "Spart Participacoes Ltda",
]

# ---------------------------------------------------------------------------
# Email via SendGrid
# No GitHub Actions configure os Secrets: SENDGRID_API_KEY, EMAIL_FROM, EMAIL_TO
# ---------------------------------------------------------------------------
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
EMAIL_FROM       = os.getenv("EMAIL_FROM", "")
EMAIL_TO         = os.getenv("EMAIL_TO", "")
EMAIL_SUBJECT    = "DJEN - Novas publicacoes encontradas"

# ---------------------------------------------------------------------------
# DJEN API
# ---------------------------------------------------------------------------
DJEN_API_URL = "https://comunicaapi.pje.jus.br/api/v1/publicacao"
