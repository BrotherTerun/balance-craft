-- Создание таблицы игроков
CREATE TABLE players (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор игрока',
    total_xp INT NOT NULL DEFAULT 0 COMMENT 'Текущие не потраченные очки опыта',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'Дата последнего обновления'
) COMMENT 'Основные данные игроков';

-- Создание таблицы предметов
CREATE TABLE items (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор предмета',
    name VARCHAR(100) NOT NULL COMMENT 'Название предмета',
    price DECIMAL(10,2) NOT NULL COMMENT 'Базовая цена предмета',
    max_durability SMALLINT UNSIGNED COMMENT 'Максимальная прочность (если применимо)',
    gear_score DECIMAL(5,2) NOT NULL COMMENT 'Рейтинг мощности предмета',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи'
) COMMENT 'Статические данные об игровых предметах';

-- Создание таблицы навыков
CREATE TABLE skills (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор навыка',
    name VARCHAR(100) NOT NULL COMMENT 'Название навыка',
    xp_cost MEDIUMINT UNSIGNED NOT NULL COMMENT 'Стоимость обучения в XP',
    skill_score DECIMAL(5,2) NOT NULL COMMENT 'Рейтинг мощности навыка',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи'
) COMMENT 'Данные о навыках игрока';

-- Создание таблицы сессий
CREATE TABLE sessions (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор сессии',
    player_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор игрока',
    session_start DATETIME NOT NULL COMMENT 'Время начала сессии',
    session_end DATETIME COMMENT 'Время окончания сессии',
    avg_apm DECIMAL(5,2) COMMENT 'Среднее количество действий в минуту',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
) COMMENT 'Данные об игровых сессиях';

-- Создание таблицы событий
CREATE TABLE events (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор события',
    session_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор сессии',
    timestamp DATETIME NOT NULL COMMENT 'Временная метка события',
    event_type ENUM(
        'SESSION_START',
        'SESSION_END',
        'GAIN_XP',
        'SPEND_XP',
        'EQUIP_ITEM',
        'UNEQUIP_ITEM',
        'LEARN_SKILL',
        'ACTION'
    ) NOT NULL COMMENT 'Тип события',
    event_data JSON COMMENT 'Данные события в формате JSON',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
) COMMENT 'Игровые события';

-- Создание таблицы экипировки игроков (связь многие-ко-многим)
CREATE TABLE player_equipment (
    player_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор игрока',
    item_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор предмета',
    current_durability SMALLINT UNSIGNED COMMENT 'Текущая прочность',
    equipped BOOLEAN DEFAULT FALSE COMMENT 'Экипирован ли предмет',
    equipped_at DATETIME COMMENT 'Когда экипирован',
    
    PRIMARY KEY (player_id, item_id),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
) COMMENT 'Экипировка игроков';

-- Создание таблицы навыков игроков (связь многие-ко-многим)
CREATE TABLE player_skills (
    player_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор игрока',
    skill_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор навыка',
    learned_at DATETIME NOT NULL COMMENT 'Когда изучен навык',
    skill_level TINYINT UNSIGNED DEFAULT 1 COMMENT 'Уровень навыка',
    
    PRIMARY KEY (player_id, skill_id),
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
) COMMENT 'Навыки игроков';

-- Создание таблицы метрик сессий
CREATE TABLE session_metrics (
    id VARCHAR(36) PRIMARY KEY COMMENT 'Уникальный идентификатор записи',
    session_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор сессии',
    player_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор игрока',
    metric_name ENUM(
        'Y_EXP_VELOCITY',
        'K_POWER_SCORE',
        'L_SESSION_ENGAGEMENT',
        'S_UNSPENT_RESOURCES',
        'D_PROGRESSION_DECAY',
        'A_PROGRESSION_ROI',
        'SPEND_XP_TOTAL'
    ) NOT NULL COMMENT 'Имя метрики',
    metric_value DECIMAL(12,4) NOT NULL COMMENT 'Значение метрики',
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Время расчета',
    
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (player_id) REFERENCES players(id) ON DELETE CASCADE
) COMMENT 'Рассчитанные метрики сессий';

-- Создание таблицы результатов симуляции
CREATE TABLE simulation_results (
    simulation_id VARCHAR(36) NOT NULL COMMENT 'Идентификатор симуляции',
    t MEDIUMINT UNSIGNED NOT NULL COMMENT 'Шаг времени (номер сессии)',
    Y_sim DECIMAL(12,4) NOT NULL COMMENT 'Симулируемое значение выпуска',
    K_sim DECIMAL(12,4) NOT NULL COMMENT 'Симулируемое значение капитала',
    L_sim DECIMAL(12,4) NOT NULL COMMENT 'Симулируемое значение труда',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Дата создания записи',
    
    PRIMARY KEY (simulation_id, t)
) COMMENT 'Результаты симуляции модели';
ALTER TABLE simulation_results 
    MODIFY K_sim DECIMAL(20,4) NOT NULL COMMENT 'Симулируемое значение капитала';
    ALTER TABLE simulation_results 
    MODIFY Y_sim DECIMAL(20,4) NOT NULL COMMENT 'Симулируемое значение выпуска';
    ALTER TABLE simulation_results 
    MODIFY L_sim DECIMAL(20,4) NOT NULL COMMENT 'Симулируемое значение труда';


-- Создание таблицы индикаторов хаоса
CREATE TABLE chaos_indicators (
    simulation_id VARCHAR(36) PRIMARY KEY COMMENT 'Идентификатор симуляции',
    lyapunov_exp DECIMAL(8,6) COMMENT 'Показатель Ляпунова',
    is_chaotic BOOLEAN NOT NULL DEFAULT FALSE COMMENT 'Флаг хаотического режима',
    bifurcation_param VARCHAR(50) COMMENT 'Параметр бифуркации',
    bifurcation_value DECIMAL(10,4) COMMENT 'Значение параметра бифуркации',
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Время расчета',
    
    FOREIGN KEY (simulation_id) REFERENCES simulation_results(simulation_id) ON DELETE CASCADE
) COMMENT 'Индикаторы хаотических режимов';

-- Создание индексов для оптимизации запросов
CREATE INDEX idx_sessions_player ON sessions(player_id);
CREATE INDEX idx_events_session ON events(session_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_metrics_session ON session_metrics(session_id);
CREATE INDEX idx_metrics_player ON session_metrics(player_id);
CREATE INDEX idx_simulation_t ON simulation_results(t);