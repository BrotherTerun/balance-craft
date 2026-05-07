import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import mysql.connector
from scipy.interpolate import interp1d
import uuid
import traceback

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}


class EconomicModelSimulator:
    def __init__(self, player_id, simulation_id=None, A=1.0, method='euler'):
        self.player_id = player_id
        self.simulation_id = simulation_id if simulation_id else self.generate_simulation_id()
        self.A = A
        self.method = method
        self.time_points = []
        self.K_values = []
        self.Y_values = []
        self.L_values = []
        self.s_values = []
        self.delta_values = []
        self.alpha_values = []
        self.param_funcs = None

        # Загрузка данных сразу при инициализации
        self.load_player_data()

    @staticmethod
    def generate_simulation_id():
        """Генерирует уникальный ID симуляции"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"sim_{timestamp}_{unique_id}"

    def load_player_data(self):
        """Загружает исторические данные игрока из базы данных"""
        conn = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor(dictionary=True)

            query = """
            SELECT 
                sm.session_id,
                MAX(CASE WHEN sm.metric_name = 'K_POWER_SCORE' THEN sm.metric_value END) AS K,
                MAX(CASE WHEN sm.metric_name = 'Y_EXP_VELOCITY' THEN sm.metric_value END) AS Y,
                MAX(CASE WHEN sm.metric_name = 'L_SESSION_ENGAGEMENT' THEN sm.metric_value END) AS L,
                MAX(CASE WHEN sm.metric_name = 'S_UNSPENT_RESOURCES' THEN sm.metric_value END) AS s,
                MAX(CASE WHEN sm.metric_name = 'D_PROGRESSION_DECAY' THEN sm.metric_value END) AS delta,
                MAX(CASE WHEN sm.metric_name = 'A_PROGRESSION_ROI' THEN sm.metric_value END) AS alpha
            FROM session_metrics sm
            JOIN sessions s ON sm.session_id = s.id
            WHERE s.player_id = %s
            GROUP BY sm.session_id
            ORDER BY s.session_start
            """
            cursor.execute(query, (self.player_id,))
            sessions_data = cursor.fetchall()

            if not sessions_data:
                print(f"[WARNING] No data found for player {self.player_id}")
                return 0

            # Проверка и преобразование данных
            for session in sessions_data:
                for key in ['K', 'Y', 'L', 's', 'delta', 'alpha']:
                    if session[key] is None:
                        print(f"[WARNING] Null value in session {session['session_id']} for metric {key}")
                        session[key] = 0.0

            self.time_points = list(range(len(sessions_data)))
            self.K_values = [float(session['K']) for session in sessions_data]
            self.Y_values = [float(session['Y']) for session in sessions_data]
            self.L_values = [float(session['L']) for session in sessions_data]
            self.s_values = [float(session['s']) for session in sessions_data]
            self.delta_values = [float(session['delta']) for session in sessions_data]
            self.alpha_values = [float(session['alpha']) for session in sessions_data]

            print(f"Loaded {len(self.time_points)} historical sessions for player {self.player_id}")
            print(f"Sample K values: {self.K_values[:3]}")
            return len(sessions_data)

        except Exception as e:
            print(f"Error loading player data: {str(e)}")
            traceback.print_exc()
            return 0
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def validate_data(self):
        """Проверяет наличие необходимых данных для симуляции"""
        if not self.time_points:
            print("Validation failed: No time points available")
            return False

        required_arrays = [
            self.K_values, self.Y_values, self.L_values,
            self.s_values, self.delta_values, self.alpha_values
        ]

        for i, arr in enumerate(required_arrays):
            if not arr:
                print(f"Validation failed: Array {i} is empty")
                return False
            if len(arr) != len(self.time_points):
                print(f"Validation failed: Array {i} has different length ({len(arr)} vs {len(self.time_points)})")
                return False

        print("Data validation passed")
        return True

    def interpolate_parameters(self):
        """Создает интерполированные функции для параметров"""
        if not self.time_points:
            raise RuntimeError("Cannot interpolate without time points")

        return {
            's': interp1d(self.time_points, self.s_values, kind='nearest', fill_value="extrapolate"),
            'delta': interp1d(self.time_points, self.delta_values, kind='nearest', fill_value="extrapolate"),
            'alpha': interp1d(self.time_points, self.alpha_values, kind='nearest', fill_value="extrapolate"),
            'L': interp1d(self.time_points, self.L_values, kind='nearest', fill_value="extrapolate")
        }

    def production_function(self, K, L, alpha):
        """Производственная функция Y = A * K^alpha * L^(1-alpha)"""
        return self.A * (K ** alpha) * (L ** (1 - alpha))

    def capital_equation(self, K, Y, s, delta):
        """Уравнение капитала dK/dt = sY - δK"""
        return s * Y - delta * K

    def euler_step(self, K, Y, s, delta, alpha, L, dt):
        """Один шаг метода Эйлера"""
        dK = self.capital_equation(K, Y, s, delta) * dt
        K_new = K + dK
        Y_new = self.production_function(K_new, L, alpha)
        return K_new, Y_new

    def rk4_step(self, K, Y, s, delta, alpha, L, dt):
        """Один шаг метода Рунге-Кутты 4-го порядка"""
        k1 = self.capital_equation(K, Y, s, delta)
        K2 = K + 0.5 * dt * k1
        Y2 = self.production_function(K2, L, alpha)
        k2 = self.capital_equation(K2, Y2, s, delta)

        K3 = K + 0.5 * dt * k2
        Y3 = self.production_function(K3, L, alpha)
        k3 = self.capital_equation(K3, Y3, s, delta)

        K4 = K + dt * k3
        Y4 = self.production_function(K4, L, alpha)
        k4 = self.capital_equation(K4, Y4, s, delta)

        dK = (dt / 6) * (k1 + 2 * k2 + 2 * k3 + k4)
        K_new = K + dK
        Y_new = self.production_function(K_new, L, alpha)
        return K_new, Y_new

    def simulate(self, t_start, t_end, dt=0.1):
        """Выполняет симуляцию экономической модели"""
        try:
            # Проверка данных перед симуляцией
            if not self.validate_data():
                raise RuntimeError("Invalid data, cannot simulate")

            if not self.time_points:
                raise RuntimeError("No time points available for simulation")

            last_index = self.time_points[-1]
            print(f"Starting simulation from last session index: {last_index}")

            # Создание интерполированных функций
            self.param_funcs = self.interpolate_parameters()

            # Подготовка временных точек
            time_steps = np.arange(t_start, t_end + dt, dt)
            K_sim = np.zeros_like(time_steps)
            Y_sim = np.zeros_like(time_steps)

            # Начальные условия (последние исторические значения)
            K_sim[0] = self.K_values[-1]
            Y_sim[0] = self.Y_values[-1]

            # Выбор метода интегрирования
            step_method = self.euler_step if self.method == 'euler' else self.rk4_step

            # Основной цикл симуляции
            for i in range(1, len(time_steps)):
                t = time_steps[i]
                s = self.param_funcs['s'](t)
                delta = self.param_funcs['delta'](t)
                alpha = self.param_funcs['alpha'](t)
                L = self.param_funcs['L'](t)

                K_sim[i], Y_sim[i] = step_method(
                    K_sim[i - 1], Y_sim[i - 1], s, delta, alpha, L, dt
                )

                # Проверка на числовую устойчивость
                if np.isnan(K_sim[i]) or np.isinf(K_sim[i]):
                    print(f"Numerical instability detected at step {i}: t={t}, K={K_sim[i]}")
                    # Обрезаем массивы до текущего шага
                    time_steps = time_steps[:i + 1]
                    K_sim = K_sim[:i + 1]
                    Y_sim = Y_sim[:i + 1]
                    break

                if abs(K_sim[i]) > 1e15:
                    print(f"Extreme value detected at step {i}: t={t}, K={K_sim[i]}")
                    # Обрезаем массивы до текущего шага
                    time_steps = time_steps[:i + 1]
                    K_sim = K_sim[:i + 1]
                    Y_sim = Y_sim[:i + 1]
                    break

            # Сохранение результатов
            self.save_simulation_results(time_steps, K_sim, Y_sim)
            return time_steps, K_sim, Y_sim

        except Exception as e:
            print("Simulation failed during execution:")
            traceback.print_exc()
            raise

    def save_simulation_results(self, time_steps, K_sim, Y_sim):
        """Сохраняет результаты симуляции в базу данных"""
        conn = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # Удаление старых результатов
            delete_query = "DELETE FROM simulation_results WHERE simulation_id = %s"
            cursor.execute(delete_query, (self.simulation_id,))
            conn.commit()

            # Подготовка данных для вставки - сохраняем только уникальные целые значения времени
            insert_query = """
            INSERT INTO simulation_results 
            (simulation_id, t, Y_sim, K_sim, L_sim) 
            VALUES (%s, %s, %s, %s, %s)
            """

            # Собираем уникальные целые значения времени
            unique_times = {}
            for i, t in enumerate(time_steps):
                t_int = int(t)
                if t_int not in unique_times:
                    L_t = float(self.param_funcs['L'](t))
                    unique_times[t_int] = (
                        self.simulation_id,
                        t_int,
                        float(Y_sim[i]),
                        float(K_sim[i]),
                        L_t
                    )

            data_to_insert = list(unique_times.values())

            # Пакетная вставка
            cursor.executemany(insert_query, data_to_insert)
            conn.commit()
            print(f"Saved {len(data_to_insert)} unique simulation points to database")

        except Exception as e:
            print(f"Error saving simulation results: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def save_chaos_indicators(self, lyapunov_exp, is_chaotic):
        """Сохраняет индикаторы хаоса в базу данных"""
        conn = None
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()

            # Удаление старых индикаторов
            delete_query = "DELETE FROM chaos_indicators WHERE simulation_id = %s"
            cursor.execute(delete_query, (self.simulation_id,))
            conn.commit()

            # Вставка новых данных
            insert_query = """
            INSERT INTO chaos_indicators 
            (simulation_id, lyapunov_exp, is_chaotic) 
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (
                self.simulation_id,
                float(lyapunov_exp),
                bool(is_chaotic)
            ))
            conn.commit()
            print("Chaos indicators saved successfully")

        except Exception as e:
            print(f"Error saving chaos indicators: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn and conn.is_connected():
                cursor.close()
                conn.close()

    def calculate_lyapunov(self, K_sim, epsilon=1e-4):
        """Вычисляет максимальный показатель Ляпунова"""
        try:
            if len(K_sim) < 2:
                print("Not enough points for Lyapunov calculation")
                return 0.0

            K1 = np.array(K_sim)
            K2 = K1.copy()
            K2[0] += epsilon

            delta_K = np.abs(K2 - K1)
            delta_K[delta_K == 0] = 1e-10
            divergence = np.log(delta_K / epsilon)

            t = np.arange(len(divergence))
            coeffs = np.polyfit(t, divergence, 1)
            return coeffs[0] if not np.isnan(coeffs[0]) else 0.0

        except Exception as e:
            print(f"Error calculating Lyapunov exponent: {str(e)}")
            return 0.0

    def plot_results(self, time_steps, K_sim, Y_sim, save_path=None):
        """Визуализирует результаты симуляции"""
        plt.figure(figsize=(12, 8))

        # График капитала K
        plt.subplot(2, 1, 1)
        plt.plot(time_steps, K_sim, 'b-', linewidth=2)
        if self.time_points:
            plt.plot(self.time_points, self.K_values, 'ro', markersize=6)
        plt.title('Capital (K) Simulation')
        plt.xlabel('Session Index')
        plt.ylabel('K Value')
        plt.grid(True)
        plt.legend(['Simulated', 'Historical'])

        # График выпуска Y
        plt.subplot(2, 1, 2)
        plt.plot(time_steps, Y_sim, 'g-', linewidth=2)
        if self.time_points:
            plt.plot(self.time_points, self.Y_values, 'ro', markersize=6)
        plt.title('Output (Y) Simulation')
        plt.xlabel('Session Index')
        plt.ylabel('Y Value')
        plt.grid(True)
        plt.legend(['Simulated', 'Historical'])

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path)
            print(f"Plot saved to {save_path}")
        else:
            plt.show()

    def run_full_simulation(self, t_end=10, dt=0.1, plot_path=None):
        """Выполняет полный цикл симуляции"""
        try:
            # Проверяем наличие данных
            if not self.time_points:
                print("No historical data available. Aborting simulation.")
                return None, None, None

            last_session = self.time_points[-1]
            print(f"Starting simulation from session {last_session} to {t_end}")

            # Запускаем симуляцию
            time_steps, K_sim, Y_sim = self.simulate(
                t_start=last_session,
                t_end=t_end,
                dt=dt
            )

            # Визуализация
            if plot_path:
                plot_path = f"simulation_{self.simulation_id}.png"
            self.plot_results(time_steps, K_sim, Y_sim, plot_path)

            # Анализ устойчивости
            lyapunov_exp = self.calculate_lyapunov(K_sim)
            is_chaotic = lyapunov_exp > 0.05
            self.save_chaos_indicators(lyapunov_exp, is_chaotic)

            print(f"\n=== SIMULATION COMPLETED ===")
            print(f"Simulation ID: {self.simulation_id}")
            print(f"Player ID: {self.player_id}")
            print(f"Historical sessions: {len(self.time_points)}")
            print(f"Simulated sessions: {len(time_steps)}")
            print(f"Lyapunov exponent: {lyapunov_exp:.6f}")
            print(f"Chaotic regime: {'Yes' if is_chaotic else 'No'}")
            print(f"Results saved to database")
            if plot_path:
                print(f"Plot saved to: {plot_path}")

            return time_steps, K_sim, Y_sim

        except Exception as e:
            print("\n!!! SIMULATION FAILED !!!")
            traceback.print_exc()
            return None, None, None


def main():
    """Основная функция для запуска симуляции"""
    try:
        # ID игрока для симуляции
        player_id = "060b926a-5c47-49d2-babc-5bf42d76c846"

        print("Starting economic model simulator...")
        print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Инициализация симулятора (данные загружаются автоматически)
        simulator = EconomicModelSimulator(
            player_id=player_id,
            A=1.0,
            method='rk4'
        )

        print(f"Simulation ID: {simulator.simulation_id}")
        print(f"Player ID: {player_id}")

        # Проверка наличия данных
        if not simulator.time_points:
            print("Aborting: No historical data loaded for this player")
            return

        # Запуск полной симуляции
        simulator.run_full_simulation(
            t_end=10,  # Прогноз на 10 сессий вперед
            dt=0.1  # Шаг симуляции
        )

    except Exception as e:
        print("\n!!! FATAL ERROR IN MAIN EXECUTION !!!")
        traceback.print_exc()


if __name__ == "__main__":
    main()