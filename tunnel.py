from pyngrok import ngrok

# открываем туннель к порту 8000
public_url = ngrok.connect(8000)

print("Публичный адрес:")
print(public_url)