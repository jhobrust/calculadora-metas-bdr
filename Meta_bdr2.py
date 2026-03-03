import streamlit as st
from datetime import date, timedelta
import calendar

st.set_page_config(page_title="Calculadora de Metas BDR", layout="wide")

# ----------------------------
# Config: metas por senioridade (AJUSTE AQUI)
# ----------------------------
METAS_REUNIOES = {
    "Junior": 20,
    "Pleno": 30,
    "Senior": 40,
}

# ----------------------------
# Funções utilitárias
# ----------------------------
def ultimo_dia_do_mes(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)

def dias_uteis(inicio: date, fim: date) -> int:
    """Conta dias úteis (seg-sex) do dia 'inicio' até 'fim' inclusive."""
    if inicio > fim:
        return 0
    qtd = 0
    d = inicio
    while d <= fim:
        if d.weekday() < 5:
            qtd += 1
        d += timedelta(days=1)
    return qtd

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))

def cor_por_status(necessario_por_dia: float, faltam: int) -> tuple[str, str]:
    if faltam <= 0:
        return "#00C853", "Meta batida ✅"
    if necessario_por_dia <= 1:
        return "#1E88E5", "Ritmo confortável 🙂"
    if necessario_por_dia <= 2:
        return "#FB8C00", "Ritmo moderado ⚠️"
    return "#E53935", "Ritmo puxado 🚨"

def barra_progresso_html(percent: float, cor: str) -> str:
    p = clamp(percent, 0, 1) * 100
    return f"""
    <div style="background-color:#2b2b2b; border-radius:14px; height:34px; width:100%; overflow:hidden;">
      <div style="
          width:{p:.2f}%;
          background-color:{cor};
          height:34px;
          display:flex;
          align-items:center;
          justify-content:center;
          color:white;
          font-weight:700;
          font-size:14px;">
          {p:.1f}%
      </div>
    </div>
    """

def calcular_comissao(qtd_reunioes: int, meta: int) -> tuple[int, int, str]:
    """
    Regra:
    - <70%: R$ 0
    - 70% a 99%: R$ 150 por reunião
    - >=100%: R$ 300 por reunião
    Retorna: (valor_total, valor_por_reuniao, faixa_label)
    """
    if meta <= 0:
        return 0, 0, "Sem meta definida"

    pct = qtd_reunioes / meta

    if pct < 0.70:
        return 0, 0, "Abaixo de 70% (sem comissão)"
    elif pct < 1.0:
        return qtd_reunioes * 150, 150, "Entre 70% e 99% (R$ 150/reunião)"
    else:
        return qtd_reunioes * 300, 300, "100%+ (R$ 300/reunião)"

def fmt_brl(valor: int) -> str:
    # Formata 12345 -> "R$ 12.345"
    return f"R$ {valor:,.0f}".replace(",", ".")

# ----------------------------
# App
# ----------------------------
st.title("📈 Calculadora de Metas - BDR (Reuniões)")

hoje = date.today()
inicio_mes = date(hoje.year, hoje.month, 1)
fim_mes = ultimo_dia_do_mes(hoje)

dias_uteis_totais = dias_uteis(inicio_mes, fim_mes)
dias_uteis_restantes = dias_uteis(hoje, fim_mes)
dias_uteis_passados = max(dias_uteis_totais - dias_uteis_restantes, 0)

colA, colB = st.columns([1, 2], gap="large")

# ----------------------------
# Entradas
# ----------------------------
with colA:
    st.subheader("Entradas")

    senioridade = st.selectbox("Qual sua senioridade?", list(METAS_REUNIOES.keys()))
    meta_base = METAS_REUNIOES[senioridade]

    reunioes_realizadas = st.number_input("Quantas reuniões você realizou (no mês)?", min_value=0, step=1, value=0)
    reunioes_agendadas = st.number_input("Quantas reuniões já estão agendadas/confirmadas (ainda este mês)?", min_value=0, step=1, value=0)

    sobrescrever_meta = st.toggle("Sobrescrever meta (opcional)")
    if sobrescrever_meta:
        meta = st.number_input("Meta mensal (reuniões)", min_value=0, value=int(meta_base), step=1)
    else:
        meta = meta_base

    st.divider()
    st.caption(f"Hoje: {hoje.strftime('%d/%m/%Y')}")
    st.caption(f"Início do mês: {inicio_mes.strftime('%d/%m/%Y')}")
    st.caption(f"Fim do mês: {fim_mes.strftime('%d/%m/%Y')}")
    st.caption(f"Dias úteis totais no mês: **{dias_uteis_totais}**")
    st.caption(f"Dias úteis restantes (inclui hoje): **{dias_uteis_restantes}**")

# ----------------------------
# Cálculos
# ----------------------------
realizadas = int(reunioes_realizadas)
agendadas = int(reunioes_agendadas)

total_previsto = realizadas + agendadas
faltam = max(int(meta - total_previsto), 0)

