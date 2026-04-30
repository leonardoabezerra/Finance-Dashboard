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

# Filter sidebar
st.sidebar.header("Filtros")
available_months = sorted(df['mes_ano'].unique().tolist(), reverse=True)
selected_month = st.sidebar.selectbox("Selecione o mês/ano", available_months)

df_filtered = df[df['mes_ano'] == selected_month] # Apply filter

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
st.dataframe(
    df_filtered[['data', 'Nome', 'Categoria', 'valor']].sort_values(by='data', ascending=False),
    use_container_width=True,
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