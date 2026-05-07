import traceback
import os

from backend.db_init import initialize_database
from backend.log_import import import_events
from backend.data_agregation_1 import process_all_sessions


def run_pipeline(logs_path):

    try:

        print("\n========== PIPELINE START ==========")

        # ===================================
        # INIT DB
        # ===================================

        print("[PIPELINE] Инициализация БД")

        initialize_database()

        print("[OK] База данных готова")

        # ===================================
        # IMPORT LOGS
        # ===================================

        print("[PIPELINE] Импорт логов")

        events_file = os.path.join(
            logs_path,
            "events.jsonl"
        )

        imported = import_events(events_file)

        print(
            f"[OK] Импортировано событий: {imported}"
        )

        # ===================================
        # AGGREGATION
        # ===================================

        print("[PIPELINE] Агрегация метрик")

        process_all_sessions()

        print("[OK] Агрегация завершена")

        print(
            "\n========== PIPELINE COMPLETE ==========\n"
        )

        return True

    except Exception as e:

        print(
            "\n========== PIPELINE ERROR ==========\n"
        )

        print("Ошибка pipeline:")
        print(e)

        traceback.print_exc()

        print(
            "\n=====================================\n"
        )

        return False