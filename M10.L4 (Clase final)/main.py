# IMPORTACIONES
import json
import os
import random

import discord
import numpy as np
import requests

from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS
from keras.models import load_model
from PIL import Image, ImageOps


# CONFIGURACIÓN
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="?", intents=intents)
bot.remove_command("help")
np.set_printoptions(suppress=True)

MODEL = load_model(
    "keras_Model.h5",
    compile=False,
)


# CONSTANTES
ARCHIVO_IDEAS = "ideas.txt"
ARCHIVO_PUNTOS = "puntos.json"

COLOR_ECO = 0x2ECC71

WEATHER_CODES = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    71: "Nevada ligera",
    73: "Nevada moderada",
    75: "Nevada intensa",
    95: "Tormenta",
}


# LISTAS DE DATOS
consejos = [
    "Apaga las luces cuando no las necesites.",
    "Utiliza transporte público o bicicleta.",
    "Reduce el consumo de plásticos.",
    "Recicla papel, vidrio y cartón.",
    "Ahorra agua al ducharte.",
    "Planta árboles en tu comunidad."
]

beneficios = [
    "Mejor calidad del aire.",
    "Reducción del calentamiento global.",
    "Protección de la biodiversidad.",
    "Menos enfermedades respiratorias.",
    "Mayor disponibilidad de agua limpia."
]


# FUNCIONES AUXILIARES

def cargar_puntos():
    """Carga los puntos almacenados de los usuarios"""
    if not os.path.exists(ARCHIVO_PUNTOS):
        return {}
    with open(ARCHIVO_PUNTOS, "r", encoding="utf-8") as archivo:
        return json.load(archivo)


