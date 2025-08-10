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
from moviepy.editor import *
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
    Genera una pregunta de trivia de anime usando la API de OpenAI.
    """
    client = openai.OpenAI()

    print(f"[INFO] Generating trivia about {tema}...")
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            response_format={ "type": "json_object" },
            messages=[
                {"role": "system", "content": "Eres un experto en anime que crea preguntas de trivia. Responde únicamente con un objeto JSON válido."},
                {"role": "user", "content": f"Genera una pregunta de trivia sobre {tema} con 4 opciones (A, B, C, D), donde solo una es correcta. Proporciona el resultado en un JSON con las claves 'pregunta', 'opciones' (un diccionario de A, B, C, D) y 'respuesta_correcta' (la letra de la opción correcta)."}
            ]
        )
        content = response.choices[0].message.content
        trivia_data = json.loads(content)
        print("[SUCCESS] Trivia generated.")
        return trivia_data
    except Exception as e:
        print(f"[ERROR] Could not generate or parse trivia: {e}")
        return None

def generar_imagen_fondo(tema):
    """
    Genera una imagen de fondo usando DALL-E 3 y la guarda localmente.
    """
    print(f"[INFO] Generating background image for {tema}...")
    prompt_para_imagen = f"Una escena de anime épica y vibrante del universo de {tema}, en formato vertical (9:16) para un fondo de TikTok. El estilo debe ser cinematográfico, colorido y detallado."
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

def crear_imagen_texto(texto, fontsize, image_width, output_path, bg_color=None):
    """
    Crea una imagen PNG con texto usando Pillow.
    """
    try:
        font = ImageFont.truetype(FONT_PATH, fontsize)
    except IOError:
        print(f"[ERROR] Font not found at {FONT_PATH}. Using default font.")
        font = ImageFont.load_default()

    # Ajustar texto
    wrapped_text = textwrap.fill(texto, width=40)

    # Crear imagen
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (0, 0)))
    bbox = dummy_draw.textbbox((0, 0), wrapped_text, font=font)
    text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

    padding = 10
    img_height = text_height + (padding * 2)
    img = Image.new("RGBA", (image_width, img_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Fondo (si se especifica)
    if bg_color:
        draw.rectangle([0, 0, image_width, img_height], fill=bg_color)

    # Posición del texto
    text_x = (image_width - text_width) / 2
    text_y = padding

    # Contorno del texto
    stroke_width = 2
    for x in range(-stroke_width, stroke_width + 1):
        for y in range(-stroke_width, stroke_width + 1):
            if x != 0 or y != 0:
                draw.text((text_x + x, text_y + y), wrapped_text, font=font, fill="black")

    draw.text((text_x, text_y), wrapped_text, font=font, fill="white")
    
    img.save(output_path, "PNG")
    return output_path

def crear_video_trivia(tema, trivia_data, imagen_path, musica_path):
    """
    Crea el video final ensamblando todos los elementos con MoviePy.
    """
    print("[INFO] Assembling the final video...")
    if not all([imagen_path, musica_path, FONT_PATH]):
        print("[ERROR] Missing a critical file path.")
        return None

    try:
        duracion_total = 15
        tiempo_aparicion_opciones = 1
        tiempo_revelacion_respuesta = 11

        background_clip = ImageClip(imagen_path).set_duration(duracion_total)
        audio_clip = AudioFileClip(musica_path).set_duration(duracion_total)

        video_width = background_clip.w

        # Crear imágenes de texto
        pregunta_path = crear_imagen_texto(trivia_data['pregunta'], 55, video_width, "temp_pregunta.png")
        
        opciones_texto = "\n".join([f"{key}) {val}" for key, val in trivia_data['opciones'].items()])
        opciones_path = crear_imagen_texto(opciones_texto, 45, video_width, "temp_opciones.png")

        respuesta_txt = f"Respuesta: {trivia_data['respuesta_correcta']}) {trivia_data['opciones'][trivia_data['respuesta_correcta']]}"
        respuesta_path = crear_imagen_texto(respuesta_txt, 55, video_width, "temp_respuesta.png", bg_color="#2c8a46")

        # Crear clips de imagen
        pregunta_clip = ImageClip(pregunta_path).set_position(('center', 0.05)).set_duration(duracion_total).crossfadein(0.5).crossfadeout(0.5)
        opciones_clip = ImageClip(opciones_path).set_position(('center', 'center')).set_start(tiempo_aparicion_opciones).set_end(tiempo_revelacion_respuesta).crossfadein(0.5).crossfadeout(0.5)
        respuesta_clip = ImageClip(respuesta_path).set_position(('center', 0.85)).set_start(tiempo_revelacion_respuesta).set_duration(duracion_total - tiempo_revelacion_respuesta).crossfadein(0.5).crossfadeout(0.5)

        # Composición final
        video_final = CompositeVideoClip(
            [background_clip, pregunta_clip, opciones_clip, respuesta_clip],
            size=background_clip.size
        ).set_audio(audio_clip)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_filename = f"{tema.replace(' ', '_')}-{timestamp}.mp4"
        output_path = os.path.join("videos", output_filename)
        
        video_final.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
        
        # Limpiar imágenes temporales
        for temp_file in [pregunta_path, opciones_path, respuesta_path]:
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
    
    trivia_data = generar_trivia_anime(tema_seleccionado)
    if not trivia_data:
        print("[ERROR] Could not generate trivia. Aborting.")
        return
        
    ruta_imagen = generar_imagen_fondo(tema_seleccionado)
    if not ruta_imagen:
        print("[ERROR] Could not generate background image. Aborting.")
        return

    ruta_musica = seleccionar_musica(tema_seleccionado)
    if not ruta_musica:
        print("[ERROR] Could not select music. Aborting.")
        return

    crear_video_trivia(tema_seleccionado, trivia_data, ruta_imagen, ruta_musica)

if __name__ == "__main__":
    main()