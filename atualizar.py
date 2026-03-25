from flask import Flask, request, render_template_string, redirect
import pandas as pd
import requests
from io import BytesIO
import re
from datetime import datetime, timedelta
import os
import urllib.parse

app = Flask(__name__)

# CONFIGURAÇÃO PADRÃO
MEU_EMAIL = "jaimebarbosa@grupoavi.com.br"
SHEET_URL = "https://1drv.ms/x/c/b96adcc2e8fff38f/IQDxY7NKJj9mR6k_xhOTtGBGAUiE7EiJCON8mKvXXKzLfAM?e=G98Lcu"

# Bancos de dados temporários
ESCOLAS = {
    "PADRAO": {
        "nome": "Escola Padrão",
        "email": "atendimento@escola.com",
        "whatsapp": "11999999999",
        "agenda": "#"
    }
}

PSICOLOGAS = {
    "PADRAO": {
        "nome": "Psicóloga Exemplo",
        "email": "clinica@exemplo.com",
        "whatsapp": "11988888888"
    }
}

# ================= LAYOUT BASE (CSS MODERNO) =================
BASE_HTML = """
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Painel de Escala RH</title>
    <style>
        body { background: #0f172a; font-family: 'Segoe UI', Tahoma, sans-serif; color: white; margin: 0; text-align: center; }
        .topo { background: #1e293b; padding: 25px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); position: sticky; top: 0; z-index: 100; }
        h2 { margin: 0 0 15px 0; display: flex; align-items: center; justify-content: center; gap: 10px; }
        input, select { padding: 12px; border-radius: 8px; border: 1px solid #334155; width: 250px; background: #0f172a; color: white; margin: 5px; }
        .btn { background: #22c55e; border: none; padding: 12px 20px; border-radius: 8px; font-weight: bold; color: white; cursor: pointer; margin: 5px; transition: 0.3s; text-decoration: none; display: inline-block; }
        .btn:hover { background: #16a34a; transform: translateY(-2px); }
        .btn-blue { background: #3b82f6; }
        .btn-purple { background: #a855f7; }
        .btn-yellow { background: #facc15; color: #0f172a; }
        .container { display: flex; flex-wrap: wrap; justify-content: center; padding: 20px; gap: 20px; }
        .card { background: #1e293b; width: 380px; padding: 20px; border-radius: 15px; box-shadow: 0px 10px 20px rgba(0,0,0,0.4); text-align: left; border: 1px solid #334155; }
        .posto-tag { border: 2px solid #facc15; color: #facc15; padding: 4px 10px; border-radius: 8px; display: inline-block; margin-bottom: 12px; font-weight: bold; font-size: 14px; }
        .nome { font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #f8fafc; }
        .info-row { margin: 5px 0; font-size: 14px; }
        .label { color: #94a3b8; font-weight: bold; }
        textarea { width: 100%; background: #0f172a; color: #22c55e; border: 1px solid #334155; border-radius: 8px; padding: 10px; font-family: monospace; margin-top: 10px; resize: none; font-size: 12px; }
        hr { border: 0; border-top: 1px solid #334155; margin: 20px 0; }
        h4 { margin: 10px 0 5px 0; font-size: 12px; color: #3b82f6; }
        .calendar-input { width: 90%; margin-bottom: 10px; border-color: #3b82f6; }
    </style>
    <script>
        function atualizarTextoEmail(id, nome, cpf, escolaEmail, meuEmail) {
            const data = document.getElementById('data_' + id).value;
            const escala = document.getElementById('escala_' + id).value;
            const almoco = document.getElementById('almoco_' + id).value;

            let textoAlmoco = (almoco === "sim") ? "\\nFavor fornecer almoço." : "";

            let corpo = `Solicito reciclagem do colaborador:\\n\\nNome: ${nome}\\nCPF: ${cpf}\\nData: ${data}\\nEscala: ${escala}${textoAlmoco}\\n\\nLizy, por favor encaminhar o ASO.`;

            // Atualiza a visualização na tela
            document.getElementById('area_' + id).value = corpo.replace(/\\\\n/g, '\\n');

            // Atualiza o link do botão
            const mailto = `mailto:${escolaEmail}?cc=${meuEmail}&subject=Solicitação de Reciclagem - ${nome}&body=${encodeURIComponent(corpo.replace(/\\\\n/g, '\\n'))}`;
            document.getElementById('link_' + id).href = mailto;
        }
    </script>
</head>
<body>
<div class="topo">
    <h2>📋 Painel de Escala</h2>
    <form method="get" action="/">
        <input name="busca" placeholder="Buscar colaborador..." value="{{busca}}">
        <button type="submit" class="btn">Buscar</button>
    </form>
    <div style="margin-top: 10px;">
        <a href="/" class="btn btn-blue">🔄 Atualizar</a>
        <a href="/relatorio" class="btn">📊 Vencimentos</a>
        <a href="/escolas" class="btn btn-blue">🏫 Escolas & Psicólogas</a>
    </div>
</div>
<div class="container">{{conteudo|safe}}</div>
</body>
</html>
"""


