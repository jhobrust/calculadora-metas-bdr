import streamlit as st
from datetime import date, timedelta
import calendar
import math

st.set_page_config(page_title="Calculadora de Metas - Inside Sales", layout="wide")

# ============================
# Configuração da política 2026
# ============================
POLITICA = {
    "BDR": {
        "JR": {"meta": 8, "valor_referencia": 1800.0, "valor_excedente": 150.0, "trimestral": 800.0},
        "PL": {"meta": 10, "valor_referencia": 2500.0, "valor_excedente": 150.0, "trimestral": 800.0},
        "SR": {"meta": 14, "valor_referencia": 3000.0, "valor_excedente": 150.0, "trimestral": 800.0},
    },
    "SDR": {
        "JR": {"meta": 20, "valor_referencia": 1500.0, "valor_excedente": 100.0, "trimestral": 200.0},
        "PL": {"meta": 30, "valor_referencia": 1800.0, "valor_excedente": 100.0, "trimestral": 200.0},
        "SR": {"meta": 40, "valor_referencia": 2500.0, "valor_excedente": 100.0, "trimestral": 200.0},
    },
}

# ============================
# Helpers
# ============================
def ultimo_dia_do_mes(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def dias_uteis(inicio: date, fim: date) -> int:
    if inicio > fim:
        return 0
    qtd = 0
    atual = inicio
    while atual <= fim:
        if atual.weekday() < 5:
            qtd += 1
        atual += timedelta(days=1)
    return qtd


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))


def fmt_brl(valor: float) -> str:
    s = f"{valor:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def fmt_pct(valor: float) -> str:
    return f"{valor * 100:.1f}%"


def get_cor_atingimento(pct: float) -> str:
    if pct < 0.75:
        return "#EF4444"  # vermelho
    if pct < 1.0:
        return "#F59E0B"  # amarelo
    return "#10B981"  # verde


def get_label_atingimento(pct: float) -> str:
    if pct < 0.75:
        return "Abaixo do mínimo para bônus"
    if pct < 1.0:
        return "Faixa proporcional"
    return "Meta batida e acelerando"


def mensagem_status(pct: float) -> str:
    if pct < 0.75:
        return "⚠️ Abaixo do mínimo para bonificação"
    if pct < 1.0:
        return "🚀 Quase lá! Você já entrou na faixa de bônus e está buscando 100%."
    return "🔥 Meta batida! Agora cada excedente aumenta seu bônus."


def barra_progresso_html(percent: float, cor: str) -> str:
    p = clamp(percent, 0, 1.2) * 100
    return f"""
    <div style="margin-top:4px;">
        <div style="background:#1F2937;border-radius:12px;height:24px;width:100%;overflow:hidden;">
            <div style="width:{p:.2f}%;background:{cor};height:100%;border-radius:12px;display:flex;align-items:center;justify-content:center;color:white;font-weight:700;font-size:13px;transition:0.4s;">
                {percent * 100:.1f}%
            </div>
        </div>
    </div>
    """


def card_kpi(label: str, valor: str, cor_valor: str = "#FFFFFF") -> str:
    return f"""
    <div style="padding:10px 0;">
        <div style="font-size:14px;color:#9CA3AF;margin-bottom:4px;">{label}</div>
        <div style="font-size:24px;font-weight:700;color:{cor_valor};line-height:1.1;">{valor}</div>
    </div>
    """


def box_status_html(texto: str, cor: str) -> str:
    return f"""
    <div style="background:#111827;padding:12px 14px;border-radius:10px;margin-top:8px;border-left:4px solid {cor};">
        <div style="font-size:15px;color:#F9FAFB;">{texto}</div>
    </div>
    """


def info_box_html(titulo: str, valor: str, fundo: str, cor_texto: str = "#F9FAFB") -> str:
    return f"""
    <div style="background:{fundo};padding:12px 14px;border-radius:10px;margin-top:8px;">
        <div style="font-size:13px;color:#D1D5DB;margin-bottom:4px;">{titulo}</div>
        <div style="font-size:18px;font-weight:700;color:{cor_texto};">{valor}</div>
    </div>
    """


