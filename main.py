# -*- coding: utf-8 -*-
"""
Main script for the local video generation app.
"""
import os
import openai
import requests
import random
import json
from datetime import datetime
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.VideoClip import ImageClip, VideoClip
from moviepy.audio.io.AudioFileClip import AudioFileClip
import numpy as np
import traceback
from PIL import Image, ImageDraw, ImageFont
import textwrap

# --- Configuración ---
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("DEBUG: .env file loaded.")
except ImportError:
    print("DEBUG: python-dotenv not found, skipping .env load.")

# --- API Key ---
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    print("[CRITICAL ERROR] The OPENAI_API_KEY environment variable is not set.")
    exit()


TEMAS_ANIME = ["Demon Slayer", "Naruto", "One Piece"] # Temas permitidos
FONT_PATH = "fonts/font.ttf" # Ruta a la fuente personalizada

def generar_trivia_anime(tema):
    """
    Genera una pregunta de trivia y su respuesta directa.
    """
    client = openai.OpenAI()

    print(f"[INFO] Generating trivia for new format about {tema}...")
    try:
        system_prompt = """Eres un experto en anime que crea trivias para videos de TikTok. 
Tu objetivo es crear una pregunta interesante y su respuesta directa y concisa.
Responde únicamente con un objeto JSON válido con dos claves: 'pregunta' y 'respuesta'."""
        
        user_prompt = f"Genera una trivia sobre {tema}. Ejemplo: Para One Piece, la pregunta podría ser '¿Cómo se llama el barco de los Piratas del Sombrero de Paja?', y la respuesta 'Thousand Sunny'."

        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        content = response.choices[0].message.content
        trivia_data = json.loads(content)
        print("[SUCCESS] Trivia for new format generated.")
        return trivia_data
    except Exception as e:
        print(f"[ERROR] Could not generate or parse trivia for new format: {e}")
        return None

def obtener_prompt_robusto(tema):
    """
    Genera un prompt detallado y robusto para DALL-E 3 basado en el tema,
    evitando palabras clave que puedan activar filtros de contenido.
    """
    prompts = {
        "Naruto": "Pintura digital épica de un poderoso ninja con cabello rubio y puntiagudo y ojos azules, vestido con un mono naranja y negro. Está en una aldea oculta entre frondosos bosques y montañas, con edificios de estilo tradicional japonés. La escena es dinámica, con efectos de energía arremolinada, sugiriendo una poderosa técnica de chakra. El estilo de arte es vibrante y cinematográfico, reminiscente de animes populares de temática ninja, en formato vertical 9:16. Sin texto ni logos.",
        "One Piece": "Pintura digital vibrante de un pirata alegre con sombrero de paja, navegando en un barco fantástico en alta mar. El mundo es colorido y exagerado, con islas extrañas al fondo. El estilo de arte es juguetón y aventurero, con líneas audaces y composición dinámica, reminiscente de animes populares de temática pirata, en formato vertical 9:16. Sin texto ni logos.",
        "Demon Slayer": "Pintura digital atmosférica de un espadachín con un haori a cuadros, empuñando una katana bajo la luna llena. Se encuentra en un oscuro bosque tradicional japonés, con un ambiente misterioso e inquietante. El estilo de arte es elegante y nítido, con hermosos efectos visuales para las técnicas de espada, reminiscente de animes populares de fantasía y samuráis, en formato vertical 9:16. Sin texto ni logos."
    }
    # Devuelve el prompt específico o uno genérico si el tema no está en el diccionario
    return prompts.get(tema, f"Una escena de anime épica y vibrante inspirada en el universo de {tema}, en formato vertical (9:16) para un fondo de TikTok. El estilo debe ser cinematográfico, colorido y detallado. Importante: la imagen no debe contener letras, texto ni palabras.")

