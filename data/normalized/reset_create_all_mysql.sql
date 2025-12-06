-- sql/reset_create_all_mysql.sql
DROP DATABASE IF EXISTS netflix_db;
CREATE DATABASE netflix_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE netflix_db;

CREATE TABLE IF NOT EXISTS netflix_titles (
  show_id VARCHAR(64) NOT NULL PRIMARY KEY,
  type VARCHAR(50),
  title TEXT,
  director TEXT,
  cast TEXT,
  country VARCHAR(255),
  date_added DATE,
  release_year INT,
  rating VARCHAR(20),
  duration_raw VARCHAR(50),
  duration_int INT,
  duration_unit VARCHAR(20),
  description TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS genres (
  genre_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  genre_name VARCHAR(150) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS title_genres (
  show_id VARCHAR(64) NOT NULL,
  genre_id INT NOT NULL,
  PRIMARY KEY (show_id, genre_id),
  CONSTRAINT fk_tg_show FOREIGN KEY (show_id) REFERENCES netflix_titles(show_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_tg_genre FOREIGN KEY (genre_id) REFERENCES genres(genre_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS actors (
  actor_id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  actor_name VARCHAR(255) NOT NULL,
  UNIQUE KEY ux_actor_name (actor_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS title_actors (
  show_id VARCHAR(64) NOT NULL,
  actor_id INT NOT NULL,
  PRIMARY KEY (show_id, actor_id),
  CONSTRAINT fk_ta_show FOREIGN KEY (show_id) REFERENCES netflix_titles(show_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_ta_actor FOREIGN KEY (actor_id) REFERENCES actors(actor_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS imdb_movies (
  imdb_id VARCHAR(64) NOT NULL PRIMARY KEY,
  title VARCHAR(255),
  original_title VARCHAR(255),
  year INT,
  imdb_rating DECIMAL(3,1),
  imdb_votes INT,
  runtime INT,
  genres TEXT,
  directors TEXT,
  countries TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS netflix_imdb_map (
  show_id VARCHAR(64) NOT NULL,
  imdb_id VARCHAR(64) NOT NULL,
  match_score TINYINT UNSIGNED,
  PRIMARY KEY (show_id, imdb_id),
  CONSTRAINT fk_map_show FOREIGN KEY (show_id) REFERENCES netflix_titles(show_id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_map_imdb FOREIGN KEY (imdb_id) REFERENCES imdb_movies(imdb_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- staging raw tables
CREATE TABLE IF NOT EXISTS title_actors_raw (
  show_id VARCHAR(64),
  actor_name VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS title_genres_raw (
  show_id VARCHAR(64),
  genre_name VARCHAR(150)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- helpful indexes
CREATE INDEX idx_netflix_release_year ON netflix_titles(release_year);
CREATE INDEX idx_netflix_country ON netflix_titles(country);
