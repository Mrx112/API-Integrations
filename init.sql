-- init.sql
CREATE USER IF NOT EXISTS 'api_user'@'%' IDENTIFIED BY 'api_pass123';
GRANT ALL PRIVILEGES ON api_platform.* TO 'api_user'@'%';
FLUSH PRIVILEGES;