def limpar(v): return str(v).strip() if not pd.isna(v) else ""


def carregar_dados():
    try:
        link = SHEET_URL.replace("?e=", "?download=1&")
        r = requests.get(link, timeout=15)
        return pd.read_excel(BytesIO(r.content), header=None)
    except:
        return pd.DataFrame()


@app.route("/")
def home():
    busca = request.args.get("busca", "").lower()
    df = carregar_dados()
    html_cards = ""
    if df.empty: return render_template_string(BASE_HTML, conteudo="<h3>Erro ao carregar planilha.</h3>", busca=busca)

    for _, row in df.iterrows():
        try:
            posto, nome, letra, escala, telefone, situacao = limpar(row[0]), limpar(row[1]), limpar(row[2]), limpar(
                row[3]), limpar(row[4]), limpar(row[5])
            if not nome or nome.lower() == "nome": continue
            if busca and (busca not in nome.lower() and busca not in posto.lower()): continue
            cor = "#ef4444" if "folga" in situacao.lower() else "#22c55e"
            num = re.sub(r'\D', '', telefone)
            html_cards += f"""
            <div class="card" style="width:320px;">
                <div class="posto-tag">🏢 {posto}</div>
                <div class="nome">👤 {nome}</div>
                <div class="info-row"><span class="label">🔤 Letra:</span> {letra} | <span class="label">🔁 Escala:</span> {escala}</div>
                <div class="info-row"><span style="height:10px;width:10px;background:{cor};border-radius:50%;display:inline-block;margin-right:5px;"></span>{situacao}</div>
                <br><a href="https://wa.me/55{num}" target="_blank" class="btn" style="width:85%; text-align:center;">💬 WhatsApp</a>
            </div>"""
        except:
            continue
    return render_template_string(BASE_HTML, conteudo=html_cards or "<h3>Nenhum resultado.</h3>", busca=busca)


@app.route("/relatorio")
def relatorio():
    df = carregar_dados()
    hoje, limite = datetime.now(), datetime.now() + timedelta(days=60)
    html_cards = "<h3>🚨 Vencimentos nos Próximos 60 Dias</h3><div class='container' style='width:100%'>"

    esc = list(ESCOLAS.values())[0] if ESCOLAS else {"nome": "[Escola]", "email": "", "agenda": "#"}
    psi = list(PSICOLOGAS.values())[0] if PSICOLOGAS else {"nome": "[Psicóloga]", "whatsapp": ""}

    for _, row in df.iterrows():
        try:
            nome, posto, tel, cpf, venc = limpar(row[1]), limpar(row[0]), limpar(row[4]), limpar(row[6]), limpar(row[7])
            data_venc = pd.to_datetime(venc)
            if hoje <= data_venc <= limite:
                dt_s = data_venc.strftime('%d/%m/%Y')
                num_colab = re.sub(r'\D', '', tel)
                num_psi = re.sub(r'\D', '', psi['whatsapp'])

                # Texto inicial (Posto Removido conforme solicitado)
                corpo_email = f"Solicito reciclagem do colaborador:\n\nNome: {nome}\nCPF: {cpf}\nEscala: 5x2\n\nLizy, por favor encaminhar o ASO."
                mailto_link = f"mailto:{esc['email']}?cc={MEU_EMAIL}&subject=Solicitação de Reciclagem - {nome}&body={urllib.parse.quote(corpo_email)}"

                html_cards += f"""
                <div class="card">
                    <div class="nome">{nome}</div>
                    <div class="info-row">📅 <b>Vencimento:</b> {dt_s}</div>
                    <hr>

                    <h4>📅 Data | 🔁 Escala | 🍽️ Almoço?</h4>
                    <input type="date" class="calendar-input" id="data_{num_colab}" onchange="atualizarTextoEmail('{num_colab}', '{nome}', '{cpf}', '{esc['email']}', '{MEU_EMAIL}')">

                    <select id="escala_{num_colab}" style="width:45%;" onchange="atualizarTextoEmail('{num_colab}', '{nome}', '{cpf}', '{esc['email']}', '{MEU_EMAIL}')">
                        <option value="5x2">5x2</option>
                        <option value="12x36">12x36</option>
                    </select>

                    <select id="almoco_{num_colab}" style="width:45%;" onchange="atualizarTextoEmail('{num_colab}', '{nome}', '{cpf}', '{esc['email']}', '{MEU_EMAIL}')">
                        <option value="nao">Almoço: Não</option>
                        <option value="sim">Almoço: Sim</option>
                    </select>

                    <h4>1. Enviar E-mail p/ Escola ({esc['nome']})</h4>
                    <a href="{mailto_link}" id="link_{num_colab}" class="btn btn-yellow" style="font-size:11px; width:90%">📧 Abrir E-mail Pronto</a>

                    <h4>2. WhatsApp Psicóloga ({psi['nome']})</h4>
                    <a href="https://wa.me/55{num_psi}?text=Olá, solicito exame para {nome}, CPF {cpf}." target="_blank" class="btn btn-purple" style="font-size:11px; width:90%">💬 Contatar Psicóloga</a>

                    <textarea id="area_{num_colab}" rows="5" readonly>{corpo_email}</textarea>
                </div>"""
        except:
            continue
    return render_template_string(BASE_HTML, conteudo=html_cards + "</div>", busca="")


