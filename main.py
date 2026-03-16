from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAI
import os
import re

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===============================
# 1C SETTINGS
# ===============================

ODATA_URL = "https://1cfresh.kz/a/ea8/239226/odata/standard.odata/"
ODATA_USER = "odata.user"
ODATA_PASS = "Nji9ol.*"

# ===============================
# FIND CUSTOMER
# ===============================

def find_customer(name):

    url = ODATA_URL + f"Catalog_Контрагенты?$filter=contains(Description,'{name}')&$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    data = response.json()

    if data["value"]:
        return data["value"][0]["Ref_Key"]

    return None


# ===============================
# CREATE CUSTOMER
# ===============================

def create_customer(name):

    url = ODATA_URL + "Catalog_Контрагенты?$format=json"

    payload = {
        "Description": name
    }

    response = requests.post(
        url,
        json=payload,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    return response.json()


# ===============================
# FIND PRODUCT
# ===============================

def find_product(name):

    url = ODATA_URL + f"Catalog_Номенклатура?$filter=contains(Description,'{name}')&$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    data = response.json()

    if data["value"]:
        return data["value"][0]["Ref_Key"]

    return None


# ===============================
# CREATE SALE
# ===============================

def create_sale(customer, product, qty, price):

    customer_id = find_customer(customer)

    if not customer_id:
        create_customer(customer)
        customer_id = find_customer(customer)

    product_id = find_product(product)

    if not product_id:
        return {"error": f"Товар {product} не найден"}

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


# ===============================
# PARSE SALE REQUEST
# ===============================

def parse_sale(text):

    customer = None
    product = None
    qty = 1
    price = 0

    m = re.search(r"продай\s+(\w+)", text)
    if m:
        customer = m.group(1)

    m = re.search(r"(\d+)\s+(\w+)", text)
    if m:
        qty = int(m.group(1))
        product = m.group(2)

    m = re.search(r"по\s+(\d+)", text)
    if m:
        price = int(m.group(1))

    return customer, product, qty, price


# ===============================
# AI REQUEST
# ===============================

class AIRequest(BaseModel):
    text: str


# ===============================
# AI CHAT
# ===============================

@app.post("/ai")
def ai_chat(req: AIRequest):

    text = req.text.lower()

    if "продай" in text or "реализац" in text:

        customer, product, qty, price = parse_sale(text)

        if not customer or not product:
            return {"answer": "Не удалось распознать клиента или товар"}

        result = create_sale(customer, product, qty, price)

        return {"answer": result}

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": "Ты помощник по анализу бизнеса"},
            {"role": "user", "content": text}
        ]
    )

    return {"answer": completion.choices[0].message.content}


# ===============================
# TEST
# ===============================

@app.get("/test")
def test():
    return {"status": "AI server working"}


# ===============================
# WEB UI
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

<input id="msg" placeholder="Например: продай Жанибек 2 iphone по 650">
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