import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import datetime

# Cargar datos
sheet_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT6s9qMzmA_sJRko5EDggumO4sybGVq3n-uOmZOMj8CJDnHo9AWZeZOXZGz7cTg4XoqeiPDIgQP3QER/pub?output=csv"
df = pd.read_csv(sheet_url, encoding='utf-8')
df.columns = df.columns.str.strip()
df['RN'] = df['RN'].astype(str).str.strip()

# Convertir fechas con dayfirst=True
df['Inicio'] = pd.to_datetime(df['Inicio'], dayfirst=True, errors='coerce')
df['Fin'] = pd.to_datetime(df['Fin'], dayfirst=True, errors='coerce')

# Mostrar info para debug
print("Columnas:", df.columns.tolist())
print("Primeras filas:\n", df.head())
print("Tipos de datos:\n", df.dtypes)

# Eliminar filas con fechas inválidas
df = df.dropna(subset=['Inicio', 'Fin'])

# Crear columnas auxiliares
df['Inicio_str'] = df['Inicio'].dt.strftime('%d-%m-%Y')
df['Fin_str'] = df['Fin'].dt.strftime('%d-%m-%Y')
df['Duracion'] = (df['Fin'] - df['Inicio']).dt.days
df['Mes'] = df['Fin'].dt.to_period('M').astype(str)
df['RN_trunc'] = df['RN'].apply(lambda x: x if len(x) <= 30 else x[:27] + '...')

color_estado = {
    'Entregado': '#2ecc71',
    'En desarrollo': '#1abc9c',
    'Backlog': '#f1c40f',
    'Para refinar': '#f5d76e',
    'Escribiendo': '#e67e22',
    'Para escribir': '#e74c3c',
    'En Análisis': '#9b59b6',
    'Cancelado': '#95a5a6',
    'Error': '#e74c3c'
}

app = Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("Gantt desarrollo ATI", style={'textAlign': 'center'}),
    html.Div(f"Fecha actual: {datetime.datetime.now().strftime('%d-%m-%Y')}",
             style={'textAlign': 'right', 'fontSize': '14px', 'color': '#888', 'marginBottom': '10px'}),
    html.Div([
        html.Div([
            html.Label("Mes de entrega:"),
            dcc.Dropdown(
                id='mes-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] + [{'label': m, 'value': m} for m in sorted(df['Mes'].unique())],
                value='Todos',
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block'}),
        html.Div([
            html.Label("Estado:"),
            dcc.Dropdown(
                id='estado-dropdown',
                options=[{'label': 'Todos', 'value': 'Todos'}] + [{'label': e, 'value': e} for e in sorted(df['Estado'].unique())],
                value=['Todos'],
                multi=True,
                clearable=False
            )
        ], style={'width': '48%', 'display': 'inline-block', 'marginLeft': '10px'}),
    ], style={'marginBottom': '20px'}),
    html.Div([
        html.Label("Tema:"),
        dcc.RadioItems(
            id='theme-switch',
            options=[
                {'label': 'Claro', 'value': 'light'},
                {'label': 'Oscuro', 'value': 'dark'}
            ],
            value='light',
            labelStyle={'display': 'inline-block', 'marginRight': '10px'}
        )
    ], style={'marginBottom': '20px'}),
    dcc.Graph(id='gantt-graph', style={'height': '80vh'}),
    html.Pre(id='debug-info', style={'whiteSpace': 'pre-wrap', 'padding': '10px', 'border': '1px solid #ddd'})
])

@app.callback(
    [Output('gantt-graph', 'figure'),
     Output('debug-info', 'children')],
    [Input('mes-dropdown', 'value'),
     Input('estado-dropdown', 'value'),
     Input('theme-switch', 'value')]
)
def actualizar_grafico(mes, estados, theme):
    df_filtrado = df.copy()

    if mes != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Mes'] == mes]

    if isinstance(estados, list):
        if 'Todos' not in estados:
            df_filtrado = df_filtrado[df_filtrado['Estado'].isin(estados)]
    else:
        if estados != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['Estado'] == estados]

    # Debug: verificar filas y columnas
    print("Filas después de filtro:", len(df_filtrado))
    print(df_filtrado[['RN_trunc', 'Inicio', 'Fin']].head())

    if df_filtrado.empty:
        return px.scatter(title="No hay datos con los filtros seleccionados"), "No hay datos para mostrar con los filtros actuales."

    if theme == 'dark':
        plot_bgcolor = '#23272f'
        paper_bgcolor = '#23272f'
        font_color = '#f0f0f0'
        gridcolor = '#444'
        current_line_color = '#e74c3c'
    else:
        plot_bgcolor = 'white'
        paper_bgcolor = 'white'
        font_color = '#222'
        gridcolor = '#eee'
        current_line_color = '#e74c3c'

    rn_order = df_filtrado['RN_trunc'].unique().tolist()
    df_filtrado['RN_order'] = df_filtrado['RN_trunc'].map({rn: i for i, rn in enumerate(rn_order)})
    df_filtrado = df_filtrado.sort_values('RN_order')

    fig = px.timeline(
        df_filtrado,
        x_start="Inicio",
        x_end="Fin",
        y="RN_trunc",
        color="Estado",
        custom_data=["RN", "Inicio_str", "Fin_str", "Duracion"],
        color_discrete_map=color_estado,
        title=f"Postventa - {', '.join(estados) if isinstance(estados, list) and 'Todos' not in estados else 'Todos los estados'} | {mes if mes != 'Todos' else 'Todos los meses'}"
    )

    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>Inicio: %{customdata[1]}<br>Fin: %{customdata[2]}<br>Días: %{customdata[3]}",
        marker=dict(line=dict(width=0.3, color='DarkSlateGrey')),
        width=0.3
    )

    fecha_actual = datetime.datetime.now()
    fig.add_vline(
        x=fecha_actual,
        line_width=2,
        line_dash="dash",
        line_color=current_line_color,
        annotation_text="Hoy",
        annotation_font_color=current_line_color,
        annotation_bgcolor=plot_bgcolor
    )

    fig.update_layout(
        xaxis=dict(title="Fecha", tickformat="%d-%m-%Y", gridcolor=gridcolor),
        yaxis=dict(
            autorange="reversed",
            title="Requerimiento",
            categoryorder='array',
            categoryarray=rn_order
        ),
        plot_bgcolor=plot_bgcolor,
        paper_bgcolor=paper_bgcolor,
        font=dict(color=font_color),
        legend=dict(title="Estado", x=1.01, y=1),
        margin=dict(l=20, r=250, t=50, b=50),
        height=800
    )

    debug_info = f"Datos filtrados: {len(df_filtrado)} filas\n"
    debug_info += f"Estados únicos: {df_filtrado['Estado'].unique().tolist()}\n"
    debug_info += f"Rango fechas: {df_filtrado['Inicio'].min().strftime('%d-%m-%Y')} a {df_filtrado['Fin'].max().strftime('%d-%m-%Y')}\n"
    debug_info += "Gráfico generado correctamente."

    return fig, debug_info

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)


















