def generar_imagen_fondo(tema):
    """
    Genera una imagen de fondo usando DALL-E 3 y la guarda localmente.
    """
    print(f"[INFO] Generating background image for {tema}...")
    prompt_para_imagen = obtener_prompt_robusto(tema)
    client = openai.OpenAI()
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt_para_imagen,
            size="1024x1792",
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{tema.replace(' ', '_')}_background_{timestamp}.png"
        
        os.makedirs("videos", exist_ok=True)
        image_path = os.path.join("videos", image_filename)
        
        image_response = requests.get(image_url, stream=True)
        image_response.raise_for_status()
        
        with open(image_path, "wb") as f:
            for chunk in image_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"[SUCCESS] Image saved at: {image_path}")
        return image_path
    except Exception as e:
        print(f"[ERROR] Could not generate image: {e}")
        return None

def seleccionar_musica(tema):
    """
    Selecciona una pista de música basada en el tema.
    """
    print(f"[INFO] Selecting music for {tema}...")
    music_folder = "music"
    try:
        archivos_musica = [f for f in os.listdir(music_folder) if os.path.isfile(os.path.join(music_folder, f)) and f.endswith(('.mp3', '.wav'))]
        if not archivos_musica:
            print("[WARNING] No music files found in the /music folder.")
            return None
            
        tema_normalizado = tema.lower().replace(" ", "-")
        musica_tema = [f for f in archivos_musica if tema_normalizado in f.lower()]
        
        if musica_tema:
            pista_seleccionada = random.choice(musica_tema)
            print(f"[SUCCESS] Theme music found: {pista_seleccionada}")
        else:
            print(f"[WARNING] No music found for '{tema}'. Selecting a random track.")
            pista_seleccionada = random.choice(archivos_musica)
            print(f"[SUCCESS] Random music selected: {pista_seleccionada}")
            
        return os.path.join(music_folder, pista_seleccionada)
    except FileNotFoundError:
        print(f"[ERROR] The folder '{music_folder}' was not found.")
        return None

def crear_imagen_texto(texto, fontsize, image_width, output_path, bg_color=None, align='center'):
    """
    Crea una imagen PNG con texto usando Pillow.
    El fondo es transparente por defecto.
    """
    try:
        font = ImageFont.truetype(FONT_PATH, fontsize)
    except IOError:
        print(f"[ERROR] Font not found at {FONT_PATH}. Using default font.")
        font = ImageFont.load_default()

    # Ajustar texto
    # El ancho del texto se calcula para que ocupe 3/4 del ancho del video
    # y el fontsize se ajusta para que quepa en ese ancho.
    # Se usa un factor de 0.75 para el ancho del texto y 0.6 para la relación fontsize/ancho_caracter
    wrapped_text = textwrap.fill(texto, width=int(image_width * 0.75 / (fontsize * 0.6)))

    # Crear imagen
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (0, 0)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font, align=align)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    padding = 25
    img_width = int(image_width * 0.9) # 90% del ancho del video para márgenes
    img_height = text_height + (padding * 2)
    
    img = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if bg_color:
        draw.rounded_rectangle([0, 0, img_width, img_height], radius=15, fill=bg_color)

    # Posición del texto
    text_x = (img_width - text_width) / 2
    text_y = padding

    # Contorno del texto más grueso
    stroke_width = 6
    for x in range(-stroke_width, stroke_width + 1):
        for y in range(-stroke_width, stroke_width + 1):
            if x != 0 or y != 0:
                draw.text((text_x + x, text_y + y), wrapped_text, font=font, fill="black", align=align)

    draw.text((text_x, text_y), wrapped_text, font=font, fill="white", align=align)
    
    img.save(output_path, "PNG")
    return output_path

