-- reset_and_create_mysql.sql
-- Elimina la base de datos netflix_db si existe y la recrea con esquema limpio.
-- ATENCIÓN: borra todos los datos de netflix_db.

-- 1) Drop DB (si existe) y crear nueva
DROP DATABASE IF EXISTS netflix_db;
CREATE DATABASE netflix_db
  CHARACTER SET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
USE netflix_db;

-- 2) Crear tabla principal: netflix_titles
-- Usamos show_id VARCHAR(32) para que coincida con ids como 'S000001'.
CREATE TABLE netflix_titles (
    show_id VARCHAR(32) NOT NULL PRIMARY KEY,
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

-- 3) Tabla de géneros
CREATE TABLE genres (
    genre_id INT AUTO_INCREMENT PRIMARY KEY,
    genre_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4) Tabla puente title_genres (many-to-many)
CREATE TABLE title_genres (
    show_id VARCHAR(32) NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (show_id, genre_id),
    CONSTRAINT fk_tg_show FOREIGN KEY (show_id) REFERENCES netflix_titles(show_id)
      ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_tg_genre FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
      ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5) Índices recomendados
CREATE INDEX idx_netflix_release_year ON netflix_titles(release_year);
CREATE INDEX idx_netflix_country ON netflix_titles(country);

-- 6) Opcional: tabla auxiliar para directors/actors si más normalización
-- (Descomenta si la quieres)
-- CREATE TABLE directors (
--   director_id INT AUTO_INCREMENT PRIMARY KEY,
--   director_name VARCHAR(255) UNIQUE
-- ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7) Mensaje final (si ejecutas desde cliente MySQL verás OKs)
-- Fin del script