def guardar_puntos(datos):
    """Guarda los puntos de los usuarios en un archivo JSON"""
    with open(ARCHIVO_PUNTOS, "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=4, ensure_ascii=False)


def agregar_puntos(usuario, cantidad):
    """Suma puntos ecológicos a un usuario"""
    datos = cargar_puntos()
    if usuario not in datos:
        datos[usuario] = 0
    datos[usuario] += cantidad
    guardar_puntos(datos)


def get_coordinates(city: str):
    """Obtiene las coordenadas geográficas de una ciudad"""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "es",
    }
    response = requests.get(
        url,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results")
    if not results:
        return None
    city_data = results[0]
    return (
        city_data["latitude"],
        city_data["longitude"],
    )


def get_weather(city: str) -> str:
    """Obtiene el clima actual usando la API Open-Meteo"""
    coordinates = get_coordinates(city)
    if coordinates is None:
        return "No se encontró la ciudad solicitada."
    latitude, longitude = coordinates
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "apparent_temperature,"
            "wind_speed_10m,"
            "surface_pressure,"
            "weather_code"
        ),
        "timezone": "auto",
    }

    response = requests.get(
        url,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    current = data["current"]
    weather = WEATHER_CODES.get(
        current["weather_code"],
        "Estado desconocido"
    )

    return (
        f"Ciudad: {city}\n"
        f"Estado: {weather}\n"
        f"Temperatura: {current['temperature_2m']} °C\n"
        f"Sensación térmica: "
        f"{current['apparent_temperature']} °C\n"
        f"Humedad: "
        f"{current['relative_humidity_2m']}%\n"
        f"Viento: "
        f"{current['wind_speed_10m']} km/h\n"
        f"Presión: "
        f"{current['surface_pressure']} hPa"
    )


def get_nasa_apod():
    """Obtiene la imagen astronómica del día desde la API de la NASA"""
    api_key = os.getenv("NASA_API_KEY")
    url = "https://api.nasa.gov/planetary/apod"
    params = {
        "api_key": api_key,
    }
    response = requests.get(
        url,
        params=params,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def analizar_imagen(ruta_imagen: str):
    """Clasifica una imagen utilizando el modelo de TensorFlow"""

    with open(
        "labels.txt",
        "r",
        encoding="utf-8",
    ) as archivo:
        class_names = archivo.readlines()

    data = np.ndarray(
        shape=(1, 224, 224, 3),
        dtype=np.float32,
    )

    image = Image.open(
        ruta_imagen
    ).convert("RGB")

    size = (224, 224)

    image = ImageOps.fit(
        image,
        size,
        Image.Resampling.LANCZOS,
    )

    image_array = np.asarray(image)

    normalized_image_array = (
        image_array.astype(np.float32) / 127.5
    ) - 1

    data[0] = normalized_image_array
    prediction = MODEL.predict(data)
    index = np.argmax(prediction)
    class_name = class_names[index].strip()

    confidence = float(
        prediction[0][index] * 100
    )

    return class_name, confidence


# EVENTO DEL BOT

@bot.event
async def on_ready():
    """Se ejecuta cuando el bot inicia correctamente"""
    print(f"Eco-Ambiental iniciado correctamente como {bot.user}")


# COMANDOS DEL BOT

@bot.command()
async def clima(ctx, *, ciudad):
    """Muestra información del cambio climático y el clima actual."""

    try:
        informacion = get_weather(ciudad)
    except requests.RequestException:
        await ctx.send(
            "No fue posible obtener la información del clima."
        )
        return

    embed = discord.Embed(
        title="Información Climática",
        description=(
            "Corresponde a los cambios del clima provocados "
            "principalmente por el aumento de gases de efecto "
            "invernadero en la atmósfera.\n\n"
            f"{informacion}"
        ),
        color=COLOR_ECO,
    )

    embed.set_footer(
        text="¡Tus acciones pueden cambiar este rumbo!"
    )

    await ctx.send(embed=embed)


@bot.command()
async def causas(ctx):
    """Muestra las principales causas del impacto ambiental"""
    embed = discord.Embed(
        title="Principales Causas del Impacto Ambiental",
        color=COLOR_ECO
    )
    embed.add_field(
        name="Industrial",
        value="• Emisión masiva de CO2\n• Contaminación industrial",
        inline=False
    )
    embed.add_field(
        name="Energía y Transporte",
        value="• Uso de combustibles fósiles\n• Transporte contaminante",
        inline=False
    )
    embed.add_field(
        name="Naturaleza",
        value="• Deforestación descontrolada",
        inline=False
    )
    await ctx.send(embed=embed)


@bot.command()
async def consejo(ctx):
    """Entrega un consejo ambiental aleatorio"""
    texto = random.choice(consejos)
    embed = discord.Embed(
        title="Consejo Eco-Eficiente",
        description=f"**{texto}**",
        color=COLOR_ECO
    )
    embed.set_footer(text=f"¡{ctx.author.name} tienes +5 puntos ecológicos!")
    await ctx.send(embed=embed)
    agregar_puntos(str(ctx.author), 5)


@bot.command()
async def beneficio(ctx):
    """Muestra un beneficio de cuidar el medio ambiente"""
    texto = random.choice(beneficios)
    embed = discord.Embed(
        title="Beneficio de un Planeta Sostenible",
        description=f"**{texto}**",
        color=COLOR_ECO
    )
    embed.set_footer(text=f"¡{ctx.author.name} tienes +5 puntos ecológicos!")
    await ctx.send(embed=embed)
    agregar_puntos(str(ctx.author), 5)


@bot.command()
async def idea(ctx, *, propuesta):
    """Guarda una propuesta ambiental enviada por el usuario"""
    with open(ARCHIVO_IDEAS, "a", encoding="utf-8") as archivo:
        archivo.write(f"{ctx.author} -> {propuesta}\n")

    agregar_puntos(str(ctx.author), 10)

    embed = discord.Embed(
        title="¡Idea Registrada!",
        description="Tu propuesta ambiental ha sido guardada con éxito.",
        color=COLOR_ECO
    )
    embed.add_field(name="Tu aporte:", value=f"*{propuesta}*")
    embed.set_footer(text="+10 puntos ecológicos otorgados.")
    await ctx.send(embed=embed)


@bot.command()
async def ideas(ctx):
    """Muestra todas las ideas registradas"""
    if not os.path.exists(ARCHIVO_IDEAS):
        await ctx.send("No existen ideas registradas.")
        return

    with open(ARCHIVO_IDEAS, "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    if not contenido.strip():
        contenido = "No existen ideas registradas."

    embed = discord.Embed(
        title="Banco de Ideas Comunitarias",
        description=contenido[:1900],
        color=COLOR_ECO
    )
    await ctx.send(embed=embed)


@bot.command()
async def nasa(ctx):
    """Muestra la imagen astronómica del día obtenida desde la NASA."""
    try:
        data = get_nasa_apod()
    except requests.RequestException:
        await ctx.send(
            "No fue posible obtener la información de la NASA."
        )
        return

    descripcion = data["explanation"]

    if len(descripcion) > 1000:
        descripcion = descripcion[:1000] + "..."

    embed = discord.Embed(
        title=data["title"],
        description=descripcion,
        color=COLOR_ECO,
    )

    embed.add_field(
        name="Fecha",
        value=data["date"],
        inline=False,
    )

    if data["media_type"] == "image":
        embed.set_image(url=data["url"])

    embed.set_footer(
        text="Fuente: NASA - Astronomy Picture of the Day"
    )

    await ctx.send(embed=embed)


@bot.command()
async def puntos(ctx):
    """Consulta los puntos ecológicos del usuario"""
    datos = cargar_puntos()
    usuario = str(ctx.author)

    if usuario not in datos:
        datos[usuario] = 0

    embed = discord.Embed(
        title="Tu Inventario Ecológico",
        description=(
            f"Hola {ctx.author.mention}, actualmente posees "
            f"**{datos[usuario]}** puntos ecológicos."
        ),
        color=COLOR_ECO
    )
    await ctx.send(embed=embed)


@bot.command()
async def ranking(ctx):
    """Muestra el ranking de usuarios con más puntos"""
    datos = cargar_puntos()

    if len(datos) == 0:
        await ctx.send("Todavía no existen participantes.")
        return

    ordenados = sorted(
        datos.items(),
        key=lambda x: x[1],
        reverse=True
    )

    texto = ""
    posicion = 1
    medallas = {1: "🥇", 2: "🥈", 3: "🥉"}

    for usuario, pts_usuario in ordenados:
        medalla = medallas.get(posicion, f"**{posicion}.**")
        texto += f"{medalla} {usuario} — `{pts_usuario} pts`\n"
        posicion += 1
        if posicion > 10:
            break

    embed = discord.Embed(
        title="Ranking Global de Protectores",
        description=texto,
        color=COLOR_ECO
    )
    await ctx.send(embed=embed)


@bot.command()
async def voz(ctx):
    """Genera un consejo ambiental en formato de audio"""
    mensaje = random.choice(consejos)

    tts = gTTS(text=mensaje, lang='es')
    archivo_audio = "consejo.mp3"
    tts.save(archivo_audio)

    embed = discord.Embed(
        title="Audio-Consejo Generado",
        description=f" Escucha la recomendación ambiental:\n\n> *{mensaje}*",
        color=COLOR_ECO
    )
    embed.set_footer(text="+5 puntos ecológicos otorgados.")

    await ctx.send(embed=embed, file=discord.File(archivo_audio))
    if os.path.exists(archivo_audio):
        os.remove(archivo_audio)

    agregar_puntos(str(ctx.author), 5)


@bot.command()
async def analizar(ctx):
    """Analiza una imagen enviada por el usuario mediante IA"""
    if len(ctx.message.attachments) == 0:
        await ctx.send(
            "Debes adjuntar una imagen para analizar."
        )
        return

    imagen = ctx.message.attachments[0]
    ruta = "imagen_usuario.jpg"
    await imagen.save(ruta)
    try:
        clase, confianza = analizar_imagen(ruta)
    except Exception as e:
        print(e)
        await ctx.send(
            "No fue posible analizar la imagen."
        )
        if os.path.exists(ruta):
            os.remove(ruta)
        return

    embed = discord.Embed(
        title="Resultado del análisis",
        color=COLOR_ECO,
    )
    embed.add_field(
        name="Clasificación",
        value=clase,
        inline=False,
    )
    embed.add_field(
        name="Confianza",
        value=f"{confianza:.2f} %",
        inline=False,
    )
    await ctx.send(embed=embed)

    if os.path.exists(ruta):
        os.remove(ruta)


@bot.command(name="help")
async def ayuda(ctx):
    """Muestra todos los comandos disponibles del bot"""
    embed = discord.Embed(
        title="Centro de Ayuda",
        description="Estos son todos los comandos disponibles del bot",
        color=COLOR_ECO
    )

    embed.add_field(
        name="?clima",
        value="Información sobre el cambio climático",
        inline=False
    )

    embed.add_field(
        name="?causas",
        value="Muestra las principales causas del impacto ambiental",
        inline=False
    )

    embed.add_field(
        name="?consejo",
        value="Entrega un consejo ambiental aleatorio (+5 puntos).",
        inline=False
    )

    embed.add_field(
        name="?beneficio",
        value="Muestra un beneficio de cuidar el planeta (+5 puntos)",
        inline=False
    )

    embed.add_field(
        name="?idea <mensaje>",
        value="Guarda una propuesta ambiental (+10 puntos)",
        inline=False
    )

    embed.add_field(
        name="?ideas",
        value="Muestra todas las ideas registradas",
        inline=False
    )

    embed.add_field(
        name="?nasa",
        value="Obtiene la imagen astronómica del día de la NASA",
        inline=False
    )

    embed.add_field(
        name="?puntos",
        value="Consulta tus puntos ecológicos",
        inline=False
    )

    embed.add_field(
        name="?ranking",
        value="Muestra el ranking de usuarios",
        inline=False
    )

    embed.add_field(
        name="?voz",
        value="Genera un consejo ambiental en audio",
        inline=False
    )

    embed.add_field(
        name="?analizar",
        value="Adjunta una imagen para clasificar residuos mediante IA",
        inline=False
    )

    embed.set_footer(
        text="Eco-Ambiental • Bot educativo sobre cambio climático"
    )

    await ctx.send(embed=embed)


# INICIO DEL BOT
if __name__ == "__main__":
    bot.run(TOKEN)
