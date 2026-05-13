import streamlit as st
import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import os
import unicodedata
import urllib.parse

# Configuración de estética superior
st.set_page_config(page_title="Referidos Banco Amazonas", page_icon="🏦", layout="centered")

# Ocultar elementos nativos de Streamlit para una experiencia de marca limpia
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {padding-top: 2rem;}
    .stButton>button {border-radius: 10px; height: 3.5em; background-color: #D32F2F; color: white; border: none;}
    .stButton>button:hover {background-color: #B71C1C; border: none; color: white;}
    </style>
    """, unsafe_allow_html=True)


def normalizar_texto(texto):
    if not isinstance(texto, str): return texto
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto.strip().upper()


def extraer_dato_flexible(fila, posibles_columnas):
    for col in posibles_columnas:
        col_norm = normalizar_texto(col)
        if col_norm in fila.index:
            valor = str(fila[col_norm])
            if valor.lower() != 'nan' and valor.strip() != '':
                return valor
    return None


def validar_cedula_ecuatoriana(cedula):
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    provincia = int(cedula[0:2])
    if provincia < 1 or provincia > 24:
        return False
    tercer_digito = int(cedula[2])
    if tercer_digito >= 6:
        return False

    suma = 0
    for i in range(9):
        digito = int(cedula[i])
        if i % 2 == 0:  # Posiciones impares
            digito *= 2
            if digito > 9:
                digito -= 9
        suma += digito

    decena_superior = ((suma + 9) // 10) * 10
    verificador_calculado = decena_superior - suma
    if verificador_calculado == 10:
        verificador_calculado = 0

    return verificador_calculado == int(cedula[9])


def generar_tarjeta_banner(data_colaborador, url_qr):
    ancho_card = 1000
    color_fondo = (255, 255, 255)
    color_amazonas = (211, 47, 47)
    color_texto_principal = (30, 30, 30)

    # 1. CARGAMOS EL BANNER
    ruta_assets = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
    banner_expandido = None
    alto_banner = 320

    if os.path.exists(ruta_assets):
        imagenes_banner = [f for f in os.listdir(ruta_assets) if
                           f.lower().endswith(('.png', '.jpg', '.jpeg')) and f.lower() not in ['logo_fondo.png', 'arial.ttf']]
        if imagenes_banner:
            ruta_banner = os.path.join(ruta_assets, imagenes_banner[0])
            banner_orig = Image.open(ruta_banner).convert("RGBA")
            ratio = banner_orig.height / banner_orig.width
            alto_banner = int(ancho_card * ratio)
            banner_expandido = banner_orig.resize((ancho_card, alto_banner), Image.Resampling.LANCZOS)

    # 2. GENERAMOS EL QR
    qr = qrcode.QRCode(version=5, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=15, border=2)
    qr.add_data(url_qr)
    qr.make(fit=True)
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    qr_w, qr_h = img_qr.size

    # 3. CÁLCULO DEL LIENZO
    margen_superior_qr = 70
    margen_inferior_qr = 50
    espacio_textos = 200
    margen_base = 60

    alto_card = alto_banner + margen_superior_qr + qr_h + margen_inferior_qr + espacio_textos + margen_base

    card = Image.new('RGBA', (ancho_card, alto_card), color_fondo)
    draw = ImageDraw.Draw(card)

    if banner_expandido:
        card.paste(banner_expandido, (0, 0), banner_expandido)
    else:
        draw.rectangle([0, 0, ancho_card, alto_banner], fill=color_amazonas)

    # 4. LOGO CENTRAL EN EL QR
    ruta_logo_qr = os.path.join(ruta_assets, 'logo_fondo.png')
    if os.path.exists(ruta_logo_qr):
        logo_img = Image.open(ruta_logo_qr).convert("RGBA")
        size_cuadro = 165
        fondo_blanco = Image.new('RGBA', (size_cuadro, size_cuadro), 'white')

        max_logo_size = size_cuadro - 30
        logo_ratio = logo_img.height / logo_img.width
        logo_w = max_logo_size if logo_img.width > logo_img.height else int(max_logo_size / logo_ratio)
        logo_h = int(max_logo_size * logo_ratio) if logo_img.width > logo_img.height else max_logo_size

        logo_para_qr = logo_img.resize((logo_w, logo_h), Image.Resampling.LANCZOS)
        fondo_blanco.paste(logo_para_qr, ((size_cuadro - logo_w) // 2, (size_cuadro - logo_h) // 2), logo_para_qr)

        pos_centro_exacto = (qr_w - size_cuadro) // 2
        img_qr.paste(fondo_blanco, (pos_centro_exacto, pos_centro_exacto), fondo_blanco)

    # 5. POSICIONAR QR
    pos_qr_y = alto_banner + margen_superior_qr
    pos_qr_x = (ancho_card - qr_w) // 2
    draw.rectangle([pos_qr_x - 3, pos_qr_y - 3, pos_qr_x + qr_w + 3, pos_qr_y + qr_h + 3], outline=(230, 230, 230), width=3)
    card.paste(img_qr, (pos_qr_x, pos_qr_y), img_qr)

    # 6. TEXTOS E INTEGRACIÓN DE FIRMA
    ruta_fuente = os.path.join(ruta_assets, 'arial.ttf')
    try:
        font_nombre = ImageFont.truetype(ruta_fuente, 60)
        font_footer = ImageFont.truetype(ruta_fuente, 35)
        font_firma = ImageFont.truetype(ruta_fuente, 18)
    except IOError:
        font_nombre = font_footer = font_firma = ImageFont.load_default()
        st.warning("⚠️ Sube 'arial.ttf' a la carpeta 'assets' en GitHub para mejorar la tipografía.")
        
    nombre = (data_colaborador['nombre'] or "Colaborador").title()

    def escribir_centrado(y, texto, fuente, color):
        bbox = draw.textbbox((0, 0), texto, font=fuente)
        draw.text(((ancho_card - (bbox[2] - bbox[0])) // 2, y), texto, fill=color, font=fuente)

    base_textos_y = pos_qr_y + qr_h + margen_inferior_qr
    escribir_centrado(base_textos_y, nombre, font_nombre, color_texto_principal)
    escribir_centrado(base_textos_y + 80, f"ID Referido: {data_colaborador['cedula']}", font_footer, (150, 150, 150))
    
    # Marca de agua de Ventura Data Solutions en la imagen
    escribir_centrado(alto_card - 35, "Desarrollado por Jeisson Ventura | Banco Amazonas", font_firma, (200, 200, 200))

    # 7. REDONDEO Y FONDO FINAL
    mask = Image.new('L', (ancho_card, alto_card), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, ancho_card, alto_card), radius=40, fill=255)
    card.putalpha(mask)

    fondo_final = Image.new('RGB', (ancho_card, alto_card), color_fondo)
    fondo_final.paste(card, (0, 0), card)

    return fondo_final


# --- PROCESAMIENTO DE DATOS ---
@st.cache_data(ttl=300)
def cargar_inventario():
    url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTIbA6WikofAFl1F52Ewv2CvFi2YtGOBPpdlaOCc7TqMoArcf3awlQBFDp7Mys1NjBAlN0dkY7yO9ZJ/pub?output=csv"
    df = pd.read_csv(url)
    df.columns = [normalizar_texto(col) for col in df.columns]
    return df


# --- VISTA WEB ---
ruta_assets = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets')
if os.path.exists(ruta_assets):
    imagenes = [f for f in os.listdir(ruta_assets) if
                f.lower().endswith(('.png', '.jpg', '.jpeg')) and f.lower() not in ['logo_fondo.png', 'arial.ttf']]
    if imagenes:
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            st.image(os.path.join(ruta_assets, imagenes[0]), use_container_width=True)

st.markdown("<h2 style='text-align: center;'>Portal de Referidos Digitales</h2>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Genera tu QR personalizado para invitar a clientes a la Neo Cuenta Digital.</p>", unsafe_allow_html=True)
st.write("---")

try:
    data = cargar_inventario()
    col_id = next((c for c in ['IDENTIFICACION', 'CEDULA', 'CODIGO_USUARIO'] if c in data.columns), None)
except:
    st.error("Error al conectar con la base de datos.")
    st.stop()

cedula_user = st.text_input("Ingresa tu número de Cédula:", max_chars=10)

if st.button("Generar Código QR de Referido", use_container_width=True):
    if cedula_user:
        cedula_clean = str(cedula_user).strip().zfill(10)

        # Blindaje matemático de cédula
        if not validar_cedula_ecuatoriana(cedula_clean):
            st.error("❌ La cédula ingresada no es válida. Por favor, revísala.")
        else:
            user_match = data[data[col_id].astype(str).str.strip().str.zfill(10) == cedula_clean]

            if not user_match.empty:
                fila = user_match.iloc[0]
                nombre_full = extraer_dato_flexible(fila, ['NOMBRE', 'NOMBRES', 'NOMBRE APELLIDO', 'NOMBRES Y APELLIDOS'])
                primer_nombre = nombre_full.split()[0] if nombre_full else "Colaborador"

                st.success(f"¡Hola {primer_nombre}! Tu Código QR ha sido generado con éxito.")
                url_referido = f"https://jeisson27vr.github.io/apertura-digital-amazonas/?oficial={cedula_clean}"

                with st.spinner("Diseñando QR de alta resolución..."):
                    img_tarjeta = generar_tarjeta_banner({'nombre': nombre_full, 'cedula': cedula_clean}, url_referido)

                buf = io.BytesIO()
                img_tarjeta.save(buf, format="PNG", quality=95)
                byte_im = buf.getvalue()

                col_img1, col_img2, col_img3 = st.columns([1, 3, 1])
                with col_img2:
                    st.image(byte_im, use_container_width=True)

                c1, c2 = st.columns(2)
                with c1:
                    st.download_button("📥 1. Descargar QR", data=byte_im, file_name=f"Referido_Amazonas_{cedula_clean}.png", mime="image/png", use_container_width=True)
                with c2:
                    # Emojis via códigos Unicode para evitar problemas de encoding
                    check_emoji = chr(9989)
                    celular_emoji = chr(128241)

                    mensaje = (
                        f"¡Hola! Te invito a abrir tu Neo cuenta digital en Banco Amazonas.\n\n"
                        f"{check_emoji} Es rápido, seguro y 100% digital.\n"
                        f"{celular_emoji} Puedes escanear la imagen que te adjunto o empezar directamente desde mi enlace seguro aquí:\n\n"
                        f"{url_referido}"
                    )

                    parametros_url = urllib.parse.urlencode({'text': mensaje})
                    url_whatsapp = f"https://api.whatsapp.com/send?{parametros_url}"

                    st.markdown(
                        f'<a href="{url_whatsapp}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:12px; border-radius:10px; cursor:pointer; font-weight:bold;">📲 2. Enviar Link por WhatsApp</button></a>',
                        unsafe_allow_html=True)
            else:
                st.error("Cédula no encontrada en la base de datos.")
    else:
        st.warning("Por favor, ingresa un número de cédula.")

# Footer Minimalista de Ventura Data Solutions
st.write("---")
st.markdown("<p style='text-align: center; color: #888888; font-size: 12px;'>Diseñado por Jeisson Ventura | Banco Amazonas 🚀</p>", unsafe_allow_html=True)
