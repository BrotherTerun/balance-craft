import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import pandas as pd
from sqlalchemy import create_engine

# Настройки подключения к БД
DB_URL = 'mysql+mysqlconnector://root:2256@localhost/monitor_rpg_model'


def load_simulation_data():
    try:
        engine = create_engine(DB_URL)
        query = "SELECT * FROM simulation_results ORDER BY simulation_id, t"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print("Ошибка загрузки данных симуляции:", e)
        return pd.DataFrame()


def load_chaos_indicators():
    try:
        engine = create_engine(DB_URL)
        query = "SELECT * FROM chaos_indicators"
        df = pd.read_sql(query, engine)
        return df
    except Exception as e:
        print("Ошибка загрузки индикаторов хаоса:", e)
        return pd.DataFrame()


app = dash.Dash(__name__)
app.title = "Визуализация симуляции RPG экономики"

# Предзагрузка данных
df_sim = load_simulation_data()
df_chaos = load_chaos_indicators()

# Ключевое исправление: преобразуем в список и проверяем длину
simulation_ids = df_sim['simulation_id'].unique().tolist() if not df_sim.empty else []

app.layout = html.Div([
    html.H1("Визуализация симуляции экономики RPG", style={'textAlign': 'center'}),
    html.Label("Выберите симуляцию:"),
    dcc.Dropdown(
        id='simulation-dropdown',
        options=[{'label': sid, 'value': sid} for sid in simulation_ids],
        value=simulation_ids[-1] if simulation_ids else None  # Теперь проверка работает корректно
    ),
    dcc.Graph(id='time-series-graph'),
    dcc.Graph(id='phase-portrait'),
    dcc.Graph(id='chaos-indicators')
])


@app.callback(
    [Output('time-series-graph', 'figure'),
     Output('phase-portrait', 'figure'),
     Output('chaos-indicators', 'figure')],
    [Input('simulation-dropdown', 'value')]
)
def update_graphs(sim_id):
    if not sim_id or df_sim.empty:
        return go.Figure(), go.Figure(), go.Figure()

    sim_df = df_sim[df_sim['simulation_id'] == sim_id]
    if sim_df.empty:
        return go.Figure(), go.Figure(), go.Figure()

    chaos_row = df_chaos[df_chaos['simulation_id'] == sim_id].squeeze() if not df_chaos.empty else None

    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(x=sim_df['t'], y=sim_df['Y_sim'], name='Y(t)'))
    fig_time.add_trace(go.Scatter(x=sim_df['t'], y=sim_df['K_sim'], name='K(t)'))
    fig_time.add_trace(go.Scatter(x=sim_df['t'], y=sim_df['L_sim'], name='L(t)'))
    fig_time.update_layout(title='Временные ряды', xaxis_title='t', yaxis_title='Значения')

    fig_phase = go.Figure()
    fig_phase.add_trace(go.Scatter(x=sim_df['K_sim'], y=sim_df['Y_sim'], name='K vs Y'))
    fig_phase.update_layout(title='Фазовый портрет', xaxis_title='K', yaxis_title='Y')

    fig_chaos = go.Figure()
    if chaos_row is not None and not pd.isnull(chaos_row.get('lyapunov_exp')):
        fig_chaos.add_trace(go.Indicator(
            mode="number",
            value=float(chaos_row['lyapunov_exp']),
            title={'text': "Показатель Ляпунова"}
        ))
        fig_chaos.update_layout(title=f"Хаотический режим: {'Да' if chaos_row['is_chaotic'] else 'Нет'}")

    return fig_time, fig_phase, fig_chaos


if __name__ == '__main__':
    app.run(debug=True)
