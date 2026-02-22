import requests

payload = {
  "no_canario": 1,
  "el_hierro": 2,
  "fuerteventura": 3,
  "gran_canaria": 4,
  "la_gomera": 5,
  "la_palma": 6,
  "lanzarote": 7,
  "tenerife": 8
}
r = requests.post("http://127.0.0.1:8000/census", json=payload)
print(r.status_code)
print(r.text)