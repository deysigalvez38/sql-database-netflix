# 📊 Netflix Data Engineering & SQL Analytics Project

Este proyecto implementa una solución completa de ingeniería de datos utilizando **MySQL**, **Python (ETL)** y análisis exploratorio para comprender mejor el catálogo de Netflix. Incluye limpieza, normalización, modelado relacional, integración con datos externos (IMDb) y creación de consultas y visualizaciones analíticas.

---

# 🚀 Objetivos del Proyecto

1. **Construir una base de datos relacional** a partir del dataset público *Netflix Titles*.
2. **Normalizar datos clave**, especialmente géneros y reparto (cast).
3. **Integrar una segunda fuente de datos** (IMDb) para enriquecer la información.
4. **Crear consultas SQL** que respondan preguntas analíticas reales.
5. **Generar visualizaciones e insights** desde un Jupyter Notebook.
6. **Diseñar un modelo entidad–relación (ERD)** profesional.
7. **Producir scripts `.sql` completos** reproducibles por cualquier usuario.

---

# 🧱 Estructura del Proyecto

```
project/
│
├── data/
│   └── normalized/
│       ├── netflix_titles_clean.csv
│       ├── genres.csv
│       ├── title_genres.csv
│       ├── actors.csv
│       ├── title_actors_raw.csv
│       ├── title_actors.csv (opcional)
│       ├── imdb_movies_clean.csv
│       ├── netflix_imdb_map.csv
│       ├── inserts.sql
│       ├── inserts_actors.sql
│       └── inserts_imdb.sql
│
├── etl/
│   ├── generate_inserts.py
│   ├── split_actors_minimal.py
│   ├── clean_netflix_data.py
│   └── imdb_matching.py
│
├── sql/
│   ├── reset_create_load_all_mysql.sql
│   ├── create_tables.sql
│   ├── load_data.sql
│   └── queries_analysis.sql
│
├── notebooks/
│   └── netflix_analysis.ipynb
│
└── README.md (este archivo)
```

---

# 🗂️ Descripción de las Tablas

## **1. netflix_titles (tabla principal)**
Contiene toda la información original del catálogo de Netflix.

| Columna | Descripción |
|---------|-------------|
| show_id (PK) | ID del título |
| type | Movie / TV Show |
| title | Título |
| director | Director(es) |
| cast | Lista original de actores |
| country | País de producción |
| date_added | Fecha de ingreso al catálogo |
| release_year | Año de lanzamiento |
| rating | Clasificación por edad |
| duration_raw | Duración original |
| duration_int | Duración numérica |
| duration_unit | Unidad (min, Seasons) |
| description | Sinopsis |

---

## **2. genres**
Catálogo único de géneros.

| Columna | Descripción |
|---------|-------------|
| genre_id (PK) | ID del género |
| genre_name | Nombre del género |

---

## **3. title_genres (tabla puente)**
Relaciona títulos con géneros (relación N:N).

| Columna | Descripción |
|---------|-------------|
| show_id (FK) | Título |
| genre_id (FK) | Género |

---

## **4. actors**
Catálogo único de actores.

| Columna | Descripción |
|---------|-------------|
| actor_id (PK) | ID del actor |
| actor_name | Nombre del actor |

---

## **5. title_actors (tabla puente)**
Relaciona títulos con actores (relación N:N).

| Columna | Descripción |
|---------|-------------|
| show_id (FK) | Título |
| actor_id (FK) | Actor |

---

## **6. imdb_movies**
Datos enriquecidos provenientes de IMDb.

| Columna | Descripción |
|---------|-------------|
| imdb_id (PK) | ID IMDb |
| title | Título IMDb |
| original_title | Título original |
| year | Año |
| imdb_rating | Rating IMDb |
| imdb_votes | Número de votos |
| runtime | Duración (min) |
| genres | Lista IMDb |
| directors | Directores |
| countries | Países |

---

## **7. netflix_imdb_map**
Relación entre títulos de Netflix y su equivalente en IMDb mediante fuzzy matching.

| Columna | Descripción |
|---------|-------------|
| show_id (FK) | Netflix |
| imdb_id (FK) | IMDb |
| match_score | Score de similitud (0–100) |

---

# 🔗 Modelo Entidad–Relación (ERD)

El diagrama completo se encuentra en el archivo:

✔ **`netflix_full_erd.mmd`** (formato Mermaid)

Puedes visualizarlo en:
- https://mermaid.live/
- VSCode con extensión Mermaid Preview

---

# 📥 Scripts SQL Incluidos

## **1. reset_create_load_all_mysql.sql**
Incluye:
- DROP DATABASE
- CREATE DATABASE
- Todas las tablas
- Llaves foráneas y constraints
- LOAD DATA desde CSV

## **2. inserts.sql / inserts_actors.sql / inserts_imdb.sql**
Scripts generados automáticamente por ETL para poblar la base de datos.

---

# 🔄 Flujo ETL

1. **Limpieza inicial** del dataset de Netflix.
2. **Normalización de géneros** → `genres.csv` + `title_genres.csv`.
3. **Extracción del reparto (cast)** → generación de:
   - `actors.csv`
   - `title_actors_raw.csv`
   - `title_actors.csv`
4. **Integración IMDb**:
   - limpieza del dataset IMDb
   - matching con RapidFuzz
   - `netflix_imdb_map.csv`
5. **Generación de scripts SQL** de carga.

---

# 📊 Consultas de Ejemplo

### 1. Top 10 países con más títulos
```sql
SELECT country, COUNT(*) AS total
FROM netflix_titles
GROUP BY country
ORDER BY total DESC
LIMIT 10;
```

### 2. Actores con más apariciones
```sql
SELECT a.actor_name, COUNT(*) AS appearances
FROM title_actors ta
JOIN actors a ON a.actor_id = ta.actor_id
GROUP BY a.actor_name
ORDER BY appearances DESC
LIMIT 10;
```

### 3. Relación Netflix–IMDb (matching alto)
```sql
SELECT nt.title, im.imdb_rating, nm.match_score
FROM netflix_imdb_map nm
JOIN netflix_titles nt ON nt.show_id = nm.show_id
JOIN imdb_movies im ON im.imdb_id = nm.imdb_id
WHERE match_score >= 85
ORDER BY imdb_rating DESC;
```

---

# 📈 Notebook

El cuaderno `notebooks/netflix_analysis.ipynb` incluye:
- Limpieza de datos final
- Estadísticas descriptivas
- Visualizaciones (Matplotlib/Seaborn/Plotly)
- Insights clave

---

# 🧪 Requisitos

- Python 3.10+
- MySQL 8+
- Pandas
- RapidFuzz (para matching)
- Matplotlib / Seaborn / Plotly

---

# 📬 Autor
Proyecto desarrollado por **Deysi Gálvez** como parte del programa Data Analytics en **Ironhack**.

---

# ✔ Licencia
Uso académico y demostrativo. Puedes reutilizar la estructura para otros proyectos de análisis de datos.