def crear_temporizador_clip(duration, video_width, video_height, font_size=50, text_color=(255, 255, 255), stroke_color=(0, 0, 0)):
    """
    Crea un clip de video que muestra un temporizador de cuenta regresiva.
    """
    def make_frame(t):
        remaining_time = max(0, int(duration - t))
        timer_text = str(remaining_time)

        # Crear imagen de texto para el temporizador
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            font = ImageFont.load_default()

        # Calcular posición del texto (inferior central)
        bbox = draw.textbbox((0, 0), timer_text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = (video_width - text_width) / 2
        text_y = video_height - text_height - 50 # 50px desde abajo

        # Contorno del texto
        stroke_width = 3
        for x in range(-stroke_width, stroke_width + 1):
            for y in range(-stroke_width, stroke_width + 1):
                if x != 0 or y != 0:
                    draw.text((text_x + x, text_y + y), timer_text, font=font, fill=stroke_color)

        draw.text((text_x, text_y), timer_text, font=font, fill=text_color)
        
        return np.array(img)

    return VideoClip(make_frame, duration=duration).with_fps(1)


def crear_temporizador_clip(duration, video_width, video_height, font_size=50, text_color=(255, 255, 255), stroke_color=(0, 0, 0)):
    """
    Crea un clip de video que muestra un temporizador de cuenta regresiva.
    """
    def make_frame(t):
        remaining_time = max(0, int(duration - t))
        timer_text = str(remaining_time)

        # Crear imagen de texto para el temporizador
        img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype(FONT_PATH, font_size)
        except IOError:
            font = ImageFont.load_default()

        # Calcular posición del texto (inferior central)
        bbox = draw.textbbox((0, 0), timer_text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        text_x = (video_width - text_width) / 2
        text_y = video_height - text_height - 50 # 50px desde abajo

        # Contorno del texto
        stroke_width = 3
        for x in range(-stroke_width, stroke_width + 1):
            for y in range(-stroke_width, stroke_width + 1):
                if x != 0 or y != 0:
                    draw.text((text_x + x, text_y + y), timer_text, font=font, fill=stroke_color)

        draw.text((text_x, text_y), timer_text, font=font, fill=text_color)
        
        return np.array(img)

    return VideoClip(make_frame, duration=duration).with_fps(1)


def crear_barra_progreso(size, duration, bar_color=(255, 165, 0), bg_color=(50, 50, 50, 150)):
    """
    Crea un clip de video de una barra de progreso que se llena.
    """
    bar_width, bar_height = size

    def make_frame(t):
        img = Image.new("RGBA", (bar_width, bar_height), bg_color)
        draw = ImageDraw.Draw(img)
        
        # Dibuja el fondo de la barra (rectángulo redondeado)
        draw.rounded_rectangle([0, 0, bar_width, bar_height], radius=bar_height/2, fill=bg_color)

        # Calcula el ancho de la barra de progreso
        current_width = int(bar_width * (t / duration))
        
        # Dibuja la barra de progreso (rectángulo redondeado)
        if current_width > 0:
            draw.rounded_rectangle([0, 0, current_width, bar_height], radius=bar_height/2, fill=bar_color)
            
        return np.array(img) # Convertir a array de numpy para MoviePy

    return VideoClip(make_frame, duration=duration).with_fps(24)


def crear_video_trivia(tema, trivia_data, imagen_fondo_path, musica_path):
    """
    Crea el video final en el nuevo formato: Pregunta -> Temporizador -> Barra de Progreso -> Respuesta.
    """
    print("[INFO] Assembling the final video in the new format...")
    if not all([imagen_fondo_path, musica_path, FONT_PATH]):
        print("[ERROR] Missing a critical file path.")
        return None

    try:
        duracion_total = 15
        tiempo_pregunta = 11 # Duración de la pregunta y el temporizador
        duracion_barra = tiempo_pregunta # La barra tarda 11 segundos en llenarse
        tiempo_revelacion_respuesta = tiempo_pregunta # La respuesta aparece cuando la barra termina (a los 11 segundos)

        background_clip = ImageClip(imagen_fondo_path).with_duration(duracion_total)
        audio_clip = AudioFileClip(musica_path).with_duration(duracion_total)
        video_width, video_height = background_clip.size

        # --- Crear clips de texto, temporizador y barra ---
        
        # Pregunta
        pregunta_path = crear_imagen_texto(
            trivia_data['pregunta'], 110, video_width, "temp_pregunta.png" # Aumentar fontsize
        )
        pregunta_clip = ImageClip(pregunta_path).with_position(('center', 'center')).with_end(tiempo_pregunta)

        # Temporizador
        temporizador_clip = crear_temporizador_clip(
            duration=tiempo_pregunta, 
            video_width=video_width, 
            video_height=video_height
        ).with_start(0).with_end(tiempo_pregunta)

        # Barra de Progreso (llenándose)
        barra_progreso_llenandose_clip = crear_barra_progreso(
            size=(int(video_width * 0.95), 50), # Ancho 95% del video, alto 50px
            duration=duracion_barra # Se llena en 11 segundos
        ).with_position(('center', video_height - 100)).with_start(0).with_end(tiempo_revelacion_respuesta) # Empieza desde el segundo 0

        # Barra de Progreso (llena y estática)
        barra_progreso_llena_clip = crear_barra_progreso(
            size=(int(video_width * 0.95), 50), 
            duration=duracion_total - tiempo_revelacion_respuesta, 
            bar_color=(255, 165, 0), 
            bg_color=(255, 165, 0) # Fondo también naranja para que se vea llena
        ).with_position(('center', video_height - 100)).with_start(tiempo_revelacion_respuesta)

        # Respuesta (Texto)
        respuesta_txt_path = crear_imagen_texto(
            trivia_data['respuesta'], 110, video_width, "temp_respuesta_texto.png" # Mismo fontsize que pregunta
        )
        respuesta_txt_clip = ImageClip(respuesta_txt_path).with_duration(duracion_total - tiempo_revelacion_respuesta).with_position(('center', 'center')).with_start(tiempo_revelacion_respuesta)

        # --- Composición final ---
        video_final = CompositeVideoClip(
            [background_clip, pregunta_clip, temporizador_clip, barra_progreso_llenandose_clip, barra_progreso_llena_clip, respuesta_txt_clip],
            size=background_clip.size
        ).with_audio(audio_clip)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"{tema.replace(' ', '_')}-{timestamp}.mp4"
        output_path = os.path.join("videos", output_filename)
        
        video_final.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        # Limpiar imágenes temporales
        for temp_file in [pregunta_path, respuesta_txt_path]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

        print(f"\n[SUCCESS] Video generated successfully! -> {output_path}")
        return output_path

    except Exception as e:
        print(f"[ERROR] Detailed error while creating video: {e}")
        traceback.print_exc()
        return None


def main():
    """
    Función principal para ejecutar la generación de video localmente.
    """
    print("Starting anime trivia video generation...")
    
    os.makedirs('videos', exist_ok=True)
    os.makedirs('music', exist_ok=True)
    os.makedirs('fonts', exist_ok=True)

    tema_seleccionado = random.choice(TEMAS_ANIME)
    print(f"[INFO] Theme selected: {tema_seleccionado}")
    
    # 1. Generar datos de trivia (pregunta, respuesta)
    trivia_data = generar_trivia_anime(tema_seleccionado)
    if not trivia_data:
        print("[ERROR] Could not generate trivia. Aborting.")
        return
        
    # 2. Generar imagen de fondo
    ruta_imagen_fondo = generar_imagen_fondo(tema_seleccionado)
    if not ruta_imagen_fondo:
        print("[ERROR] Could not generate background image. Aborting.")
        return

    # 3. Seleccionar música
    ruta_musica = seleccionar_musica(tema_seleccionado)
    if not ruta_musica:
        print("[ERROR] Could not select music. Aborting.")
        return

    # 4. Crear video
    crear_video_trivia(tema_seleccionado, trivia_data, ruta_imagen_fondo, ruta_musica)

if __name__ == "__main__":
    main()