from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import requests
from requests.auth import HTTPBasicAuth
from openai import OpenAI
import os
import json

app = FastAPI()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ===============================
# 1C SETTINGS
# ===============================

ODATA_URL = "https://1cfresh.kz/a/ea8/239226/odata/standard.odata/"
ODATA_USER = "odata.user"
ODATA_PASS = "Nji9ol.*"

# ===============================
# GET SALES
# ===============================

def get_sales():

    url = ODATA_URL + "Document_РеализацияТоваровУслуг?$format=json"

    response = requests.get(
        url,
        auth=HTTPBasicAuth(ODATA_USER, ODATA_PASS)
    )

    return response.json()


# ===============================
# FIND CUSTOMER
# ===============================

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

    if response.status_code != 200:
        return None

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
# AI TOOLS
# ===============================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "find_customer",
            "description": "Найти клиента",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_customer",
            "description": "Создать клиента",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_product",
            "description": "Найти товар",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_sale",
            "description": "Создать реализацию",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer": {"type": "string"},
                    "product": {"type": "string"},
                    "qty": {"type": "number"},
                    "price": {"type": "number"}
                },
                "required": ["customer","product","qty","price"]
            }
        }
    }
]


# ===============================
# AI REQUEST MODEL
# ===============================

class AIRequest(BaseModel):
    text: str


# ===============================
# AI AGENT
# ===============================

@app.post("/ai")
def ai_chat(req: AIRequest):

    text = req.text

    completion = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": """
Ты AI агент для управления системой 1С.

Если пользователь просит:
- создать реализацию
- продать товар
- сделать продажу

ты должен вызвать функцию create_sale.

Параметры:

customer — имя клиента  
product — товар  
qty — количество  
price — цена
"""
            },
            {"role": "user", "content": text}
        ],
        tools=TOOLS,
        tool_choice="auto"
    )

    message = completion.choices[0].message

    if message.tool_calls:

        tool = message.tool_calls[0]

        name = tool.function.name
        args = json.loads(tool.function.arguments)

        if name == "find_customer":
            result = find_customer(**args)

        elif name == "create_customer":
            result = create_customer(**args)

        elif name == "find_product":
            result = find_product(**args)

        elif name == "create_sale":
            result = create_sale(**args)

        return {"answer": result}

    return {"answer": message.content}


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