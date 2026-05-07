import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
# Reminder: run docker compose up -d --build
# TODO: Create container and github repo

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("My Finance Dashboard")

# Autorefresh loop
st_autorefresh(interval=10000, key="atualizacao_automatica")

# Connect and read data
conn = st.connection("gsheets", type=GSheetsConnection)

current_year = datetime.now().strftime("%Y")
try:
    df = conn.read(worksheet=current_year, ttl=10)
except Exception:
    st.error(f"Aba '{current_year}' não encontrada. Verifique se a aba foi criada na planilha")
    st.stop()
    
df = df.dropna(how="all") # Drop rows where all elements are NaN

# Data cleaning and processing   
df['data'] = pd.to_datetime(df['Data/Hora'], errors='coerce')
df['valor'] = pd.to_numeric(df['Valor'], errors='coerce')


df = df.dropna(subset=['data', 'valor']) # Drop rows with invalid 'data' or 'valor'

df['mes_ano'] = df['data'].dt.to_period('M').astype(str) # Create 'mes_ano' column in 'YYYY-MM' format

# FILTER SIDEBAR ==========================
st.sidebar.header("Filtros")

# Text Search (Nome or Descrição)
search_query = st.sidebar.text_input(
    "Buscar Lançamento",
    placeholder="Ex: Mercado, Uber, Conta de Luz..."
)

st.sidebar.divider()

# Time filters
st.sidebar.subheader("Período")
available_months = ["Todos"] + sorted(df['mes_ano'].unique().tolist(), reverse=True)
selected_month = st.sidebar.selectbox("Mês/Ano (Atalho rápido)", available_months)

min_date = df['data'].min().date()
max_date = df['data'].max().date()

date_range = st.sidebar.date_input(
    "Ou selecione um período específico",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    format="DD/MM/YYYY"
)

st.sidebar.divider()

# Category Filter
st.sidebar.subheader("Categorias")
available_categories = sorted(df['Categoria'].dropna().unique().tolist())
selected_categories = st.sidebar.multiselect(
    "Selecione as categorias",
    options=available_categories,
    default=available_categories,
    help="Deixe vazio para ocultar todos os dados ou selecione categorias para exibir."
)

st.sidebar.divider()

# Value range slider
st.sidebar.subheader("Faixa de Valor")
min_val = float(df['valor'].min())
max_val = float(df['valor'].max())

# Show slider only if valid range is available
if min_val < max_val:
    value_range = st.sidebar.slider(
        "Selecione a faixa de R$",
        min_value=min_val,
        max_value=max_val,
        value=(min_val, max_val),
        step=10.0
    )
else:
    value_range = (min_val, max_val)

# APPLY FILTERS ==================
df_filtered = df.copy()

if search_query:
    mask_nome = df_filtered['Nome'].str.contains(search_query, case=False, na=False)
    mask_desc = df_filtered['Descrição'].str.contains(search_query, case=False, na=False)

    df_filtered = df_filtered[mask_nome | mask_desc]

if selected_month != "Todos":
    df_filtered = df_filtered[df_filtered['mes_ano'] == selected_month]

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
    df_filtered = df_filtered[
        (df_filtered['data'].dt.date >= start_date) &
        (df_filtered['data'].dt.date <= end_date)
    ]

df_filtered = df_filtered[df_filtered['Categoria'].isin(selected_categories)]

df_filtered = df_filtered[
    (df_filtered['valor'] >= value_range[0]) &
    (df_filtered['valor'] <= value_range[1])
]

if df_filtered.empty:
    st.warning("Nenhum lançamento encontrado com a combinação de filtros atual.")

# FILTER SIDEBAR END ==========================

# KPIs
st.markdown("### Resumo do Mês")
col1, col2, col3 = st.columns(3)

total_spent = df_filtered['valor'].sum()
highest_expense = df_filtered['valor'].max()
main_category = df_filtered.groupby('Categoria')['valor'].sum().idxmax() if not df_filtered.empty else "N/A"

col1.metric("Total Gasto", f"R$ {total_spent:,.2f}")
col2.metric("Maior Despesa", f"R$ {highest_expense:,.2f}")
col3.metric("Categoria Principal", main_category)

st.divider()

# Graphics
col_graph1, col_graph2 = st.columns(2)

with col_graph1:
    st.markdown("#### Gastos por Categoria")
    if not df_filtered.empty:
        category_expenses = df_filtered.groupby('Categoria', as_index=False)['valor'].sum()
        fig_category = px.pie(category_expenses, values='valor', names='Categoria', hole=0.4)
        st.plotly_chart(fig_category, use_container_width=True)
    else:
        st.info("Sem dados para este mês.")

with col_graph2:
    st.markdown('#### Evolução Diária')
    if not df_filtered.empty:
        daily_expenses = df_filtered.groupby('data', as_index=False)['valor'].sum()
        fig_day = px.line(daily_expenses, x='data', y='valor', markers=True)
        st.plotly_chart(fig_day, use_container_width=True)
    else:
        st.info("Sem dados para este mês.")

# Expenses History
st.markdown('#### Histórico de Lançamentos')

df_display = df_filtered[['valor', 'Nome', 'Categoria', 'data']].sort_values(by='data', ascending=False).copy()

df_display['valor'] = df_display['valor'].apply(lambda x: f"R$ {x:,.2f}")
df_display['data'] = df_display['data'].dt.strftime('%d/%m/%Y')

st.dataframe(
    df_display,
    use_container_width=True,
    hide_index=True,
)


#    ___           _________     _________
#   /\  \         /\   ______\  /\   ____  \
#   \ \  \        \ \   ___\ /  \ \  \__/\  \
#    \ \  \______  \ \  \_/____  \ \  \___\  \    ___
#     \ \_________\ \ \_________\ \ \_________\  /\__\
#      \/_________/  \/_________/  \/_________/  \/__/
#
#
#    Developed by: Leonardo Alves Bezerra.