def calcular_bonus_mensal(qtd_valida: int, meta: int, valor_referencia: float, valor_excedente: float):
    if meta <= 0:
        return {
            "bonus": 0.0,
            "pct": 0.0,
            "faixa": "Sem meta definida",
            "excedente": 0,
        }

    pct = qtd_valida / meta

    if pct < 0.75:
        return {
            "bonus": 0.0,
            "pct": pct,
            "faixa": "Abaixo de 75%",
            "excedente": 0,
        }

    if pct <= 1.0:
        return {
            "bonus": pct * valor_referencia,
            "pct": pct,
            "faixa": "Entre 75% e 100% (proporcional)",
            "excedente": 0,
        }

    excedente = max(qtd_valida - meta, 0)
    return {
        "bonus": valor_referencia + (excedente * valor_excedente),
        "pct": pct,
        "faixa": "Acima de 100% (referência + excedente)",
        "excedente": excedente,
    }


def calcular_atingimento_bdr(out_real: int, evt_real: int, out_ag: int, evt_ag: int):
    equiv_evento_real = evt_real // 2
    equiv_evento_proj = (evt_real + evt_ag) // 2

    realizado_valido = out_real + equiv_evento_real
    projetado_valido = out_real + out_ag + equiv_evento_proj

    return {
        "realizado_valido": realizado_valido,
        "projetado_valido": projetado_valido,
        "equiv_evento_real": equiv_evento_real,
        "equiv_evento_proj": equiv_evento_proj,
    }


def calcular_atingimento_sdr(in_real: int, in_ag: int):
    return {
        "realizado_valido": in_real,
        "projetado_valido": in_real + in_ag,
        "equiv_evento_real": 0,
        "equiv_evento_proj": 0,
    }


def faltam_para_faixa(meta: int, realizado_valido: int, faixa: float) -> int:
    alvo = math.ceil(meta * faixa)
    return max(alvo - realizado_valido, 0)


# ============================
# Datas base
# ============================
hoje = date.today()
inicio_mes = date(hoje.year, hoje.month, 1)
fim_mes = ultimo_dia_do_mes(hoje)

dias_uteis_totais = dias_uteis(inicio_mes, fim_mes)
dias_uteis_restantes = dias_uteis(hoje, fim_mes)
dias_uteis_passados = max(dias_uteis_totais - dias_uteis_restantes, 0)

# ============================
# Cabeçalho
# ============================
st.title("📈 Calculadora de Metas - Inside Sales")
st.caption("Política mensal 2026 | BDR e SDR")

colA, colB = st.columns([1, 2], gap="large")

# ============================
# Entradas
# ============================
with colA:
    st.subheader("Entradas")

    cargo = st.selectbox("Cargo", list(POLITICA.keys()))
    senioridade = st.selectbox("Senioridade", list(POLITICA[cargo].keys()))

    config = POLITICA[cargo][senioridade]
    meta_base = int(config["meta"])
    valor_referencia = float(config["valor_referencia"])
    valor_excedente = float(config["valor_excedente"])
    bonus_trimestral = float(config["trimestral"])

    st.divider()

    if cargo == "BDR":
        st.markdown("### Produção BDR")
        realizadas_outbound = st.number_input("Reuniões realizadas - Outbound", min_value=0, step=1, value=0)
        realizadas_evento = st.number_input("Reuniões realizadas - Evento", min_value=0, step=1, value=0)
        agendadas_outbound = st.number_input("Reuniões agendadas - Outbound", min_value=0, step=1, value=0)
        agendadas_evento = st.number_input("Reuniões agendadas - Evento", min_value=0, step=1, value=0)
    else:
        st.markdown("### Produção SDR")
        realizadas_inbound = st.number_input("Reuniões realizadas - Inbound", min_value=0, step=1, value=0)
        agendadas_inbound = st.number_input("Reuniões agendadas - Inbound", min_value=0, step=1, value=0)

    sobrescrever_meta = st.toggle("Sobrescrever meta", value=False)
    if sobrescrever_meta:
        meta = st.number_input("Meta mensal", min_value=0, step=1, value=meta_base)
    else:
        meta = meta_base

    st.divider()
    st.subheader("Parâmetros da política")
    st.markdown(card_kpi("Meta base", str(meta_base)), unsafe_allow_html=True)
    st.markdown(card_kpi("Valor de referência", fmt_brl(valor_referencia)), unsafe_allow_html=True)
    st.markdown(card_kpi("Valor por excedente", fmt_brl(valor_excedente)), unsafe_allow_html=True)
    st.markdown(card_kpi("Bônus trimestral por venda", fmt_brl(bonus_trimestral)), unsafe_allow_html=True)

    st.divider()
    st.caption(f"Hoje: {hoje.strftime('%d/%m/%Y')}")
    st.caption(f"Dias úteis totais: {dias_uteis_totais}")
    st.caption(f"Dias úteis restantes: {dias_uteis_restantes}")

