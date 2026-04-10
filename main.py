"""
DJEN Notificator
================
Consulta diária ao DJEN (comunicaapi.pje.jus.br) por palavras-chave e
envia um e-mail via Outlook quando encontra publicações.

Uso:
    python main.py
    python main.py --data 2024-06-15   # busca em data específica
"""

import sys
import smtplib
import logging
import argparse
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import (
    KEYWORDS,
    EMAIL_FROM, EMAIL_PASSWORD, EMAIL_TO, EMAIL_SUBJECT,
    SMTP_HOST, SMTP_PORT,
    DJEN_API_URL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Consulta à API
# ---------------------------------------------------------------------------

def buscar_publicacoes(keyword: str, data_busca: str) -> list:
    """
    Retorna lista de publicações do DJEN que contenham *keyword* na data
    *data_busca* (formato YYYY-MM-DD).

    Parâmetros aceitos pela API (ajuste conforme documentação oficial):
        dataDisponibilizacao – data de disponibilização
        texto                – texto livre para filtro
        pagina               – índice da página (0-based)
        tamanho              – itens por página
    """
    params = {
        "dataDisponibilizacao": data_busca,
        "texto": keyword,
        "pagina": 0,
        "tamanho": 50,
    }

    try:
        response = requests.get(DJEN_API_URL, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        log.error("HTTP %s ao buscar '%s': %s", exc.response.status_code, keyword, exc)
        return []
    except requests.exceptions.RequestException as exc:
        log.error("Erro de rede ao buscar '%s': %s", keyword, exc)
        return []

    payload = response.json()

    # A API pode retornar a lista diretamente ou aninhada em uma chave.
    # Adapte a chave abaixo conforme o retorno real da API.
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for chave in ("resultado", "content", "data", "publicacoes", "items", "hits"):
            if chave in payload and isinstance(payload[chave], list):
                return payload[chave]
        # resposta é um único objeto
        return [payload] if payload else []

    return []


# ---------------------------------------------------------------------------
# Formatação do e-mail
# ---------------------------------------------------------------------------

def _campo(pub: dict, *chaves, fallback: str = "N/D") -> str:
    """Lê a primeira chave encontrada no dict; retorna *fallback* se nenhuma."""
    for chave in chaves:
        if chave in pub and pub[chave]:
            return str(pub[chave])
    return fallback


def formatar_publicacao_html(pub: dict, indice: int) -> str:
    numero   = _campo(pub, "numeroProcesso", "numero", "id")
    data_pub = _campo(pub, "dataDisponibilizacao", "data", "dataPub")
    tribunal = _campo(pub, "siglaTribunal", "tribunal", "orgaoJulgador", fallback="")
    texto    = _campo(pub, "texto", "conteudo", "descricao", fallback="")

    if len(texto) > 600:
        texto = texto[:600] + "…"

    linhas = [
        f"<strong>#{indice} — Processo:</strong> {numero}<br>",
        f"<strong>Data:</strong> {data_pub}<br>",
    ]
    if tribunal:
        linhas.append(f"<strong>Tribunal:</strong> {tribunal}<br>")
    if texto:
        linhas.append(f"<strong>Trecho:</strong> {texto}")

    return (
        "<div style='border:1px solid #ddd;border-radius:4px;"
        "padding:10px 14px;margin:6px 0;font-family:sans-serif;font-size:14px'>"
        + "".join(linhas)
        + "</div>"
    )


def montar_html(resultados: dict) -> str:
    total = sum(len(v) for v in resultados.values())
    hoje  = date.today().strftime("%d/%m/%Y")

    partes = [
        "<html><body style='font-family:sans-serif;color:#222'>",
        f"<h2 style='color:#1a5276'>DJEN – Publicações encontradas em {hoje}</h2>",
        f"<p><strong>Total:</strong> {total} publicação(ões)</p>",
        "<hr>",
    ]

    for keyword, pubs in resultados.items():
        if not pubs:
            continue
        partes.append(
            f"<h3 style='color:#1f618d'>🔑 Palavra-chave: <em>{keyword}</em>"
            f" — {len(pubs)} resultado(s)</h3>"
        )
        for i, pub in enumerate(pubs, 1):
            partes.append(formatar_publicacao_html(pub, i))

    partes.append(
        "<hr><p style='font-size:12px;color:#888'>"
        "Gerado automaticamente pelo DJEN Notificator.</p>"
        "</body></html>"
    )
    return "".join(partes)


# ---------------------------------------------------------------------------
# Envio de e-mail
# ---------------------------------------------------------------------------

def enviar_email(resultados: dict) -> None:
    if not EMAIL_FROM:
        log.error("EMAIL_FROM não configurado. Defina a variável de ambiente.")
        sys.exit(1)
    if not EMAIL_PASSWORD:
        log.error("EMAIL_PASSWORD não configurado. Defina a variável de ambiente.")
        sys.exit(1)

    msg = MIMEMultipart("alternative")
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg["Subject"] = EMAIL_SUBJECT

    corpo_html = montar_html(resultados)
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    log.info("Conectando ao SMTP %s:%s …", SMTP_HOST, SMTP_PORT)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(EMAIL_FROM, EMAIL_PASSWORD)
        smtp.sendmail(EMAIL_FROM, [EMAIL_TO], msg.as_string())

    log.info("E-mail enviado para %s.", EMAIL_TO)


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Notificador DJEN por palavras-chave")
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data de busca no formato YYYY-MM-DD (padrão: hoje)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    data_busca = args.data

    log.info("=== DJEN Notificator | data: %s ===", data_busca)
    log.info("Palavras-chave: %s", KEYWORDS)

    resultados: dict[str, list] = {}
    for keyword in KEYWORDS:
        log.info("Buscando: '%s' …", keyword)
        pubs = buscar_publicacoes(keyword, data_busca)
        resultados[keyword] = pubs
        log.info("  → %d resultado(s)", len(pubs))

    total = sum(len(v) for v in resultados.values())

    if total == 0:
        log.info("Nenhuma publicação encontrada. E-mail não enviado.")
        sys.exit(0)

    log.info("%d publicação(ões) encontrada(s). Preparando e-mail …", total)
    enviar_email(resultados)


if __name__ == "__main__":
    main()
