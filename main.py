import requests
from requests.auth import HTTPBasicAuth
from fastapi import FastAPI

app = FastAPI()

@app.get("/test")
def test():
    return {"status": "AI server working"}

@app.post("/analyze_sales")
def analyze_sales(data: dict):

    revenue = data.get("revenue", 0)
    previous = data.get("previous_revenue", 0)

    change = 0
    if previous > 0:
        change = (revenue - previous) / previous * 100

    result = {
        "summary": f"Изменение выручки: {round(change,2)}%",
        "risk": "Падение продаж" if change < -10 else "Риски не обнаружены",
        "recommendation": "Проверьте динамику клиентов"
    }

    return result
import requests
from requests.auth import HTTPBasicAuth

ODATA_URL = "https://1cfresh.kz/a/ea8/239226/odata/standard.odata/"
ODATA_USER = "odata.user"
ODATA_PASS = "Nji9ol.*"

def get_sales():

    url = ODATA_URL + "Document_РеализацияТоваровУслуг?$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    return response.json()

@app.get("/sales")
def sales():

    data = get_sales()

    return {
        "count": len(data["value"]),
        "example": data["value"][0]
    }