# ============================
# Cálculos
# ============================
if cargo == "BDR":
    calculos = calcular_atingimento_bdr(
        int(realizadas_outbound),
        int(realizadas_evento),
        int(agendadas_outbound),
        int(agendadas_evento),
    )
    realizadas_brutas = int(realizadas_outbound) + int(realizadas_evento)
    agendadas_brutas = int(agendadas_outbound) + int(agendadas_evento)
else:
    calculos = calcular_atingimento_sdr(int(realizadas_inbound), int(agendadas_inbound))
    realizadas_brutas = int(realizadas_inbound)
    agendadas_brutas = int(agendadas_inbound)

realizado_valido = int(calculos["realizado_valido"])
projetado_valido = int(calculos["projetado_valido"])
equiv_evento_real = int(calculos["equiv_evento_real"])
equiv_evento_proj = int(calculos["equiv_evento_proj"])

faltam_proj = max(meta - projetado_valido, 0)
faltam_real = max(meta - realizado_valido, 0)

atingimento_real = 0.0 if meta == 0 else (realizado_valido / meta)
atingimento_proj = 0.0 if meta == 0 else (projetado_valido / meta)

bonus_real = calcular_bonus_mensal(realizado_valido, meta, valor_referencia, valor_excedente)
bonus_proj = calcular_bonus_mensal(projetado_valido, meta, valor_referencia, valor_excedente)

cor_real = get_cor_atingimento(atingimento_real)
cor_proj = get_cor_atingimento(atingimento_proj)
label_real = get_label_atingimento(atingimento_real)
label_proj = get_label_atingimento(atingimento_proj)

if dias_uteis_totais > 0 and meta > 0:
    ideal_ate_hoje = (meta / dias_uteis_totais) * dias_uteis_passados
else:
    ideal_ate_hoje = 0.0

pace_diff = realizado_valido - ideal_ate_hoje

if dias_uteis_restantes > 0:
    necessario_por_dia = faltam_proj / dias_uteis_restantes
else:
    necessario_por_dia = float("inf") if faltam_proj > 0 else 0.0

necessario_por_semana = necessario_por_dia * 5 if necessario_por_dia != float("inf") else float("inf")

faltam_75 = faltam_para_faixa(meta, realizado_valido, 0.75)
faltam_100 = faltam_para_faixa(meta, realizado_valido, 1.0)

