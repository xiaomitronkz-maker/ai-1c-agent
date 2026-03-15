from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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

@app.get("/ai/sales")
def ai_sales():

    data = get_sales()

    docs = data["value"]

    total = len(docs)

    sum_sales = 0

    for d in docs:
        if "СуммаДокумента" in d:
            sum_sales += d["СуммаДокумента"]

    return {
        "documents": total,
        "total_sales": sum_sales
    }

from pydantic import BaseModel

class AIRequest(BaseModel):
    text: str


@app.post("/ai")
def ai_chat(req: AIRequest):

    text = req.text

    prompt = f"""
    Пользователь спрашивает про бизнес.

    Запрос: {text}

    Возможные команды:
    продажи
    """

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role":"system","content":"Ты ассистент 1С"},
            {"role":"user","content":prompt}
        ]
    )

    answer = completion.choices[0].message.content

    if "продажи" in answer:

        data = get_sales()
        docs = data["value"]

        total = len(docs)
        sum_sales = sum(d.get("СуммаДокумента",0) for d in docs)

        return {
            "answer": f"Продажи: {total}. Сумма: {sum_sales}"
        }

    return {"answer": answer}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
    <head>
        <title>AI 1C Assistant</title>
        <style>
        body {font-family: Arial; background:#111; color:white; padding:40px}
        input {padding:10px; width:400px}
        button {padding:10px}
        #response {margin-top:20px}
        </style>
    </head>
    <body>

    <h1>AI Assistant 1C</h1>

    <input id="msg" placeholder="Например: покажи продажи">
    <button onclick="send()">Отправить</button>

    <pre id="response"></pre>

    <script>

    async function send(){

        let text = document.getElementById("msg").value

        let r = await fetch("/ai",{
            method:"POST",
            headers:{
                "Content-Type":"application/json"
            },
            body:JSON.stringify({
                text:text
            })
        })

        let data = await r.json()

        document.getElementById("response").innerText =
        JSON.stringify(data,null,2)

    }

    </script>

    </body>
    </html>
    """