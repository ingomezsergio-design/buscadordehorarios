import os
from flask import Flask, jsonify, request, render_template
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()
ANIO_FIJO = int(os.getenv("ANIO_FIJO", 2025))

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "service-account.json"
if not os.path.isabs(creds_path):
    creds_path = os.path.join(BASE_DIR, creds_path)
if not os.path.exists(creds_path):
    raise RuntimeError("Falta service-account.json en la raíz del proyecto")

creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
client = gspread.authorize(creds)

app = Flask(__name__)

SHEET_ID = "18LDSIcvRwNHW8-Ja38q8Ll02o6DKxzhK8qrjwnR7R3Y"
GID_BY_MONTH = {10: 1756623178, 11: 530216982}  # 10=Oct, 11=Nov

MESES_ABREV = ["ene","feb","mar","abr","may","jun","jul","ago","sept","oct","nov","dic"]

def formatear_fecha(dia:int, mes:int) -> str:
    import datetime
    dias_abrev_ld = ["lun","mar","mié","jue","vie","sáb","dom"]
    dt = datetime.date(ANIO_FIJO, mes, dia)
    return f"{dias_abrev_ld[dt.weekday()]} {dia:02d}-{MESES_ABREV[mes-1]}"

def extraer_mes(fecha_ddmm:str) -> int:
    try:
        _d, m = fecha_ddmm.split("/")
        return int(m)
    except Exception:
        return 0

def get_ws_for_month(mes:int):
    gid = GID_BY_MONTH.get(mes)
    if not gid:
        return None
    sh = client.open_by_key(SHEET_ID)
    return sh.get_worksheet_by_id(gid)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/agentes")
def api_agentes():
    mes = request.args.get("mes", type=int)
    if mes not in (10, 11):
        return jsonify({"ok": False, "error": "Solo disponibles Octubre (10) y Noviembre (11)"}), 400
    try:
        ws = get_ws_for_month(mes)
        if not ws:
            return jsonify({"ok": False, "error": "Worksheet no encontrado para ese mes"}), 400
        data = ws.get_all_values()
        nombres = [row[3] for row in data[3:] if len(row) > 4 and row[3]]
        seen=set(); valores=[x for x in nombres if not (x in seen or seen.add(x))]
        return jsonify({"ok": True, "agentes": valores})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/buscar", methods=["POST"])
def api_buscar():
    body = request.get_json(force=True)
    valor = (body.get("valorBuscado") or "").strip()
    mes = int(body.get("mes") or 0)
    if mes not in (10, 11) or not valor:
        return jsonify({"ok": False, "error": "Solo 10/11 y valorBuscado requerido"}), 400
    try:
        ws = get_ws_for_month(mes)
        if not ws: return jsonify({"ok": False, "error": "Worksheet no encontrado"}), 400
        data = ws.get_all_values()

        agente = {"sup":"", "score":"", "contrato":"", "horas":""}
        horarios = {}
        response_sync = []
        mapa = {"F":"Franco", "V":"Vac", "NP":"-", "Fe":"Libre", "C":"Franco", "LSG":"LSG", "AUX":"Aux"}

        filas_idx = [i for i,row in enumerate(data) if len(row)>4 and row[3] and row[3].strip().lower()==valor.lower()]
        if not filas_idx:
            return jsonify({"ok": True, "respuesta": [], "agente": agente, "responseSync": []})

        fila = data[filas_idx[0]]
        fila2 = data[filas_idx[1]] if len(filas_idx)>1 else None

        agente.update({
            "sup": fila[4] if len(fila) > 5 else "",
            "score": fila[9] if len(fila) > 9 else "",
            "contrato": ("Mensuales" if (len(fila) > 10 and str(fila[10]).strip().isdigit() and int(float(fila[10])) > 40) else "Semanales"),
            "horas": fila[10] if len(fila) > 10 else ""
        })

        headers = data[1]
        for j in range(17, len(fila), 5):
            if j >= len(headers): break
            dia = headers[j]
            val = fila[j] if j < len(fila) else ""
            if val in mapa:
                horarios[dia] = f"<br>{mapa[val]}"
                response_sync.append({"fecha": dia, "ingreso": val, "salida": "-"})
            elif isinstance(val, str) and ":" in val:
                salida = fila[j+1] if j+1 < len(fila) else ""
                horarios[dia] = f"<div>{val}<br>{salida}</div>"
                response_sync.append({"fecha": dia, "ingreso": val, "salida": salida})
            elif fila2:
                val2 = fila2[j] if j < len(fila2) else ""
                if val2 in mapa:
                    horarios[dia] = f"<br>{mapa[val2]}"
                    response_sync.append({"fecha": dia, "ingreso": val2, "salida": "-"})
                elif isinstance(val2, str) and ":" in val2:
                    sal2 = fila2[j+1] if j+1 < len(fila2) else ""
                    horarios[dia] = f"<div>{val2}<br>{sal2}</div>"
                    response_sync.append({"fecha": dia, "ingreso": val2, "salida": sal2})

        respuesta = [f"{k}  {v}" for k,v in horarios.items()]
        return jsonify({"ok": True, "respuesta": respuesta, "agente": agente, "responseSync": response_sync})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/cambio/franco", methods=["POST"])
