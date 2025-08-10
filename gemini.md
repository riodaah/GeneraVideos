# Proyecto: Generador de Videos de Trivia de Anime para TikTok

## Descripción General
Esta aplicación automatiza la creación de videos cortos de trivia de anime, diseñados para plataformas como TikTok. Utiliza inteligencia artificial para generar el contenido (preguntas, opciones, respuestas e imágenes de fondo) y herramientas de edición de video para ensamblar el producto final con música.

## Componentes Clave

*   **Lenguaje de Programación:** Python
*   **Generación de Contenido (Trivia y Prompts de Imagen):** API de OpenAI (GPT-3.5-Turbo)
*   **Generación de Imágenes de Fondo:** API de OpenAI (DALL-E 3)
*   **Edición y Composición de Video:** MoviePy (basado en FFmpeg)
*   **Manejo de Dependencias:** `requirements.txt`
*   **Contenerización:** Docker
*   **Gestión de Credenciales:** `python-dotenv` (para `.env`)

## Flujo de Trabajo Actual

1.  **Selección de Tema:** La aplicación elige aleatoriamente un tema de anime predefinido (ej. "Naruto", "Demon Slayer", "One Piece").
2.  **Generación de Trivia:** Se llama a la API de GPT-3.5-Turbo para generar una pregunta de trivia, 4 opciones y la respuesta correcta en formato JSON, todo relacionado con el tema seleccionado.
3.  **Generación de Imagen:** Se llama a la API de DALL-E 3 con un prompt basado en el tema para crear una imagen de fondo vertical (9:16) adecuada para TikTok. La imagen se guarda con un nombre único (tema + timestamp).
4.  **Selección de Música:** Se busca una pista de música en la carpeta `music/` que coincida con el tema. Si no se encuentra una específica, se selecciona una al azar.
5.  **Ensamblaje de Video:** MoviePy combina la imagen de fondo, los textos de la trivia (pregunta, opciones, respuesta) con animaciones de aparición/desaparición y la música. Los textos tienen un contorno para mejorar la legibilidad.
6.  **Exportación:** El video final se guarda como un archivo `.mp4` en la carpeta `videos/` con un nombre único (tema + timestamp).

## Mejoras Implementadas Recientemente

*   **Cohesión Temática:** La trivia, imagen y música ahora se generan o seleccionan en base a un tema de anime elegido aleatoriamente.
*   **Manejo de Errores:** Mejoras en el manejo de errores de la API de OpenAI y MoviePy.
*   **Legibilidad del Texto en Video:** Se ajustaron tamaños, posiciones y se añadió un contorno a los textos para una mejor visualización en TikTok.
*   **Almacenamiento de Archivos:** Tanto las imágenes generadas como los videos finales se guardan con nombres únicos (incluyendo marca de tiempo) para evitar sobrescritura.

## Próximos Pasos (Despliegue y Nuevas Funcionalidades)

*   **Despliegue en Google Cloud Run:** Subir la imagen de Docker a Google Artifact Registry y desplegarla como un servicio de Cloud Run para ejecución bajo demanda y costos optimizados.
*   **Integración con Google Drive:** Implementar la subida automática de los videos generados a una carpeta específica de Google Drive.
*   **Gestión de Archivos (Limpieza):** Añadir un parámetro para controlar la eliminación de videos e imágenes antiguas, manteniendo solo las últimas generadas.

## Cómo Ejecutar Localmente (con Docker)

1.  Asegúrate de tener Docker instalado.
2.  Crea un archivo `.env` en la raíz del proyecto con `OPENAI_API_KEY=tu_api_key_aqui`.
3.  Coloca archivos de música (`.mp3` o `.wav`) en la carpeta `music/`. Nómbralos incluyendo el tema (ej. `naruto-theme.mp3`).
4.  Coloca un archivo de fuente `.ttf` en la carpeta `fonts/` y renómbralo a `font.ttf`.
5.  Construye la imagen de Docker:
    ```bash
    docker build -t video-generator .
    ```
6.  Ejecuta el contenedor (asegúrate de que la carpeta `videos` exista en tu máquina):
    ```bash
    docker run --rm --env-file .env -v C:\Users\damor\Desktop\VideosAI\videos:/app/videos video-generator
    ```

