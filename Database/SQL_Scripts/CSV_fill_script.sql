SHOW GLOBAL VARIABLES LIKE 'local_infile';
SHOW VARIABLES LIKE 'secure_file_priv';
SET GLOBAL local_infile = 1;

LOAD DATA LOCAL INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/players_seed.csv'
INTO TABLE players
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, total_xp, created_at, updated_at);

LOAD DATA LOCAL INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/items_seed.csv'
INTO TABLE items
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, name, price, max_durability, gear_score, created_at);

LOAD DATA LOCAL INFILE 'C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/skills_seed.csv'
INTO TABLE skills
FIELDS TERMINATED BY ',' ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(id, name, xp_cost, skill_score, created_at);