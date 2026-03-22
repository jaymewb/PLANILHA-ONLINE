from flask import Flask, request, render_template_string
import pandas as pd
import pytz
import requests
from io import BytesIO
import re
from datetime import datetime
import os

app = Flask(__name__)

SHEET_URL = "https://1drv.ms/x/c/b96adcc2e8fff38f/IQCdM2bSlO7fQqt_G-cfm5DcAetm_TK94nO-7aL_uVBpRKE?e=7xSnPT"

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Painel</title>
    <style>
        body {
            font-family: Arial;
            background: #1e293b;
            color: white;
            text-align: center;
        }

        input {
            padding: 10px;
            width: 250px;
            border-radius: 5px;
            border: none;
        }

        button {
            padding: 10px;
            border-radius: 5px;
            border: none;
            background: #22c55e;
            color: black;
            font-weight: bold;
        }

        .card {
            background: #334155;
            margin: 20px auto;
            padding: 25px;
            border-radius: 12px;
            width: 420px;
            box-shadow: 0px 0px 10px rgba(0,0,0,0.3);
        }

        .btn {
            display: inline-block;
            margin-top: 10px;
            padding: 10px;
            background: #22c55e;
            color: black;
            text-decoration: none;
            border-radius: 5px;
        }

        .ok { color: #22c55e; font-weight: bold; }
        .warn { color: #facc15; font-weight: bold; }
        .off { color: #ef4444; font-weight: bold; }
    </style>
</head>
<body>

<h2>📋 Painel de Colaboradores</h2>

<form method="get">
    <input type="text" name="busca" placeholder="Digite o nome">
    <button type="submit">Buscar</button>
</form>

<hr>

{% for p in dados %}
<div class="card">

    <p>🏢 <b>Posto:</b> {{p.posto}}</p>
    <p>👤 <b>Nome:</b> {{p.nome}}</p>
    <p>🔤 <b>Letra:</b> {{p.letra}}</p>
    <p>🔁 <b>Escala:</b> {{p.escala}}</p>

    <p>📊 <b>Situação:</b>
        {% if "Trabalhando" in p.situacao %}
            <span class="ok">{{p.situacao}}</span>
        {% elif "Fora" in p.situacao %}
            <span class="warn">{{p.situacao}}</span>
        {% else %}
            <span class="off">{{p.situacao}}</span>
        {% endif %}
    </p>

    <p>📞 <b>Telefone:</b> {{p.telefone}}</p>

    <a class="btn" href="{{p.link}}" target="_blank">
        💬 Abrir WhatsApp
    </a>

</div>
{% endfor %}

</body>
</html>
"""

def limpar(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()

def carregar_planilha(link):
    link = link.replace("?e=", "?download=1&")
    response = requests.get(link)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content), header=None)

@app.route("/")
def home():
    try:
        busca = request.args.get("busca", "").lower()

        df = carregar_planilha(SHEET_URL)

        dados = []

        for _, row in df.iterrows():

            # 🔥 NOVOS ÍNDICES BASEADOS NA SUA PLANILHA
            posto = limpar(row[0])   # A
            nome = limpar(row[1])    # B
            letra = limpar(row[2])   # C
            escala = limpar(row[3])  # D
            telefone = limpar(row[4]) # E
            situacao_planilha = limpar(row[5]).lower() # F

            # 🔥 IGNORA LINHA VAZIA
            if not nome:
                continue

            fuso_sp = pytz.timezone('America/Sao_Paulo')
            hora = datetime.now(fuso_sp).hour
            escala_tipo = escala.lower()

            # 🔥 LÓGICA DE STATUS
            if "trabalhando" in situacao_planilha:

                if escala_tipo == "d":
                    situacao = "🟢 Trabalhando" if 6 <= hora < 18 else "🟡 Fora do horário"

                elif escala_tipo == "n":
                    situacao = "🟢 Trabalhando" if hora >= 19 or hora < 7 else "🟡 Fora do horário"

                elif "5x2" in escala_tipo:
                    situacao = "🟢 Trabalhando" if 8 <= hora < 16 else "🟡 Fora do horário"

                else:
                    situacao = "🟡 Escala desconhecida"

            else:
                situacao = "🔴 Folga"

            # 🔍 BUSCA
            if busca and busca not in nome.lower():
                continue

            # 📞 LIMPA TELEFONE
            numero = re.sub(r'\D', '', telefone)
            link = f"https://wa.me/55{numero}" if numero else "#"

            dados.append({
                "posto": posto,
                "nome": nome,
                "letra": letra,
                "escala": escala,
                "telefone": numero,
                "situacao": situacao,
                "link": link
            })

        return render_template_string(HTML, dados=dados)

    except Exception as e:
        return f"❌ Erro: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)