atingimento_previsto = 0.0 if meta == 0 else (total_previsto / meta)
atingimento_previsto_clamped = clamp(atingimento_previsto, 0, 1)

# Necessário por dia útil (gap / dias restantes)
if dias_uteis_restantes > 0:
    necessario_por_dia = faltam / dias_uteis_restantes
else:
    necessario_por_dia = float("inf") if faltam > 0 else 0.0

necessario_por_semana = necessario_por_dia * 5 if necessario_por_dia != float("inf") else float("inf")

# Pacing (ideal até hoje) -> comparo com realizadas (não conto agendadas)
ideal_ate_hoje = 0.0
if dias_uteis_totais > 0 and meta > 0:
    ideal_ate_hoje = (meta / dias_uteis_totais) * dias_uteis_passados

pace_diff = float(realizadas) - ideal_ate_hoje  # >0 adiantado, <0 atrasado

# Comissão atual e projetada
comissao_atual, valor_unit_atual, faixa_atual = calcular_comissao(realizadas, meta)
comissao_proj, valor_unit_proj, faixa_proj = calcular_comissao(total_previsto, meta)

# Cor e status baseados no esforço necessário
cor_status, label_status = cor_por_status(necessario_por_dia if necessario_por_dia != float("inf") else 9999, faltam)

# ----------------------------
# Painel
# ----------------------------
with colB:
    st.subheader("Painel de Atingimento")

    # Métricas (inclui os 2 cards de comissão)
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    c1.metric("Meta do mês", f"{int(meta)}")
    c2.metric("Realizado", f"{realizadas}")
    c3.metric("Agendado", f"{agendadas}")
    c4.metric("Previsto (real+agend)", f"{total_previsto}")
    c5.metric("Faltam", f"{int(faltam)}")
    c6.metric("💰 Comissão atual", fmt_brl(comissao_atual))
    c7.metric("💰 Comissão projetada", fmt_brl(comissao_proj))

    # Barra de progresso do previsto
    st.markdown(barra_progresso_html(atingimento_previsto_clamped, cor_status), unsafe_allow_html=True)
    st.write(f"**Atingimento:** {atingimento_previsto_clamped*100:.1f}% (considerando realizado + agendado)")

    # Texto explicando comissão (bem claro)
    st.caption(
        f"Comissão atual: **{faixa_atual}** (valor atual: **R$ {valor_unit_atual}/reunião**). "
        f"Comissão projetada: **{faixa_proj}** (valor projetado: **R$ {valor_unit_proj}/reunião**)."
    )

    st.divider()

    # Ritmo necessário + ideal até hoje
    colC, colD, colE = st.columns(3)
    if necessario_por_dia == float("inf"):
        colC.metric("Necessário por dia útil", "—")
        colD.metric("Necessário por semana útil", "—")
    else:
        colC.metric("Necessário por dia útil", f"{necessario_por_dia:.2f}")
        colD.metric("Necessário por semana útil", f"{necessario_por_semana:.2f}")
    colE.metric("Ideal até hoje", f"{ideal_ate_hoje:.1f}")

    # Mensagem de pacing
    if meta == 0:
        st.info("Defina uma meta para calcular ritmo e comissão.")
    else:
        if pace_diff >= 0:
            st.success(f"Você está **{pace_diff:.1f}** reuniões **ADIANTADO** vs. ritmo ideal ✅")
        else:
            st.error(f"Você está **{abs(pace_diff):.1f}** reuniões **ATRASADO** vs. ritmo ideal 🚨")

    st.divider()

    # Card de status (visível)
    if faltam <= 0:
        st.success("🎯 Meta batida! (considerando realizado + agendado)")
    else:
        if necessario_por_dia <= 1:
            st.info(f"{label_status} — faltam **{faltam}** reuniões e você precisa de **{necessario_por_dia:.2f}/dia útil**.")
        elif necessario_por_dia <= 2:
            st.warning(f"{label_status} — faltam **{faltam}** reuniões e você precisa de **{necessario_por_dia:.2f}/dia útil**.")
        else:
            st.error(f"{label_status} — faltam **{faltam}** reuniões e você precisa de **{necessario_por_dia:.2f}/dia útil**.")

    # Incentivo: faltam p/ 70% e 100% (considera realizadas)
    st.divider()
    if meta > 0:
        alvo_70 = int((0.70 * meta) + 0.9999)  # arredonda pra cima
        alvo_100 = int(meta)

        faltam_70 = max(alvo_70 - realizadas, 0)
        faltam_100 = max(alvo_100 - realizadas, 0)

        colX, colY = st.columns(2)
        colX.metric("Faltam para 70% (comissão)", f"{faltam_70}")
        colY.metric("Faltam para 100% (R$ 300/reunião)", f"{faltam_100}")
        st.caption("Obs.: os cards 70%/100% consideram **somente reuniões realizadas**.")