def api_cambio_franco():
    body = request.get_json(force=True)
    fecha = body.get("fecha")  # dd/mm
    nombre = body.get("nombreAgente")
    if not fecha or not nombre:
        return jsonify({"ok": False, "error": "fecha y nombreAgente requeridos"}), 400
    mes = extraer_mes(fecha)
    if mes not in (10, 11):  # solo Oct/Nov
        return jsonify({"ok": True, "items": []})
    try:
        ws = get_ws_for_month(mes); data = ws.get_all_values()
        d, m = fecha.split("/")
        target_header = formatear_fecha(int(d), int(m))
        headers = data[1]
        try:
            idx = headers.index(target_header)
        except ValueError:
            return jsonify({"ok": True, "items": []})

        score = ""
        for i, row in enumerate(data):
            if i>2 and len(row)>9 and row[3] == nombre:
                score = row[9]; break

        items = []
        for i, row in enumerate(data):
            if i>2 and len(row)>idx and row[idx] == "F" and (len(row)>9 and row[9]==score):
                ant_in = row[idx-5] if idx-5 >=0 and len(row)>idx-5 else "-"
                ant_out = row[idx-4] if idx-4 >=0 and len(row)>idx-4 else "-"
                sig_in = row[idx+5] if len(row)>idx+5 else "-"
                sig_out = row[idx+6] if len(row)>idx+6 else "-"
                horario_ant = f"{ant_in}-{ant_out}" if ":" in ant_in else "-"
                horario_sig = f"{sig_in}-{sig_out}"
                items.append({"agente": row[3], "sup": row[4], "horarioAnterior": horario_ant, "horarioSiguiente": horario_sig})
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/api/cambio/horario", methods=["POST"])
def api_cambio_horario():
    body = request.get_json(force=True)
    fecha = body.get("fecha")
    nombre = body.get("nombreAgente")
    hora = body.get("hora")
    if not (fecha and nombre and hora):
        return jsonify({"ok": False, "error": "fecha, nombreAgente y hora requeridos"}), 400
    mes = extraer_mes(fecha)
    if mes not in (10, 11):
        return jsonify({"ok": True, "items": []})
    try:
        ws = get_ws_for_month(mes); data = ws.get_all_values()
        d, m = fecha.split("/")
        target_header = formatear_fecha(int(d), int(m))
        headers = data[1]
        try:
            idx = headers.index(target_header)
        except ValueError:
            return jsonify({"ok": True, "items": []})

        score = ""
        for i,row in enumerate(data):
            if i>2 and len(row)>9 and row[3] == nombre:
                score = row[9]; break

        items = []
        for i,row in enumerate(data):
            if i>2 and len(row)>idx and row[idx] == hora and (len(row)>9 and row[9]==score):
                out = row[idx+1] if len(row)>idx+1 else ""
                items.append({"agente": row[3], "sup": row[4], "horario": f"{row[idx]}-{out}"})
        return jsonify({"ok": True, "items": items})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)), debug=True)
