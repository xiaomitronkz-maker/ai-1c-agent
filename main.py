from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAI
import os

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===============================
# 1C ODATA SETTINGS
# ===============================

ODATA_URL = "https://1cfresh.kz/a/ea8/239226/odata/standard.odata/"
ODATA_USER = "odata.user"
ODATA_PASS = "Nji9ol.*"


# ===============================
# GET SALES FROM 1C
# ===============================

def get_sales():

    url = ODATA_URL + "Document_РеализацияТоваровУслуг?$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    return response.json()


# ===============================
# TEST
# ===============================

@app.get("/test")
def test():
    return {"status": "AI server working"}


# ===============================
# SALES RAW
# ===============================

@app.get("/sales")
def sales():

    data = get_sales()
    docs = data.get("value", [])

    return {
        "count": len(docs),
        "example": docs[0] if docs else None
    }


# ===============================
# SALES ANALYTICS
# ===============================

@app.get("/ai/sales")
def ai_sales():

    data = get_sales()
    docs = data.get("value", [])

    total = len(docs)
    sum_sales = sum(d.get("СуммаДокумента", 0) for d in docs)

    return {
        "documents": total,
        "total_sales": sum_sales
    }


# ===============================
# AI REQUEST MODEL
# ===============================

class AIRequest(BaseModel):
    text: str


# ===============================
# AI CHAT
# ===============================

@app.post("/ai")
def ai_chat(req: AIRequest):

    text = req.text.lower()

    if "создай реализацию" in text:

        result = create_sale(
        customer="Xiaomi",
        product="iPhone",
        qty=2,
        price=650
    )

    return {
        "answer": result
    }

    # ПОСЛЕДНИЕ ПРОДАЖИ
    if "последние" in text:

        data = get_sales()
        docs = data.get("value", [])

        last_docs = docs[-3:]

        result = []

        for d in last_docs:

            result.append({
                "номер": d.get("Number"),
                "дата": d.get("Date"),
                "сумма": d.get("СуммаДокумента")
            })

        return {
            "answer": result
        }

    # ОБЩИЕ ПРОДАЖИ
    if "продажи" in text:

        data = get_sales()
        docs = data.get("value", [])

        total = len(docs)
        sum_sales = sum(d.get("СуммаДокумента", 0) for d in docs)

        return {
            "answer": f"Продажи: {total}. Сумма: {sum_sales}"
        }

    # OPENAI
    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Ты ассистент для анализа бизнеса из 1С"},
            {"role": "user", "content": text}
        ]
    )

    answer = completion.choices[0].message.content

    return {"answer": answer}


# ===============================
# WEB INTERFACE
# ===============================

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
def find_customer(name):

    url = ODATA_URL + f"Catalog_Контрагенты?$filter=contains(Description,'{name}')&$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    if response.status_code != 200:
        return None

    data = response.json()

    if data["value"]:
        return data["value"][0]["Ref_Key"]

    return None

def find_product(name):

    url = ODATA_URL + f"Catalog_Номенклатура?$filter=contains(Description,'{name}')&$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    if response.status_code != 200:
        return None

    data = response.json()

    if data["value"]:
        return data["value"][0]["Ref_Key"]

    return None

def create_sale(customer, product, qty, price):

    customer_id = find_customer(customer)
    product_id = find_product(product)

    if not customer_id:
        return {"error": "Клиент не найден"}

    if not product_id:
        return {"error": "Товар не найден"}

    url = ODATA_URL + "Document_РеализацияТоваровУслуг?$format=json"

    payload = {
        "Контрагент_Key": customer_id,
        "Товары": [
            {
                "Номенклатура_Key": product_id,
                "Количество": qty,
                "Цена": price
            }
        ]
    }

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    return response.json()