import qrcode
import pandas as pd
from PIL import Image, ImageDraw
import os

# 1. Conectamos Pandas directamente a la URL viva de Google Sheets
# Reemplaza el string de abajo con el link exacto que copiaste en el Paso 1
url_google_sheets = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTIbA6WikofAFl1F52Ewv2CvFi2YtGOBPpdlaOCc7TqMoArcf3awlQBFDp7Mys1NjBAlN0dkY7yO9ZJ/pub?output=csv"

# Pandas lee la nube directamente
df = pd.read_csv(url_google_sheets)

# ... (El resto del código de la función generar_lote_qrs(df) queda exactamente igual) ...


def generar_lote_qrs(dataframe):
    url_base = "https://tu-usuario.github.io/apertura-digital/"

    for index, fila in dataframe.iterrows():
        id_empleado = str(fila['CODIGO_USUARIO'])
        nombre = fila['NOMBRE']
        area = fila['AREA']

        # Link único para la micro-landing
        link_final = f"{url_base}?oficial={id_empleado}"

        # Generar QR
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(link_final)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="#D32F2F", back_color="white").convert('RGB')

        # Diseño con nombre y código
        ancho, alto = img_qr.size
        lienzo = Image.new('RGB', (ancho, alto + 70), 'white')
        lienzo.paste(img_qr, (0, 0))
        draw = ImageDraw.Draw(lienzo)

        # Texto inferior
        texto = f"{nombre}\nID: {id_empleado} | {area}"
        draw.text((25, alto + 5), texto, fill="black")

        # Carpeta por área (Escalabilidad)
        ruta_area = f"../qrs_generados/{area.replace(' ', '_')}"
        if not os.path.exists(ruta_area):
            os.makedirs(ruta_area)

        lienzo.save(f"{ruta_area}/QR_{id_empleado}.png")


generar_lote_qrs(df)