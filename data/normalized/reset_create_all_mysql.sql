-- reset_create_all_mysql.sql
-- Crea la BD netflix_db y todas las tablas necesarias con relaciones e índices.
-- Incluye tanto `cast` como `cast_list` en netflix_titles para compatibilidad
-- UTF8MB4 / InnoDB por defecto.

DROP DATABASE IF EXISTS `netflix_db`;
CREATE DATABASE `netflix_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `netflix_db`;

SET FOREIGN_KEY_CHECKS = 0;

---------------------------------------------------------------------
-- Tabla principal: netflix_titles
---------------------------------------------------------------------
DROP TABLE IF EXISTS `netflix_titles`;
CREATE TABLE `netflix_titles` (
  `show_id` VARCHAR(128) NOT NULL,
  `type` VARCHAR(50),
  `title` VARCHAR(1000),
  `director` VARCHAR(500),
  `cast` TEXT,        -- columna con nombre "cast" (para compatibilidad)
  `cast_list` TEXT,   -- columna alternativa "cast_list" (recomendada)
  `country` VARCHAR(300),
  `date_added` DATE,
  `release_year` INT,
  `rating` VARCHAR(50),
  `duration_raw` VARCHAR(100),
  `duration_int` INT,
  `duration_unit` VARCHAR(50),
  `description` TEXT,
  PRIMARY KEY (`show_id`),
  KEY `ix_titles_type` (`type`(20)),
  KEY `ix_titles_release_year` (`release_year`),
  FULLTEXT KEY `ft_title_description` (`title`, `description`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- Tabla: genres
---------------------------------------------------------------------
DROP TABLE IF EXISTS `genres`;
CREATE TABLE `genres` (
  `genre_id` INT NOT NULL AUTO_INCREMENT,
  `genre_name` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`genre_id`),
  UNIQUE KEY `ux_genre_name` (`genre_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- Tabla relación: title_genres (N:N)
---------------------------------------------------------------------
DROP TABLE IF EXISTS `title_genres`;
CREATE TABLE `title_genres` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `show_id` VARCHAR(128) NOT NULL,
  `genre_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_tg_show` (`show_id`),
  KEY `ix_tg_genre` (`genre_id`),
  CONSTRAINT `fk_tg_show` FOREIGN KEY (`show_id`) REFERENCES `netflix_titles`(`show_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_tg_genre` FOREIGN KEY (`genre_id`) REFERENCES `genres`(`genre_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- Tabla: actors
---------------------------------------------------------------------
DROP TABLE IF EXISTS `actors`;
CREATE TABLE `actors` (
  `actor_id` INT NOT NULL AUTO_INCREMENT,
  `actor_name` VARCHAR(400) NOT NULL,
  PRIMARY KEY (`actor_id`),
  UNIQUE KEY `ux_actor_name` (`actor_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- Tabla relación: title_actors (N:N)
---------------------------------------------------------------------
DROP TABLE IF EXISTS `title_actors`;
CREATE TABLE `title_actors` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `show_id` VARCHAR(128) NOT NULL,
  `actor_id` INT NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_ta_show` (`show_id`),
  KEY `ix_ta_actor` (`actor_id`),
  CONSTRAINT `fk_ta_show` FOREIGN KEY (`show_id`) REFERENCES `netflix_titles`(`show_id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_ta_actor` FOREIGN KEY (`actor_id`) REFERENCES `actors`(`actor_id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- (Opcional) Tabla staging para cargas masivas (si la quieres)
---------------------------------------------------------------------
DROP TABLE IF EXISTS `staging_netflix_titles`;
CREATE TABLE `staging_netflix_titles` (
  `show_id` VARCHAR(128),
  `raw_json` LONGTEXT,
  `loaded_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

---------------------------------------------------------------------
-- Final
---------------------------------------------------------------------
SET FOREIGN_KEY_CHECKS = 1;
