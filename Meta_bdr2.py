import streamlit as st
from datetime import date, timedelta
import calendar
import math

st.set_page_config(page_title="Calculadora de Metas - Inside Sales", layout="wide")

# =========================================================
# CONFIGURAÇÕES DA POLÍTICA 2026
# =========================================================
# Regra usada no app:
# - < 75%: sem bônus
# - 75% a 100%: bônus proporcional ao atingimento
# - > 100%: valor de referência cheio + excedente por lead
#
# Observação:
# A PEC fala em "Até R$ X" de referência e em excedente acima de 101%.
# Por isso, aqui o comportamento adotado foi:
# acima de 100% => trava o valor base na referência e soma excedente.
# =========================================================

CONFIG_CARGOS = {
    "BDR": {
        "JR": {
            "meta": 8,
            "valor_referencia": 1800.0,
            "valor_excedente": 150.0,
            "bonus_trimestral_por_venda": 800.0,
        },
        "PL": {
            "meta": 10,
            "valor_referencia": 2500.0,
            "valor_excedente": 150.0,
            "bonus_trimestral_por_venda": 800.0,
        },
        "SR": {
            "meta": 14,
            "valor_referencia": 3000.0,
            "valor_excedente": 150.0,
            "bonus_trimestral_por_venda": 800.0,
        },
    },
    "SDR": {
        "JR": {
            "meta": 20,
            "valor_referencia": 1500.0,
            "valor_excedente": 100.0,
            "bonus_trimestral_por_venda": 200.0,
        },
        "PL": {
            "meta": 30,
            "valor_referencia": 1800.0,
            "valor_excedente": 100.0,
            "bonus_trimestral_por_venda": 200.0,
        },
        "SR": {
            "meta": 40,
            "valor_referencia": 2500.0,
            "valor_excedente": 100.0,
            "bonus_trimestral_por_venda": 200.0,
        },
    },
}


# =========================================================
# FUNÇÕES UTILITÁRIAS
# =========================================================
def ultimo_dia_do_mes(d: date) -> date:
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)


def dias_uteis(inicio: date, fim: date) -> int:
    """Conta dias úteis (seg-sex) de inicio até fim, inclusive."""
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


def fmt_brl(valor: float) -> str:
    txt = f"{valor:,.2f}"
    txt = txt.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {txt}"


def fmt_int(valor: float) -> str:
    if float(valor).is_integer():
        return str(int(valor))
    return f"{valor:.2f}".replace(".", ",")


def cor_por_status(necessario_por_dia: float, faltam: float) -> tuple[str, str]:
    if faltam <= 0:
        return "#00C853", "Meta batida ✅"
    if necessario_por_dia <= 1:
        return "#1E88E5", "Ritmo confortável 🙂"
    if necessario_por_dia <= 2:
        return "#FB8C00", "Ritmo moderado ⚠️"
    return "#E53935", "Ritmo puxado 🚨"


