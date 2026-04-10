"""
DJEN Notificator
================
Consulta diaria ao DJEN (comunicaapi.pje.jus.br) por palavras-chave e
envia um e-mail via SendGrid quando encontra publicacoes.

Uso:
    python main.py
    python main.py --data 2024-06-15   # busca em data especifica
"""

import sys
import json
import logging
import argparse
from datetime import date

import requests

from config import (
    KEYWORDS,
    SENDGRID_API_KEY,
    EMAIL_FROM, EMAIL_TO, EMAIL_SUBJECT,
    DJEN_API_URL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Consulta a API
# ---------------------------------------------------------------------------

def buscar_publicacoes(keyword: str, data_busca: str) -> list:
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

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        for chave in ("resultado", "content", "data", "publicacoes", "items", "hits"):
            if chave in payload and isinstance(payload[chave], list):
                return payload[chave]
        return [payload] if payload else []

    return []


# ---------------------------------------------------------------------------
# Formatacao do e-mail
# ---------------------------------------------------------------------------

def _campo(pub: dict, *chaves, fallback: str = "N/D") -> str:
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
        texto = texto[:600] + "..."

    linhas = [
        f"<strong>#{indice} - Processo:</strong> {numero}<br>",
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
        f"<h2 style='color:#1a5276'>DJEN - Publicacoes encontradas em {hoje}</h2>",
        f"<p><strong>Total:</strong> {total} publicacao(oes)</p>",
        "<hr>",
    ]

    for keyword, pubs in resultados.items():
        if not pubs:
            continue
        partes.append(
            f"<h3 style='color:#1f618d'>Palavra-chave: <em>{keyword}</em>"
            f" - {len(pubs)} resultado(s)</h3>"
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
# Envio de e-mail via SendGrid
# ---------------------------------------------------------------------------

def enviar_email(resultados: dict) -> None:
    if not SENDGRID_API_KEY:
        log.error("SENDGRID_API_KEY nao configurado. Defina a variavel de ambiente.")
        sys.exit(1)

    corpo_html = montar_html(resultados)

    payload = {
        "personalizations": [{"to": [{"email": EMAIL_TO}]}],
        "from": {"email": EMAIL_FROM},
        "subject": EMAIL_SUBJECT,
        "content": [{"type": "text/html", "value": corpo_html}],
    }

    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json",
    }

    log.info("Enviando e-mail via SendGrid para %s ...", EMAIL_TO)
    try:
        response = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers=headers,
            data=json.dumps(payload),
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        log.error("Erro ao enviar e-mail: %s - %s", exc.response.status_code, exc.response.text)
        sys.exit(1)

    log.info("E-mail enviado com sucesso para %s.", EMAIL_TO)


# ---------------------------------------------------------------------------
# Entrada principal
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="Notificador DJEN por palavras-chave")
    parser.add_argument(
        "--data",
        default=date.today().isoformat(),
        help="Data de busca no formato YYYY-MM-DD (padrao: hoje)",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    data_busca = args.data

    log.info("=== DJEN Notificator | data: %s ===", data_busca)
    log.info("Palavras-chave: %s", KEYWORDS)

    resultados: dict[str, list] = {}
    for keyword in KEYWORDS:
        log.info("Buscando: '%s' ...", keyword)
        pubs = buscar_publicacoes(keyword, data_busca)
        resultados[keyword] = pubs
        log.info("  -> %d resultado(s)", len(pubs))

    total = sum(len(v) for v in resultados.values())

    if total == 0:
        log.info("Nenhuma publicacao encontrada. E-mail nao enviado.")
        sys.exit(0)

    log.info("%d publicacao(oes) encontrada(s). Preparando e-mail ...", total)
    enviar_email(resultados)


if __name__ == "__main__":
    main()