# ============================
# Painel
# ============================
with colB:
    st.subheader("Painel de Atingimento")

    p1, p2, p3, p4 = st.columns(4)
    p1.markdown(card_kpi("Cargo", cargo), unsafe_allow_html=True)
    p2.markdown(card_kpi("Senioridade", senioridade), unsafe_allow_html=True)
    p3.markdown(card_kpi("Meta do mês", str(meta)), unsafe_allow_html=True)
    p4.markdown(card_kpi("Valor ref.", fmt_brl(valor_referencia)), unsafe_allow_html=True)

    st.divider()

    a1, a2, a3, a4 = st.columns(4)
    a1.markdown(card_kpi("Realizado válido", str(realizado_valido), cor_real), unsafe_allow_html=True)
    a2.markdown(card_kpi("Projetado válido", str(projetado_valido), cor_proj), unsafe_allow_html=True)
    a3.markdown(card_kpi("Faltam (proj.)", str(faltam_proj), "#10B981" if faltam_proj == 0 else "#EF4444"), unsafe_allow_html=True)
    a4.markdown(card_kpi("Excedente proj.", str(bonus_proj["excedente"]), "#10B981"), unsafe_allow_html=True)

    if cargo == "BDR":
        st.divider()
        e1, e2, e3, e4 = st.columns(4)
        e1.markdown(card_kpi("Eventos realizados", f"🎟️ {int(realizadas_evento)}"), unsafe_allow_html=True)
        e2.markdown(card_kpi("Eventos agendados", f"🗓️ {int(agendadas_evento)}"), unsafe_allow_html=True)
        e3.markdown(card_kpi("Equiv. evento real", f"⚖️ {equiv_evento_real}"), unsafe_allow_html=True)
        e4.markdown(card_kpi("Equiv. evento proj.", f"⚖️ {equiv_evento_proj}"), unsafe_allow_html=True)

    st.divider()

    b1, b2 = st.columns(2)
    with b1:
        st.markdown(card_kpi("Bônus atual", fmt_brl(bonus_real["bonus"]), cor_real), unsafe_allow_html=True)
        st.caption(f"{label_real} | {bonus_real['faixa']} | {fmt_pct(atingimento_real)}")
    with b2:
        st.markdown(card_kpi("Bônus projetado", fmt_brl(bonus_proj["bonus"]), cor_proj), unsafe_allow_html=True)
        st.caption(f"{label_proj} | {bonus_proj['faixa']} | {fmt_pct(atingimento_proj)}")

    st.markdown(barra_progresso_html(atingimento_proj, cor_proj), unsafe_allow_html=True)
    st.markdown(box_status_html(mensagem_status(atingimento_proj), cor_proj), unsafe_allow_html=True)

    if bonus_proj["excedente"] > 0:
        st.markdown(
            info_box_html(
                "Acelerador projetado",
                f"💰 +{bonus_proj['excedente']} excedente(s) x {fmt_brl(valor_excedente)}",
                "#052e16",
                "#86EFAC",
            ),
            unsafe_allow_html=True,
        )

    st.divider()

    r1, r2, r3 = st.columns(3)
    if necessario_por_dia == float("inf"):
        r1.markdown(card_kpi("Necessário por dia útil", "—"), unsafe_allow_html=True)
        r2.markdown(card_kpi("Necessário por semana útil", "—"), unsafe_allow_html=True)
    else:
        r1.markdown(card_kpi("Necessário por dia útil", f"{necessario_por_dia:.2f}"), unsafe_allow_html=True)
        r2.markdown(card_kpi("Necessário por semana útil", f"{necessario_por_semana:.2f}"), unsafe_allow_html=True)
    r3.markdown(card_kpi("Ideal até hoje", f"{ideal_ate_hoje:.1f}"), unsafe_allow_html=True)

    if meta == 0:
        st.info("Defina uma meta para calcular ritmo e bônus.")
    else:
        if pace_diff >= 0:
            st.success(f"Você está {pace_diff:.1f} reunião(ões) adiantado(a) vs. o ritmo ideal.")
        else:
            st.error(f"Você está {abs(pace_diff):.1f} reunião(ões) atrasado(a) vs. o ritmo ideal.")

    st.divider()

    i1, i2 = st.columns(2)
    i1.markdown(card_kpi("Faltam para 75%", str(faltam_75), "#F59E0B" if faltam_75 > 0 else "#10B981"), unsafe_allow_html=True)
    i2.markdown(card_kpi("Faltam para 100%", str(faltam_100), "#F59E0B" if faltam_100 > 0 else "#10B981"), unsafe_allow_html=True)

    st.caption("Os cards de 75% e 100% consideram somente o realizado válido do mês.")

    with st.expander("Ver memória de cálculo"):
        if cargo == "BDR":
            st.write(
                {
                    "realizadas_outbound": int(realizadas_outbound),
                    "realizadas_evento": int(realizadas_evento),
                    "agendadas_outbound": int(agendadas_outbound),
                    "agendadas_evento": int(agendadas_evento),
                    "equiv_evento_real": equiv_evento_real,
                    "equiv_evento_proj": equiv_evento_proj,
                    "realizado_valido": realizado_valido,
                    "projetado_valido": projetado_valido,
                }
            )
        else:
            st.write(
                {
                    "realizadas_inbound": int(realizadas_inbound),
                    "agendadas_inbound": int(agendadas_inbound),
                    "realizado_valido": realizado_valido,
                    "projetado_valido": projetado_valido,
                }
            )

st.divider()
st.caption(
    "Regras implementadas: abaixo de 75% sem bônus; entre 75% e 100% bônus proporcional ao valor de referência; acima de 100% paga valor de referência cheio + excedente por reunião."
)
st.caption(
    "Para BDR, reuniões de evento têm peso de 50%: a cada 2 reuniões de evento, 1 conta para a meta."
)
