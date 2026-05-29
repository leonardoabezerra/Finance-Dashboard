import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
# Reminder: run docker compose up -d --build

st.set_page_config(page_title="Finance Dashboard", layout="wide")
st.title("Dashboard de Despesas")

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

# Month/Year filter
current_month = datetime.now().strftime("%Y-%m")

available_months = ["Todos"] + sorted(df['mes_ano'].unique().tolist(), reverse=True)

try:
    default_index = available_months.index(current_month)
except ValueError:
    default_index = 0

selected_month = st.sidebar.selectbox("Mês/Ano", available_months, index=default_index)

# Date range filter
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

selected_categories = []

for category in available_categories:
    is_checked = st.sidebar.checkbox(category, value=True, key=f"cat_{category}")

    if is_checked:
        selected_categories.append(category)
    
if not selected_categories:
    st.sidebar.warning("Selecione pelo menos uma categoria.")

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

# KPIs ==================================
st.markdown("### Resumo do Mês")
col1, col2, col3 = st.columns(3)

total_spent = df_filtered['valor'].sum()
highest_expense = df_filtered['valor'].max()
category_sum = df_filtered.groupby('Categoria')['valor'].sum() if not df_filtered.empty else 0
main_category = category_sum.idxmax() if not df_filtered.empty else "N/A"
# current month category total spent
main_category_total = category_sum.max() if main_category != 'N/A' else 0 

# Calculate expenses delta comparison with last month
# Calculate previous month total
if not df_filtered.empty:
    current_date = pd.to_datetime(df_filtered['data'].iloc[0])
    first_day_current_month = current_date.replace(day=1)
    last_day_previous_month = first_day_current_month - pd.Timedelta(days=1)

    # get last months transactions
    df_previous_month = df[
        ((df['data']).dt.month == last_day_previous_month.month) &
        ((df['data']).dt.year == last_day_previous_month.year)
    ]

    if not df_previous_month.empty:
    
        # last month total spent
        previous_total_spent = df_previous_month['valor'].sum()

        # last month highest expense
        previous_highest_expense = df_previous_month['valor'].max()

        # last month main category
        previous_main_category = df_previous_month.groupby('Categoria')['valor'].sum().idxmax()
        if main_category != 'N/A':
            previous_main_category_spent = df_previous_month[df_previous_month['Categoria'] == main_category]['valor'].sum()
        else:
            previous_main_category_spent = 0
    
    else:
        previous_total_spent = 0
        previous_highest_expense = 0
        previous_main_category = 'N/A'
        previous_main_category_spent = 0
   
else:
    previous_total_spent = 0
    previous_highest_expense = 0
    previous_main_category = 'N/A'
    previous_main_category_spent = 0

    
# -- Get % diffs --

# col1
if previous_total_spent > 0:
    percent_diff = ((total_spent - previous_total_spent) / previous_total_spent) * 100
    operator = '+' if percent_diff > 0 else ''
    delta_text1 = f"{operator}" + f"{percent_diff:.1f}% em relação ao mês passado"
else:
    delta_text1 = "Nenhum dado anterior"

col1.metric(
    label="Total Gasto",
    value=f"R$ {total_spent:,.2f}",
    delta=delta_text1,
    delta_color="inverse"
)

# col2
if previous_highest_expense > 0:
    percent_diff = ((highest_expense - previous_highest_expense) / previous_highest_expense) * 100
    operator = '+' if percent_diff > 0 else ''
    delta_text2 = f"{operator}" + f"{percent_diff:.1f}%"
else:
    delta_text2 = "Nenhum dado anterior"

col2.metric(
   label="Maior Despesa",
   value=f"R$ {highest_expense:,.2f}",
   delta=delta_text2,
   delta_color="inverse" 
)

# col3
if previous_main_category_spent > 0:
    percent_diff = ((main_category_total - previous_main_category_spent) / previous_main_category_spent) * 100
    operator = '+' if percent_diff > 0 else ''
    delta_text3 = f"{operator}" + f"{percent_diff:.1f}%"
else:
    delta_text3 = "Nenhum dado anterior"

col3.metric(
    label="Categoria Principal", 
    value=main_category,
    delta=delta_text3,
    delta_color="inverse"
)

st.divider()

# GRAPHICS ================================
col_graph1, col_graph2 = st.columns(2)

# Color dictionary
CATEGORY_COLORS = {
    "Alimentação": "#34D399",
    "Moradia": "#2DD4BF",
    "Transporte": "#22D3EE",
    "Saúde": "#38BDF8",
    "Lazer e Entretenimento": "#60A5FA",
    "Presentes": "#818CF8",
    "Jogos": "#A78BFA",
    "Educação": "#C084FC",
    "Vestuário e Cuidados Pessoais": "#E879F9",
    "Compras e Utilidades": "#008bad",
    "Serviços e Assinaturas": "#94A3B8",
    "Taxas e Impostos": "#64748B",
    "Outros": "#CBD5E1"
}

# --- Pie Chart ---
with col_graph1:
    st.markdown("#### Gastos por Categoria")
    if not df_filtered.empty:
        category_expenses = df_filtered.groupby('Categoria', as_index=False)['valor'].sum()
        fig_category = px.pie(
            category_expenses,
            values='valor',
            names='Categoria',
            hole=0.6,
            color='Categoria',
            color_discrete_map=CATEGORY_COLORS
        )
        st.plotly_chart(fig_category, use_container_width=True)
    else:
        st.info("Sem dados para este mês.")

# --- Stacked Bar Graph ---
with col_graph2:
    st.markdown('#### Evolução Diária')
    if not df_filtered.empty:
        df_chart = df_filtered.copy()

        # Format dates on x axis
        df_chart['data_real'] = df_chart['data'].dt.date
        df_chart['data_label'] = df_chart['data'].dt.strftime('%d/%m')
        
        daily_expenses = df_chart.groupby(['data_real', 'data_label', 'Categoria'], as_index=False)['valor'].sum()
        daily_expenses = daily_expenses.sort_values(by='data_real')

        fig_day = px.bar(
            daily_expenses,
            x='data_label',
            y='valor',
            color='Categoria',
            color_discrete_map=CATEGORY_COLORS,
            labels={'valor': 'Valor (R$)', 'data': 'Data'}
        )

        fig_day.update_layout(
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=0, r=0, t=10, b=0),
            bargap=0.15
        )

        # Set days with no expenses
        first_day = daily_expenses['data_real'].min()
        last_day = daily_expenses['data_real'].max()
        all_days = pd.date_range(first_day, last_day)   
        
        complete_labels = all_days.strftime('%d/%m').tolist()

        # Format spacing between bars
        fig_day.update_xaxes(
            type='category',
            categoryorder='array',
            categoryarray=complete_labels
        )
        
        st.plotly_chart(fig_day, use_container_width=True)
    else:
        st.info("Sem dados para este mês.")
        
# GRAPHICS END =================================

# Expenses History
st.markdown('#### Histórico de Lançamentos')

df_display = df_filtered[['valor', 'Nome', 'Categoria', 'data']].sort_values(by='data', ascending=False).copy()

df_display['valor'] = df_display['valor'].apply(lambda x: f"R$ {x:,.2f}")
df_display['data'] = df_display['data'].dt.strftime('%d/%m/%Y')

# Format column names
df_display = df_display.rename(columns={'valor': 'Valor', 'data': 'Data'})

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