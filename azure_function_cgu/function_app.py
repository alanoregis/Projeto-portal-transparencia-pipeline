import logging
import azure.functions as func
import requests

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

CGU_BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"

@app.route(route="cgu_proxy", methods=["GET"])
def cgu_proxy(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Recebida chamada no gateway cgu_proxy da Azure Function (São Paulo).")

    # 1. Endpoint desejado (default: /cartoes)
    endpoint = req.params.get("endpoint", "/cartoes")
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    url = f"{CGU_BASE_URL}{endpoint}"

    # 2. Encaminha query params (ignorando o parâmetro interno 'endpoint')
    params = {k: v for k, v in req.params.items() if k != "endpoint"}

    # 3. Autenticação e Headers de navegador
    api_key = req.headers.get("chave-api-dados") or req.params.get("api_key")
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }
    if api_key:
        headers["chave-api-dados"] = api_key

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=60)
        return func.HttpResponse(
            body=resp.content,
            status_code=resp.status_code,
            mimetype="application/json"
        )
    except Exception as exc:
        logging.error(f"Erro na ponte HTTP da Azure Function: {exc}")
        return func.HttpResponse(
            body=f'{{"error": "Falha na ponte Azure Function: {str(exc)}"}}',
            status_code=502,
            mimetype="application/json"
        )
