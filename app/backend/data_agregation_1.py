import mysql.connector
import json
import math
from decimal import Decimal

# Конфигурация подключения к MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256',
    'database': 'monitor_rpg_model'
}


def safe_convert(value, default=0.0):
    """Безопасное преобразование значений в float"""
    if isinstance(value, (Decimal, int)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_previous_session_data(player_id, current_session_start):
    """Получает данные предыдущей сессии для игрока"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT 
            s.session_end,
            sm_power.metric_value AS prev_power_score,
            sm_spend.metric_value AS prev_spend_xp
        FROM sessions s
        LEFT JOIN session_metrics sm_power 
            ON s.id = sm_power.session_id 
            AND sm_power.metric_name = 'K_POWER_SCORE'
        LEFT JOIN session_metrics sm_spend 
            ON s.id = sm_spend.session_id 
            AND sm_spend.metric_name = 'SPEND_XP_TOTAL'
        WHERE s.player_id = %s 
            AND s.session_end < %s
        ORDER BY s.session_end DESC 
        LIMIT 1
        """

        cursor.execute(query, (player_id, current_session_start))
        result = cursor.fetchone()
        return result if result else None

    except Exception as e:
        print(f"Ошибка при получении данных предыдущей сессии: {str(e)}")
        return None
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def calculate_power_score(player_id, total_xp, session_end):
    """Рассчитывает Power Score для игрока на момент окончания сессии"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # Получаем средний gear_score экипированных предметов
        cursor.execute("""
        SELECT AVG(i.gear_score) AS avg_gear_score
        FROM player_equipment pe
        JOIN items i ON pe.item_id = i.id
        WHERE pe.player_id = %s 
            AND pe.equipped = TRUE
            AND pe.equipped_at <= %s
        """, (player_id, session_end))
        gear_result = cursor.fetchone()
        avg_gear_score = safe_convert(gear_result['avg_gear_score']) if gear_result and gear_result[
            'avg_gear_score'] else 0.0

        # Получаем средний skill_score изученных навыков
        cursor.execute("""
        SELECT AVG(s.skill_score) AS avg_skill_score
        FROM player_skills ps
        JOIN skills s ON ps.skill_id = s.id
        WHERE ps.player_id = %s 
            AND ps.learned_at <= %s
        """, (player_id, session_end))
        skill_result = cursor.fetchone()
        avg_skill_score = safe_convert(skill_result['avg_skill_score']) if skill_result and skill_result[
            'avg_skill_score'] else 0.0

        # Рассчитываем Power Score по формуле
        gear_component = avg_gear_score / 100.0
        skill_component = avg_skill_score / 100.0
        power_score = safe_convert(total_xp) * (1 + gear_component + skill_component)

        return power_score

    except Exception as e:
        print(f"Ошибка расчета Power Score: {str(e)}")
        return safe_convert(total_xp)  # Возвращаем базовое значение
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def calculate_session_metrics(session_id):
    """Вычисляет метрики для указанной сессии по новым формулам"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)

        # 1. Получение данных сессии
        cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
        session = cursor.fetchone()

        if not session:
            print(f"Сессия {session_id} не найдена!")
            return

        player_id = session['player_id']
        session_start = session['session_start']
        session_end = session['session_end']

        # 2. Получение данных игрока (начальное состояние)
        cursor.execute("SELECT total_xp FROM players WHERE id = %s", (player_id,))
        player = cursor.fetchone()
        start_total_xp = safe_convert(player['total_xp']) if player else 0.0

        # 3. Получение событий сессии
        cursor.execute("""
        SELECT * FROM events 
        WHERE session_id = %s 
        ORDER BY timestamp
        """, (session_id,))
        events = cursor.fetchall()

        # 4. Парсинг событий
        actions = 0
        xp_gain = 0.0
        xp_spend = 0.0
        equipment_changes = []
        skills_learned = []

        for event in events:
            # Безопасная обработка event_data
            event_data = {}
            if event['event_data']:
                try:
                    if isinstance(event['event_data'], str):
                        event_data = json.loads(event['event_data'])
                    else:
                        event_data = event['event_data']
                except (json.JSONDecodeError, TypeError):
                    event_data = {}

            if event['event_type'] == 'GAIN_XP':
                xp_gain += safe_convert(event_data.get('amount', 0))
            elif event['event_type'] == 'SPEND_XP':
                xp_spend += safe_convert(event_data.get('amount', 0))
            elif event['event_type'] == 'EQUIP_ITEM' and 'item_id' in event_data:
                equipment_changes.append(('equip', event_data['item_id']))
            elif event['event_type'] == 'UNEQUIP_ITEM' and 'item_id' in event_data:
                equipment_changes.append(('unequip', event_data['item_id']))
            elif event['event_type'] == 'LEARN_SKILL' and 'skill_id' in event_data:
                skills_learned.append(event_data['skill_id'])

            actions += 1

        # 5. Обновление total_xp игрока
        end_total_xp = start_total_xp + xp_gain - xp_spend
        cursor.execute("""
        UPDATE players 
        SET total_xp = %s 
        WHERE id = %s
        """, (end_total_xp, player_id))

        # 6. Расчет длительности сессии и APM
        if session_start and session_end:
            duration_seconds = (session_end - session_start).total_seconds()
            duration_minutes = duration_seconds / 60.0
            avg_apm = safe_convert(actions) / duration_minutes if duration_minutes > 0 else 0.0
        else:
            duration_minutes = 0.0
            avg_apm = 0.0

        # Обновление APM в сессии
        cursor.execute("""
        UPDATE sessions 
        SET avg_apm = %s 
        WHERE id = %s
        """, (avg_apm, session_id))

        # 7. Расчет метрик по новым формулам

        # Y: Experience Velocity
        exp_velocity = xp_gain / duration_minutes if duration_minutes > 0 else 0.0

        # K: Power Score (на конец сессии)
        power_score_end = calculate_power_score(player_id, end_total_xp, session_end)

        # L: Session Engagement
        session_engagement = duration_minutes * avg_apm

        # s: Unspent Resources
        unspent_resources = (xp_gain - xp_spend) / xp_gain if xp_gain > 0 else 0.0

        # δ: Progression Decay Rate
        prev_session_data = get_previous_session_data(player_id, session_start)
        prev_spend_xp = safe_convert(prev_session_data['prev_spend_xp']) if prev_session_data and prev_session_data.get(
            'prev_spend_xp') else 0.0

        progression_decay = (prev_spend_xp - xp_spend) / duration_minutes if duration_minutes > 0 else 0.0

        # α: Progression ROI
        progression_roi = 0.0
        if prev_session_data and prev_session_data.get('prev_power_score'):
            prev_power_score = safe_convert(prev_session_data['prev_power_score'])
            power_score_diff = power_score_end - prev_power_score
            spend_xp_diff = xp_spend - prev_spend_xp
            progression_roi = power_score_diff / spend_xp_diff if spend_xp_diff > 0 else 0.0

        # 8. Сохранение всех метрик
        metrics = [
            ('Y_EXP_VELOCITY', exp_velocity),
            ('K_POWER_SCORE', power_score_end),
            ('L_SESSION_ENGAGEMENT', session_engagement),
            ('S_UNSPENT_RESOURCES', unspent_resources),
            ('D_PROGRESSION_DECAY', progression_decay),
            ('A_PROGRESSION_ROI', progression_roi),
            ('SPEND_XP_TOTAL', xp_spend)  # Сохраняем для будущих расчетов
        ]

        for metric_name, metric_value in metrics:
            # Проверка на NaN и Infinity
            if isinstance(metric_value, float) and (math.isnan(metric_value) or math.isinf(metric_value)):
                metric_value = 0.0

            cursor.execute("""
            INSERT INTO session_metrics 
            (id, session_id, player_id, metric_name, metric_value) 
            VALUES (UUID(), %s, %s, %s, %s)
            """, (session_id, player_id, metric_name, metric_value))

        # 9. Обновление экипировки игрока
        for action, item_id in equipment_changes:
            cursor.execute("SELECT id FROM items WHERE id = %s", (item_id,))
            if not cursor.fetchone():
                print(f"Предмет {item_id} не существует, пропускаем")
                continue

            if action == 'equip':
                cursor.execute("""
                INSERT INTO player_equipment 
                (player_id, item_id, equipped, equipped_at) 
                VALUES (%s, %s, TRUE, %s)
                ON DUPLICATE KEY UPDATE equipped = TRUE, equipped_at = %s
                """, (player_id, item_id, session_end, session_end))
            else:
                cursor.execute("""
                UPDATE player_equipment 
                SET equipped = FALSE 
                WHERE player_id = %s AND item_id = %s
                """, (player_id, item_id))

        # 10. Обновление навыков игрока
        for skill_id in skills_learned:
            cursor.execute("SELECT id FROM skills WHERE id = %s", (skill_id,))
            if not cursor.fetchone():
                print(f"Навык {skill_id} не существует, пропускаем")
                continue

            cursor.execute("""
            INSERT INTO player_skills 
            (player_id, skill_id, learned_at) 
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE learned_at = %s
            """, (player_id, skill_id, session_end, session_end))

        conn.commit()
        print(f"Данные для сессии {session_id} успешно агрегированы!")

    except Exception as e:
        print(f"Ошибка агрегации: {str(e)}")
        if conn.is_connected():
            conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


def process_all_sessions():
    """Обрабатывает все сессии без агрегированных данных"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Поиск сессий без метрик
        cursor.execute("""
        SELECT s.id 
        FROM sessions s
        LEFT JOIN session_metrics m ON s.id = m.session_id
        WHERE m.id IS NULL
        """)
        sessions = cursor.fetchall()

        for (session_id,) in sessions:
            print(f"Обработка сессии: {session_id}")
            calculate_session_metrics(session_id)

        print(f"Обработано {len(sessions)} сессий")

    except Exception as e:
        print(f"Ошибка обработки сессий: {str(e)}")
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


if __name__ == "__main__":
    process_all_sessions()