@app.route("/escolas", methods=["GET", "POST"])
def escolas():
    global MEU_EMAIL
    if request.method == "POST":
        tipo = request.form.get("tipo")
        if tipo == "CONFIG":
            MEU_EMAIL = request.form.get("meu_email")
        else:
            nome = request.form.get("nome")
            dados = {"nome": nome, "email": request.form.get("email"), "whatsapp": request.form.get("whatsapp"),
                     "agenda": request.form.get("agenda", "#")}
            if tipo == "ESCOLA":
                ESCOLAS[nome.upper()] = dados
            else:
                PSICOLOGAS[nome.upper()] = dados
        return redirect("/escolas")

    form_html = f"""
    <div class="container">
        <div class="card" style="width:90%; border-bottom: 4px solid #3b82f6;">
            <h3>⚙️ Configuração de Envio</h3>
            <form method="post">
                <input type="hidden" name="tipo" value="CONFIG">
                <input name="meu_email" value="{MEU_EMAIL}" placeholder="Seu E-mail (para CC)" style="width:80%">
                <button class="btn btn-blue">Atualizar Meu E-mail</button>
            </form>
        </div>
        <div class="card" style="width:45%; min-width:320px;">
            <h3>🏫 Cadastrar Escola</h3>
            <form method="post">
                <input type="hidden" name="tipo" value="ESCOLA">
                <input name="nome" placeholder="Nome da Escola" required style="width:90%">
                <input name="email" placeholder="E-mail da Escola" style="width:90%">
                <input name="whatsapp" placeholder="WhatsApp" style="width:90%">
                <input name="agenda" placeholder="Link da Agenda Online" style="width:90%">
                <button class="btn" style="width:95%">💾 Salvar Escola</button>
            </form>
        </div>
        <div class="card" style="width:45%; min-width:320px; border-top: 4px solid #a855f7;">
            <h3>🧠 Cadastrar Psicóloga</h3>
            <form method="post">
                <input type="hidden" name="tipo" value="PSICOLOGA">
                <input name="nome" placeholder="Nome da Psicóloga" required style="width:90%">
                <input name="email" placeholder="E-mail da Clínica" style="width:90%">
                <input name="whatsapp" placeholder="WhatsApp" style="width:90%">
                <button class="btn btn-purple" style="width:95%">💾 Salvar Psicóloga</button>
            </form>
        </div>
    </div>
    <hr><div class="container">
    """
    for e in ESCOLAS.values():
        form_html += f'<div class="card" style="width:300px;"><b>🏫 {e["nome"]}</b><br>Email: {e["email"]}<br>Zap: {e["whatsapp"]}<br>Link Agenda: {e["agenda"]}</div>'
    for p in PSICOLOGAS.values():
        form_html += f'<div class="card" style="width:300px; border-left:5px solid #a855f7;"><b>🧠 {p["nome"]}</b><br>Email: {p.get("email", "")}<br>Zap: {p["whatsapp"]}</div>'
    return render_template_string(BASE_HTML, conteudo=form_html + "</div>", busca="")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))