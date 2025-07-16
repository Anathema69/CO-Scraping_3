import os
import re
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DOWNLOAD_URL = (
    "https://consultajurisprudencial.ramajudicial.gov.co"
    "/WebRelatoria/FileReferenceServlet?corp=csj&ext=pdf&file={id}"
)

def extract_ids_from_page(driver):
    """
    Lee todos los <tr data-rk="..."> o el texto 'ID: <número>' de la página actual
    y devuelve una lista de cadenas (los IDs).
    """
    ids = set()
    # método A: usar el atributo data-rk
    filas = driver.find_elements(By.CSS_SELECTOR, "#resultForm\\:jurisTable_data tr")
    for tr in filas:
        rk = tr.get_attribute("data-rk")
        if rk:
            ids.add(rk)
    if ids:
        return list(ids)

    # fallback B: parsear texto
    cells = driver.find_elements(
        By.CSS_SELECTOR,
        "#resultForm\\:jurisTable_data font[color='000000']"
    )
    for f in cells:
        txt = f.text.strip()
        m = re.match(r"(\d{5,})$", txt)
        if m:
            ids.add(m.group(1))
    return list(ids)


def download_pdf(id_, out_folder="pdfs", session=None):
    """
    Descarga el PDF con el ID dado y lo guarda usando el nombre que envía el servidor
    en la cabecera Content-Disposition. Si no la encuentra, usa {id_}.pdf.
    """
    if session is None:
        session = requests.Session()
    url = DOWNLOAD_URL.format(id=id_)
    r = session.get(url, timeout=30)
    r.raise_for_status()

    # tratamos de extraer filename de Content-Disposition
    cd = r.headers.get('Content-Disposition', '')
    filename = None
    if cd:
        # busca filename="algo.pdf"
        m = re.search(r'filename="(?P<name>[^"]+)"', cd)
        if m:
            filename = m.group('name')

    if not filename:
        filename = f"{id_}.pdf"

    os.makedirs(out_folder, exist_ok=True)
    path = os.path.join(out_folder, filename)
    with open(path, "wb") as f:
        f.write(r.content)
    print(f"[DOWNLOADED] {url} → {path}")



def click_next_page(driver, wait=10):
    """
    Hace click en el botón 'rightIcon' para pasar a la siguiente página.
    Devuelve True si encontró y pulsó el botón, o False si no existe.
    """
    try:
        btn = WebDriverWait(driver, wait).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#resultForm\\:j_idt225"))
        )
        btn.click()
        return True
    except Exception:
        return False


def paginate_and_download(driver, max_pages=None, out_folder="pdfs"):
    """
    Recorre las páginas de resultados, descargando todos los PDFs.
    - driver: WebDriver ya con la búsqueda cargada.
    - max_pages: límite de páginas (None = todas).
    - out_folder: carpeta de salida.
    """
    session = requests.Session()
    page = 1
    while True:
        print(f"\n=== Página {page} ===")
        # espera a que la tabla esté lista
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#resultForm\\:jurisTable_data tr"))
        )
        # extrae IDs
        ids = extract_ids_from_page(driver)
        print(f"Encontrados {len(ids)} IDs en página {page}")
        for id_ in ids:
            try:
                download_pdf(id_, out_folder=out_folder, session=session)
            except Exception as e:
                print(f"[ERROR] descargando {id_}: {e}")

        # si hay límite de páginas y lo superamos, salimos
        if max_pages and page >= max_pages:
            print("Alcanzado límite de páginas.")
            break

        # intentamos saltar a la siguiente
        if not click_next_page(driver):
            print("No hay más páginas.")
            break

        # le damos unos segundos para que cargue
        time.sleep(2)
        page += 1
