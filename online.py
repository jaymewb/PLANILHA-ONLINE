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

# ================= HTML =================
HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Painel de Escala</title>
    <style>
        body { font-family: Arial; background: #1e293b; color: white; text-align: center; }

        input { padding: 10px; width: 250px; border-radius: 5px; border: none; }
        button { padding: 10px; border-radius: 5px; border: none; background: #22c55e; font-weight: bold; cursor: pointer; }

        .card {
            background: #334155;
            margin: 20px auto;
            padding: 20px;
            border-radius: 12px;
            width: 420px;
        }

        .posto {
            color: #facc15;
            font-weight: bold;
            border: 2px solid #facc15;
            padding: 6px;
            border-radius: 6px;
            display: inline-block;
        }

        .ok { color: #22c55e; font-weight: bold; }
        .warn { color: #facc15; font-weight: bold; }
        .off { color: #ef4444; font-weight: bold; }
        .shift { color: #94a3b8; font-weight: bold; }

        .timer {
            font-size: 0.9em;
            margin-top: 5px;
            display: block;
        }

        .btn {
            display: inline-block;
            margin-top: 10px;
            padding: 8px 15px;
            background: #22c55e;
            color: black;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
        }
    </style>
</head>
<body>

<h2>📋 Painel de Escala</h2>

<form method="get">
    <input type="text" name="busca" placeholder="Buscar colaborador..." value="{{busca}}">
    <button type="submit">Buscar</button>
</form>

<hr>

{% for p in dados %}
<div class="card">

    <p>🏢 <span class="posto">{{p.posto}}</span></p>

    <p>👤 {{p.nome}}</p>

    <p>🔤 Letra:
        {% if p.letra|lower in ['a','c','e','g','i','k','m','o','q','s','u','w','y'] %}
            ÍMPAR
        {% elif p.letra %}
            PAR
        {% else %}
            {{p.letra}}
        {% endif %}
    </p>

    <p>🔁 Escala:
        {% if p.escala|lower == 'd' %}
            DIURNA
        {% elif p.escala|lower == 'n' %}
            NOTURNA
        {% else %}
            {{p.escala}}
        {% endif %}
    </p>

    <p>📊 Situação:
        {% if "Trabalhando" in p.situacao %}
            <span class="ok">{{p.situacao}}</span>

        {% elif "Fora" in p.situacao %}
            <span class="warn">{{p.situacao}}</span>
            {% if p.target_h %}
                <span class="timer" data-target="{{p.target_h}}">⏱️ --:--:--</span>
            {% endif %}

        {% elif "Troca" in p.situacao or "Encerrando" in p.situacao %}
            <span class="shift">{{p.situacao}}</span>

        {% else %}
            <span class="off">{{p.situacao}}</span>
        {% endif %}
    </p>

    <p>📞 Telefone: {{p.telefone}}</p>

    <a class="btn" href="{{p.link}}" target="_blank">💬 WhatsApp</a>

</div>
{% endfor %}

<script>
function updateTimers() {
    const now = new Date();
    const nowSec = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();

    document.querySelectorAll('.timer').forEach(el => {
        const targetSec = parseFloat(el.getAttribute('data-target')) * 3600;
        let diff = targetSec - nowSec;

        if (diff > 0) {
            const h = Math.floor(diff / 3600);
            const m = Math.floor((diff % 3600) / 60);
            const s = diff % 60;
            el.innerText = `⏱️ Inicia em: ${h}h ${m}m ${s}s`;
        } else {
            el.innerText = "🔔 No horário!";
        }
    });
}

setInterval(updateTimers, 1000);
updateTimers();
</script>

</body>
</html>
"""

# ================= FUNÇÕES =================
def limpar(valor):
    return str(valor).strip() if not pd.isna(valor) else ""

def carregar_planilha(link):
    link = link.replace("?e=", "?download=1&")
    response = requests.get(link)
    response.raise_for_status()
    return pd.read_excel(BytesIO(response.content), header=None)

# ================= ROTA =================
@app.route("/")
def home():
    try:
        busca = request.args.get("busca", "").lower()
        df = carregar_planilha(SHEET_URL)

        dados = []

        fuso_sp = pytz.timezone('America/Sao_Paulo')
        agora = datetime.now(fuso_sp)
        h_dec = agora.hour + (agora.minute / 60)

        for _, row in df.iterrows():
            posto = limpar(row[0])
            nome = limpar(row[1])
            letra = limpar(row[2])
            escala = limpar(row[3])
            telefone = limpar(row[4])
            situacao_planilha = limpar(row[5]).lower()

            if not nome or nome.lower() == "nome":
                continue

            if busca and busca not in nome.lower():
                continue

            escala_tipo = escala.lower()
            target_h = None

            if "trabalhando" in situacao_planilha:

                # DIURNO
                if escala_tipo == "d":
                    if 6.0 <= h_dec < 18.0:
                        situacao = "🟢 Trabalhando"
                    elif 5.0 <= h_dec < 6.0:
                        situacao = "🟡 Fora do horário"
                        target_h = 6.0
                    elif 18.0 <= h_dec < 18.5:
                        situacao = "⚪ Troca de Turno"
                    elif 18.5 <= h_dec < 19.0:
                        situacao = "⚪ Encerrando Plantão"
                    else:
                        situacao = "🔴 Folga"

                # NOTURNO
                elif escala_tipo == "n":
                    if h_dec >= 19.0 or h_dec < 6.0:
                        situacao = "🟢 Trabalhando"
                    elif 17.5 <= h_dec < 19.0:
                        situacao = "🟡 Fora do horário"
                        target_h = 19.0
                    elif 6.0 <= h_dec < 6.5:
                        situacao = "⚪ Troca de Turno"
                    elif 6.5 <= h_dec < 7.0:
                        situacao = "⚪ Encerrando Plantão"
                    else:
                        situacao = "🔴 Folga"
                else:
                    situacao = "🔴 Folga"

            else:
                situacao = "🔴 Folga"

            num = re.sub(r'\D', '', telefone)

            dados.append({
                "posto": posto,
                "nome": nome,
                "letra": letra,
                "escala": escala,
                "telefone": num,
                "situacao": situacao,
                "target_h": target_h,
                "link": f"https://wa.me/55{num}" if num else "#"
            })

        return render_template_string(HTML, dados=dados, busca=busca)

    except Exception as e:
        return f"❌ Erro: {str(e)}"

# ================= RUN =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)