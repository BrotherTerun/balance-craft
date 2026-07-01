ALTER TABLE events
MODIFY COLUMN event_type VARCHAR(64) NOT NULL;

ALTER TABLE session_metrics
MODIFY COLUMN metric_name VARCHAR(64) NOT NULL;

SHOW COLUMNS FROM events LIKE 'event_type';
SHOW COLUMNS FROM session_metrics LIKE 'metric_name';