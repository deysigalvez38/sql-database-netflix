/*Actores más frecuentes por género
Identificamos qué actores dominan cada género dentro del catálogo de Netflix. 
Esto permitió entender patrones de casting y tendencias
*/

WITH genre_actor_pairs AS (
    SELECT 
        g.genre_name,
        a.actor_name,
        COUNT(*) AS appearances
    FROM title_actors ta
    JOIN actors a ON ta.actor_id = a.actor_id
    JOIN title_genres tg ON tg.show_id = ta.show_id
    JOIN genres g ON g.genre_id = tg.genre_id
    GROUP BY g.genre_name, a.actor_name
),
ranked AS (
    SELECT *,
           ROW_NUMBER() OVER (PARTITION BY genre_name ORDER BY appearances DESC) AS rn
    FROM genre_actor_pairs
)
SELECT genre_name, actor_name AS top_actor, appearances
FROM ranked
WHERE rn = 1
ORDER BY appearances DESC;

/*Consulta avanzada: Promedio de duración de películas vs. series por país
“Los países con producciones más largas fueron, 
mientras que otros producen series más cortas.”
*/

SELECT 
    country,
    AVG(CASE WHEN type = 'Movie' THEN CAST(REGEXP_SUBSTR(duration_raw, '[0-9]+') AS UNSIGNED) END) 
        AS avg_movie_minutes,
    AVG(CASE WHEN type = 'TV Show' THEN CAST(REGEXP_SUBSTR(duration_raw, '[0-9]+') AS UNSIGNED) END) 
        AS avg_tvshow_seasons
FROM netflix_titles
WHERE country IS NOT NULL AND country <> ''
GROUP BY country
HAVING COUNT(*) > 5
ORDER BY avg_movie_minutes DESC;

/*Consulta compleja: Relación entre año de lanzamiento y géneros más populares
Detectamos qué géneros dominaron por año — tendencia clave 
para análisis de contenido y predicción.
*/

SELECT 
    release_year,
    g.genre_name,
    COUNT(*) AS total_titles,
    RANK() OVER (PARTITION BY release_year ORDER BY COUNT(*) DESC) AS genre_rank
FROM title_genres tg
JOIN genres g ON tg.genre_id = g.genre_id
JOIN netflix_titles t ON t.show_id = tg.show_id
GROUP BY release_year, g.genre_name
HAVING release_year IS NOT NULL
ORDER BY release_year DESC, total_titles DESC;

/*Directores más versátiles (más géneros diferentes)
Mostramos quiénes son los directores más versátiles, un indicador de creatividad 
y valor para plataformas de streaming.
*/
WITH director_genres AS (
    SELECT 
        director,
        COUNT(DISTINCT g.genre_name) AS genre_count
    FROM netflix_titles t
    JOIN title_genres tg ON tg.show_id = t.show_id
    JOIN genres g ON tg.genre_id = g.genre_id
    WHERE director IS NOT NULL AND director <> ''
    GROUP BY director
)
SELECT director, genre_count
FROM director_genres
ORDER BY genre_count DESC
LIMIT 10;

/*Títulos con el elenco más grande
Identificamos títulos con grandes elencos, útiles para medir complejidad de producción.”
*/

SELECT 
    t.title,
    COUNT(a.actor_id) AS total_actors
FROM netflix_titles t
JOIN title_actors ta ON t.show_id = ta.show_id
JOIN actors a ON ta.actor_id = a.actor_id
GROUP BY t.title
ORDER BY total_actors DESC
LIMIT 10;

/*Países con mayor diversidad de géneros*/

SELECT 
    country,
    COUNT(DISTINCT g.genre_name) AS unique_genres
FROM netflix_titles t
JOIN title_genres tg ON t.show_id = tg.show_id
JOIN genres g ON tg.genre_id = g.genre_id
WHERE country IS NOT NULL AND country <> ''
GROUP BY country
ORDER BY unique_genres DESC;

/*¿Qué tipo de contenido agrega Netflix más rápido?
Las películas/series tardan X años en llegar a la plataforma; 
útil para decisiones de adquisiciones
*/

SELECT show_id, title, date_added, release_year,
       YEAR(date_added) AS year_added,
       (CAST(YEAR(date_added) AS SIGNED) - CAST(release_year AS SIGNED)) AS year_diff
FROM netflix_titles
WHERE date_added IS NULL
   OR release_year IS NULL
   OR (CAST(YEAR(date_added) AS SIGNED) - CAST(release_year AS SIGNED)) < -100
   OR (CAST(YEAR(date_added) AS SIGNED) - CAST(release_year AS SIGNED)) > 200
LIMIT 200;


/*Detectamos actores que suelen trabajar juntos — 
clusters de colaboración, útil para análisis de industria*/

WITH actor_pairs AS (
    SELECT 
        LEAST(a1.actor_name, a2.actor_name) AS actor_1,
        GREATEST(a1.actor_name, a2.actor_name) AS actor_2,
        COUNT(*) AS collaborations
    FROM title_actors ta1
    JOIN title_actors ta2 
         ON ta1.show_id = ta2.show_id AND ta1.actor_id < ta2.actor_id
    JOIN actors a1 ON ta1.actor_id = a1.actor_id
    JOIN actors a2 ON ta2.actor_id = a2.actor_id
    GROUP BY actor_1, actor_2
)
SELECT *
FROM actor_pairs
WHERE collaborations > 1
ORDER BY collaborations DESC;