def barra_progresso_html(percent: float, cor: str) -> str:
    p = clamp(percent, 0, 1.2) * 100
    largura = min(p, 100)
    return f"""
    <div style="background-color:#2b2b2b; border-radius:14px; height:34px; width:100%; overflow:hidden;">
      <div style="
          width:{largura:.2f}%;
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


def arredondar_alvo_para_cima(valor: float) -> int:
    return math.ceil(valor)


# =========================================================
# REGRAS DE NEGÓCIO
# =========================================================
def calcular_bonus_mensal(
    qtd_valida: float,
    meta: int,
    valor_referencia: float,
    valor_excedente: float,
) -> tuple[float, float, str, float]:
    """
    Retorna:
    (bonus_total, percentual_atingimento, faixa_label, qtd_excedente)
    """
    if meta <= 0:
        return 0.0, 0.0, "Sem meta definida", 0.0

    pct = qtd_valida / meta

    if pct < 0.75:
        return 0.0, pct, "Abaixo de 75% (sem bônus)", 0.0

    if pct <= 1.0:
        bonus = pct * valor_referencia
        return bonus, pct, "Entre 75% e 100% (bônus proporcional)", 0.0

    excedente = max(qtd_valida - meta, 0.0)
    bonus = valor_referencia + (excedente * valor_excedente)
    return bonus, pct, "Acima de 100% (referência cheia + excedente)", excedente


def calcular_equivalencia_bdr(
    outbound_realizadas: int,
    evento_realizadas: int,
    outbound_agendadas: int,
    evento_agendadas: int,
) -> dict:
    """
    Para BDR:
    - evento vale 50%
    - 2 eventos = 1 lead válido para meta

    Real:
      outbound_realizadas + floor(evento_realizadas / 2)

    Projetado:
      (outbound_realizadas + outbound_agendadas)
      + floor((evento_realizadas + evento_agendadas) / 2)
    """
    eventos_validos_real = evento_realizadas // 2
    eventos_validos_proj = (evento_realizadas + evento_agendadas) // 2

    realizado_valido = outbound_realizadas + eventos_validos_real
    projetado_valido = (outbound_realizadas + outbound_agendadas) + eventos_validos_proj

    return {
        "eventos_validos_real": eventos_validos_real,
        "eventos_validos_proj": eventos_validos_proj,
        "realizado_valido": realizado_valido,
        "projetado_valido": projetado_valido,
    }


def calcular_equivalencia_sdr(
    inbound_realizadas: int,
    inbound_agendadas: int,
) -> dict:
    realizado_valido = inbound_realizadas
    projetado_valido = inbound_realizadas + inbound_agendadas

    return {
        "eventos_validos_real": 0,
        "eventos_validos_proj": 0,
        "realizado_valido": realizado_valido,
        "projetado_valido": projetado_valido,
    }


# =========================================================
# APP
# =========================================================
st.title("📈 Calculadora de Metas - Inside Sales")
st.caption("Política mensal 2026 | BDR e SDR")

hoje = date.today()
inicio_mes = date(hoje.year, hoje.month, 1)
fim_mes = ultimo_dia_do_mes(hoje)

dias_uteis_totais = dias_uteis(inicio_mes, fim_mes)
dias_uteis_restantes = dias_uteis(hoje, fim_mes)
dias_uteis_passados = max(dias_uteis_totais - dias_uteis_restantes, 0)

colA, colB = st.columns([1, 2], gap="large")

# =========================================================
# ENTRADAS
# =========================================================
with colA:
    st.subheader("Entradas")

    cargo = st.selectbox("Cargo", ["BDR", "SDR"])
    senioridade = st.selectbox("Senioridade", ["JR", "PL", "SR"])

    conf = CONFIG_CARGOS[cargo][senioridade]
    meta_base = conf["meta"]
    valor_referencia = conf["valor_referencia"]
    valor_excedente = conf["valor_excedente"]

    st.divider()
    st.markdown("### Parâmetros da política")
    st.metric("Meta base", f"{meta_base}")
    st.metric("Valor de referência", fmt_brl(valor_referencia))
    st.metric("Valor por lead excedente", fmt_brl(valor_excedente))

    sobrescrever_meta = st.toggle("Sobrescrever meta (opcional)")
    if sobrescrever_meta:
        meta = st.number_input("Meta mensal (reuniões)", min_value=0, value=int(meta_base), step=1)
    else:
        meta = meta_base

    st.divider()
    st.markdown("### Produção do mês")

    if cargo == "BDR":
        outbound_realizadas = st.number_input(
            "Reuniões realizadas - Outbound",
            min_value=0,
            step=1,
            value=0,
        )
        evento_realizadas = st.number_input(
            "Reuniões realizadas - Evento",
            min_value=0,
            step=1,
            value=0,
        )
        outbound_agendadas = st.number_input(
            "Reuniões agendadas - Outbound",
            min_value=0,
            step=1,
            value=0,
        )
        evento_agendadas = st.number_input(
            "Reuniões agendadas - Evento",
            min_value=0,
            step=1,
            value=0,
        )

        resultado_base = calcular_equivalencia_bdr(
            outbound_realizadas=int(outbound_realizadas),
            evento_realizadas=int(evento_realizadas),
            outbound_agendadas=int(outbound_agendadas),
            evento_agendadas=int(evento_agendadas),
        )

    else:
        inbound_realizadas = st.number_input(
            "Agendas qualificadas realizadas - Inbound",
            min_value=0,
            step=1,
            value=0,
        )
        inbound_agendadas = st.number_input(
            "Agendas qualificadas agendadas - Inbound",
            min_value=0,
            step=1,
            value=0,
        )

        resultado_base = calcular_equivalencia_sdr(
            inbound_realizadas=int(inbound_realizadas),
            inbound_agendadas=int(inbound_agendadas),
        )

    st.divider()
    st.caption(f"Hoje: {hoje.strftime('%d/%m/%Y')}")
    st.caption(f"Início do mês: {inicio_mes.strftime('%d/%m/%Y')}")
    st.caption(f"Fim do mês: {fim_mes.strftime('%d/%m/%Y')}")
    st.caption(f"Dias úteis totais no mês: **{dias_uteis_totais}**")
    st.caption(f"Dias úteis restantes (inclui hoje): **{dias_uteis_restantes}**")


# =========================================================
# CÁLCULOS
# =========================================================
realizado_valido = float(resultado_base["realizado_valido"])
projetado_valido = float(resultado_base["projetado_valido"])

faltam_proj = max(meta - projetado_valido, 0.0)
faltam_real = max(meta - realizado_valido, 0.0)

atingimento_real = 0.0 if meta == 0 else (realizado_valido / meta)
atingimento_proj = 0.0 if meta == 0 else (projetado_valido / meta)

atingimento_real_clamped = clamp(atingimento_real, 0, 1.2)
atingimento_proj_clamped = clamp(atingimento_proj, 0, 1.2)

if dias_uteis_restantes > 0:
    necessario_por_dia = faltam_proj / dias_uteis_restantes
else:
    necessario_por_dia = float("inf") if faltam_proj > 0 else 0.0

necessario_por_semana = necessario_por_dia * 5 if necessario_por_dia != float("inf") else float("inf")

ideal_ate_hoje = 0.0
if dias_uteis_totais > 0 and meta > 0:
    ideal_ate_hoje = (meta / dias_uteis_totais) * dias_uteis_passados

pace_diff = realizado_valido - ideal_ate_hoje

bonus_atual, pct_atual, faixa_atual, excedente_atual = calcular_bonus_mensal(
    qtd_valida=realizado_valido,
    meta=meta,
    valor_referencia=valor_referencia,
    valor_excedente=valor_excedente,
)

bonus_proj, pct_proj, faixa_proj, excedente_proj = calcular_bonus_mensal(
    qtd_valida=projetado_valido,
    meta=meta,
    valor_referencia=valor_referencia,
    valor_excedente=valor_excedente,
)

cor_status, label_status = cor_por_status(
    necessario_por_dia if necessario_por_dia != float("inf") else 9999,
    faltam_proj,
)

alvo_75 = arredondar_alvo_para_cima(meta * 0.75)
alvo_100 = int(meta)

faltam_75_real = max(alvo_75 - realizado_valido, 0)
faltam_100_real = max(alvo_100 - realizado_valido, 0)

# =========================================================
# PAINEL
# =========================================================
with colB:
    st.subheader("Painel de Atingimento")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Cargo", cargo)
    p2.metric("Senioridade", senioridade)
    p3.metric("Meta do mês", f"{int(meta)}")
    p4.metric("Valor ref.", fmt_brl(valor_referencia))

    st.divider()

    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Realizado válido", fmt_int(realizado_valido))
    a2.metric("Projetado válido", fmt_int(projetado_valido))
    a3.metric("Faltam (proj.)", fmt_int(faltam_proj))
    a4.metric("Excedente proj.", fmt_int(excedente_proj))

    if cargo == "BDR":
        st.divider()
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Eventos realizados", f"{int(evento_realizadas)}")
        e2.metric("Eventos agendados", f"{int(evento_agendadas)}")
        e3.metric("Equiv. evento real", f"{int(resultado_base['eventos_validos_real'])}")
        e4.metric("Equiv. evento proj.", f"{int(resultado_base['eventos_validos_proj'])}")

        st.caption(
            "Regra de evento: **a cada 2 reuniões de evento, 1 conta para a meta do BDR**."
        )

    st.divider()

    b1, b2 = st.columns(2)
    b1.metric("💰 Bônus atual", fmt_brl(bonus_atual))
    b2.metric("💰 Bônus projetado", fmt_brl(bonus_proj))

    st.caption(
        f"Bônus atual: **{faixa_atual}** | "
        f"Atingimento atual: **{pct_atual*100:.1f}%** | "
        f"Bônus projetado: **{faixa_proj}** | "
        f"Atingimento projetado: **{pct_proj*100:.1f}%**"
    )

    st.divider()

    st.markdown(barra_progresso_html(atingimento_proj_clamped, cor_status), unsafe_allow_html=True)
    st.write(f"**Atingimento projetado:** {pct_proj*100:.1f}% (considerando realizado + agendado)")

    st.divider()

    c1, c2, c3 = st.columns(3)
    if necessario_por_dia == float("inf"):
        c1.metric("Necessário por dia útil", "—")
        c2.metric("Necessário por semana útil", "—")
    else:
        c1.metric("Necessário por dia útil", f"{necessario_por_dia:.2f}")
        c2.metric("Necessário por semana útil", f"{necessario_por_semana:.2f}")
    c3.metric("Ideal até hoje", f"{ideal_ate_hoje:.1f}")

    if meta == 0:
        st.info("Defina uma meta para calcular ritmo e bônus.")
    else:
        if pace_diff >= 0:
            st.success(f"Você está **{pace_diff:.1f}** reuniões **ADIANTADO** vs. ritmo ideal ✅")
        else:
            st.error(f"Você está **{abs(pace_diff):.1f}** reuniões **ATRASADO** vs. ritmo ideal 🚨")

    st.divider()

    if faltam_proj <= 0:
        st.success("🎯 Meta batida! (considerando realizado + agendado)")
    else:
        if necessario_por_dia <= 1:
            st.info(
                f"{label_status} — faltam **{fmt_int(faltam_proj)}** reuniões e você precisa de "
                f"**{necessario_por_dia:.2f}/dia útil**."
            )
        elif necessario_por_dia <= 2:
            st.warning(
                f"{label_status} — faltam **{fmt_int(faltam_proj)}** reuniões e você precisa de "
                f"**{necessario_por_dia:.2f}/dia útil**."
            )
        else:
            st.error(
                f"{label_status} — faltam **{fmt_int(faltam_proj)}** reuniões e você precisa de "
                f"**{necessario_por_dia:.2f}/dia útil**."
            )

    st.divider()

    x1, x2 = st.columns(2)
    x1.metric("Faltam para 75% (real)", fmt_int(faltam_75_real))
    x2.metric("Faltam para 100% (real)", fmt_int(faltam_100_real))

    st.caption("Esses cards consideram apenas a produção válida já realizada.")

    st.divider()
    st.markdown("### Resumo da regra aplicada")
    st.write(f"- **Cargo:** {cargo}")
    st.write(f"- **Senioridade:** {senioridade}")
    st.write(f"- **Meta:** {meta}")
    st.write(f"- **Gatilho de bônus:** 75%")
    st.write(f"- **Valor de referência:** {fmt_brl(valor_referencia)}")
    st.write(f"- **Valor por lead excedente:** {fmt_brl(valor_excedente)}")

    if cargo == "BDR":
        st.write("- **Evento:** 2 reuniões de evento = 1 reunião válida para meta")
