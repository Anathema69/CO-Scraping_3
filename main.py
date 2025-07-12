# main.py
import time
from flask import Flask, render_template, request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re

from downloader import paginate_and_download 

# ——————————————————————————————————————————————
# Aquí importas o dejas definidas tus funciones:
# open_browser, expand_section, set_fecha, set_tipo_providencia, etc.


def open_browser():
    options = Options()
    options.add_argument('--start-maximized')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.implicitly_wait(5)
    return driver

def expand_section(driver, fieldset_id, timeout=5):
    """
    Asegura que el fieldset esté expandido (value="false").
    """
    try:
        hidden = driver.find_element(By.ID, f"{fieldset_id}_collapsed")
        if hidden.get_attribute("value") == "true":
            leg = driver.find_element(
                By.CSS_SELECTOR,
                f"#{fieldset_id.replace(':','\\:')} .ui-fieldset-legend"
            )
            leg.click()
            WebDriverWait(driver, timeout).until(
                lambda d: d.find_element(By.ID, f"{fieldset_id}_collapsed").get_attribute("value") == "false"
            )
            print(f"[OK] Expanded {fieldset_id}")
    except Exception as e:
        # Ya estaba abierto o no existe collapsible
        print(f"[WARN] expand_section({fieldset_id}): {e}")

def set_fecha(driver, desde, hasta, retries=3):
    expand_section(driver, "searchForm:set-fecha")
    ini = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "searchForm:fechaIniCal"))
    )
    fin = driver.find_element(By.ID, "searchForm:fechaFinCal")
    for i in range(1, retries+1):
        ini.clear(); ini.send_keys(desde)
        fin.clear(); fin.send_keys(hasta)
        time.sleep(0.5)
        val_ini = ini.get_attribute("value")
        val_fin = fin.get_attribute("value")
        if val_ini == desde and val_fin == hasta:
            print(f"[OK] Fecha = {desde} → {hasta}")
            return
        print(f"[WARN] Fecha no aplicada (intento {i}): ini='{val_ini}', fin='{val_fin}'")
    print(f"[ERROR] No pude fijar la Fecha tras {retries} intentos")



def set_tipo_providencia(driver, opcion_texto, max_retries=3, wait=5):
    """
    Abre el diálogo, selecciona opcion_texto y confirma con Aceptar.
    Sólo pulsa 'Aceptar' cuando detecta que en la columna derecha
    (targetListNew) ya está tu opción. Reintenta hasta max_retries veces.
    """
    for intento in range(1, max_retries+1):
        try:
            print(f"→ Intento {intento} de {max_retries} para '{opcion_texto}'")

            # 1) Asegurarnos de que el fieldset está abierto
            expand_section(driver, "searchForm:set-tipo")

            # 2) Abrir el diálogo
            WebDriverWait(driver, wait).until(
                EC.element_to_be_clickable((By.ID, "searchForm:tipoList"))
            ).click()

            # 3) Esperar a que el diálogo aparezca
            WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((By.ID, "mainForm:dialogListNew"))
            )

            # 4) Clicar la opción en la lista izquierda
            items = WebDriverWait(driver, wait).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "#mainForm\\:optionListNew .ui-selectlistbox-item")
                )
            )
            for li in items:
                if li.text.strip() == opcion_texto:
                    driver.execute_script("arguments[0].scrollIntoView(true);", li)
                    time.sleep(0.2)
                    li.click()
                    break
            else:
                raise RuntimeError(f"No encontré '{opcion_texto}' en la lista izquierda")

            # 5) Esperar a que aparezca en la lista derecha (target)
            WebDriverWait(driver, wait).until(
                EC.text_to_be_present_in_element((
                    By.CSS_SELECTOR,
                    "#mainForm\\:targetListNew .ui-selectlistbox-item"
                ), opcion_texto)
            )

            # 6) Pulsar Aceptar (localizado por el texto del span interno)
            btn_aceptar = WebDriverWait(driver, wait).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[.//span[normalize-space(text())='Aceptar']]"
                ))
            )
            btn_aceptar.click()

            # 7) Esperar a que el diálogo cierre
            WebDriverWait(driver, wait).until(
                EC.invisibility_of_element_located((By.ID, "mainForm:dialogListNew"))
            )

            # 8) Validar que el input quedó con el valor correcto
            inp = WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((By.ID, "searchForm:tipoInput"))
            )
            raw = inp.get_attribute("value")               # ej. '"SENTENCIA" '
            norm = raw.strip().strip('"').strip()          # queda 'SENTENCIA'
            if norm != opcion_texto:
                raise RuntimeError(
                    f"El campo tipoInput quedó como «{raw}» (normalizado: «{norm}»), "
                    f"esperaba «{opcion_texto}»"
                )

            print(f"[OK] Tipo de providencia = «{opcion_texto}» (intento {intento})")
            return

        except Exception as e:
            print(f"[WARN] intento {intento} falló: {e}")
            # Si el diálogo sigue abierto, lo cerramos para el próximo intento
            try:
                close_btn = driver.find_element(
                    By.CSS_SELECTOR, "#mainForm\\:dialogListNew .ui-dialog-titlebar-close"
                )
                close_btn.click()
                WebDriverWait(driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "mainForm:dialogListNew"))
                )
            except:
                pass
            time.sleep(1)

    # Si llegamos aquí, todos los intentos fallaron
    print(f"[ERROR] No pude seleccionar «{opcion_texto}» tras {max_retries} intentos.")

def expand_section(driver, fieldset_id, timeout=5):
    """
    Asegura que el fieldset esté expandido (value="false").
    """
    try:
        hidden = driver.find_element(By.ID, f"{fieldset_id}_collapsed")
        if hidden.get_attribute("value") == "true":
            leg = driver.find_element(
                By.CSS_SELECTOR,
                f"#{fieldset_id.replace(':','\\:')} .ui-fieldset-legend"
            )
            leg.click()
            WebDriverWait(driver, timeout).until(
                lambda d: d.find_element(By.ID, f"{fieldset_id}_collapsed").get_attribute("value") == "false"
            )
            print(f"[OK] Expanded {fieldset_id}")
    except Exception as e:
        # Ya estaba abierto o no existe collapsible
        print(f"[WARN] expand_section({fieldset_id}): {e}")


def set_fecha(driver, desde, hasta, retries=3):
    expand_section(driver, "searchForm:set-fecha")
    ini = WebDriverWait(driver, 5).until(
        EC.visibility_of_element_located((By.ID, "searchForm:fechaIniCal"))
    )
    fin = driver.find_element(By.ID, "searchForm:fechaFinCal")
    for i in range(1, retries+1):
        ini.clear(); ini.send_keys(desde)
        fin.clear(); fin.send_keys(hasta)
        time.sleep(0.5)
        val_ini = ini.get_attribute("value")
        val_fin = fin.get_attribute("value")
        if val_ini == desde and val_fin == hasta:
            print(f"[OK] Fecha = {desde} → {hasta}")
            return
        print(f"[WARN] Fecha no aplicada (intento {i}): ini='{val_ini}', fin='{val_fin}'")
    print(f"[ERROR] No pude fijar la Fecha tras {retries} intentos")

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def set_tipo_providencia(driver, opcion_texto, max_retries=3, wait=13):
    """
    Abre el diálogo, selecciona opcion_texto y confirma con Aceptar.
    Luego valida que el campo contenga esa cadena (no igualdad exacta).
    """
    for intento in range(1, max_retries+1):
        try:
            print(f"→ Intento {intento} de {max_retries} para '{opcion_texto}'")

            # 1) Asegurarnos de que el fieldset está abierto
            expand_section(driver, "searchForm:set-tipo")

            # 2) Abrir el diálogo
            WebDriverWait(driver, wait).until(
                EC.element_to_be_clickable((By.ID, "searchForm:tipoList"))
            ).click()

            # 3) Esperar a que aparezca el diálogo
            WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((By.ID, "mainForm:dialogListNew"))
            )

            # 4) Clicar la opción en la lista izquierda
            items = driver.find_elements(
                By.CSS_SELECTOR, "#mainForm\\:optionListNew .ui-selectlistbox-item"
            )
            for li in items:
                if li.text.strip() == opcion_texto:
                    driver.execute_script("arguments[0].scrollIntoView(true);", li)
                    time.sleep(0.2)
                    li.click()
                    break
            else:
                raise RuntimeError(f"No encontré '{opcion_texto}' en la lista izquierda")

            # 5) Esperar a que aparezca en la lista derecha
            WebDriverWait(driver, wait).until(
                EC.text_to_be_present_in_element(
                    (By.CSS_SELECTOR, "#mainForm\\:targetListNew .ui-selectlistbox-item"),
                    opcion_texto
                )
            )

            # 6) Pulsar Aceptar
            btn = WebDriverWait(driver, wait).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[.//span[normalize-space(text())='Aceptar']]"
                ))
            )
            btn.click()

            # 7) Esperar a que cierre el diálogo
            WebDriverWait(driver, wait).until(
                EC.invisibility_of_element_located((By.ID, "mainForm:dialogListNew"))
            )

            # 8) Validar que el input contenga la opción
            inp = WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((By.ID, "searchForm:tipoInput"))
            )
            raw = inp.get_attribute("value")
            print(f"    [DEBUG] raw tipoInput = {raw!r}")

            # Normalizamos (quitamos comillas y espacios)
            normalized = raw.replace('"','').strip()

            if opcion_texto.lower() not in normalized.lower():
                raise RuntimeError(
                    f"Validación fallida: «{normalized}» no contiene «{opcion_texto}»"
                )

            print(f"[OK] Tipo de providencia = «{opcion_texto}» (intento {intento})")
            return

        except Exception as e:
            print(f"[WARN] intento {intento} falló: {e}")
            # Intentamos cerrar el diálogo si quedó abierto
            try:
                close_btn = driver.find_element(
                    By.CSS_SELECTOR, "#mainForm\\:dialogListNew .ui-dialog-titlebar-close"
                )
                close_btn.click()
                WebDriverWait(driver, 2).until(
                    EC.invisibility_of_element_located((By.ID, "mainForm:dialogListNew"))
                )
            except:
                pass
            time.sleep(1)

    print(f"[ERROR] No pude seleccionar «{opcion_texto}» tras {max_retries} intentos.")

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def set_salas(driver, salas, wait=5):
    """
    Selecciona varias 'salas' en el filtro Sala (multi-check).
    salas: lista de strings exactos a marcar.
    """
    if not salas:
        return

    expand_section(driver, "searchForm:set-sala")

    # Mapeo de los IDs de cada grupo
    grupos = {
        "scivil":   "searchForm:scivil",
        "slaboral": "searchForm:slaboral",
        "spenal":   "searchForm:spenal",
        "splena":   "searchForm:splena",
    }

    for sala in salas:
        encontrada = False
        for clave, menu_id in grupos.items():
            esc = menu_id.replace(":", "\\:")
            trigger = driver.find_element(
                By.CSS_SELECTOR,
                f"#{esc} .ui-selectcheckboxmenu-trigger"
            )
            # 1) Abrir menú
            trigger.click()
            # 2) Esperar panel visible
            panel = WebDriverWait(driver, wait).until(
                EC.visibility_of_element_located((By.ID, f"{menu_id}_panel"))
            )
            # 3) Buscar items dentro del panel
            items = panel.find_elements(By.CSS_SELECTOR, ".ui-selectcheckboxmenu-item")
            for it in items:
                if it.text.strip() == sala:
                    it.click()
                    encontrada = True
                    # NO break del for clave: queremos cerrar y pasar a la próxima sala
                    break
            # 4) Cerrar menú
            trigger.click()
            if encontrada:
                break

        if not encontrada:
            print(f"[WARN] Sala no encontrada para marcar: «{sala}»")
    print(f"[OK] Salas marcadas: {salas}")


def set_ambito(driver, temas, max_retries=3, wait=5):
    """Marca checkboxes de Ámbito Temático con retry interno."""
    if not temas:
        return

    for tema in temas:
        success = False
        for intento in range(1, max_retries+1):
            print(f"  Ámbito «{tema}», intento {intento}/{max_retries}")
            try:
                inp = driver.find_element(
                    By.XPATH,
                    f"//input[@name='searchForm:j_idt154' and @value='{tema}']"
                )
                inp_id = inp.get_attribute("id")
                lbl = driver.find_element(
                    By.XPATH,
                    f"//label[@for='{inp_id}']"
                )
                lbl.click()
                time.sleep(0.2)
                if inp.is_selected():
                    print(f"    [OK] Ámbito «{tema}» marcado")
                    success = True
                    break
                else:
                    print(f"    [WARN] Ámbito no marcado en intento {intento}")
            except Exception as e:
                print(f"    [WARN] Error en intento {intento}: {e}")
            time.sleep(0.5)

        if not success:
            print(f"[ERROR] No pude marcar Ámbito «{tema}» tras {max_retries} intentos")


def set_asunto(driver, asunto, max_retries=3, wait=5):
    """Selecciona el radio de Tipo de Asunto (incluyendo 'TODO')."""
    if asunto is None:
        return

    for intento in range(1, max_retries+1):
        print(f"  Asunto «{asunto}», intento {intento}/{max_retries}")
        try:
            inp = WebDriverWait(driver, wait).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    f"//input[@name='searchForm:tutelaselect' and @value='{asunto}']"
                ))
            )
            inp_id = inp.get_attribute("id")
            lbl = driver.find_element(
                By.XPATH,
                f"//label[@for='{inp_id}']"
            )
            lbl.click()
            time.sleep(0.2)
            if inp.is_selected():
                print(f"    [OK] Asunto «{asunto}» marcado")
                return
            else:
                print(f"    [WARN] No marcado en intento {intento}")
        except Exception as e:
            print(f"    [WARN] Error en intento {intento}: {e}")
        time.sleep(0.5)

    print(f"[ERROR] No pude marcar Asunto «{asunto}» tras {max_retries} intentos")


def set_publicacion(driver, publicacion, max_retries=3, wait=5):
    """Selecciona el radio de Publicación (incluye default '')."""
    # mapeo value→visibleText
    m = {"RELEVANTE":"Relevantes", "PUBLICADA":"Gaceta Judicial", "":"Todas"}
    texto = m.get(publicacion, "Todas")

    for intento in range(1, max_retries+1):
        print(f"  Publicación «{texto}», intento {intento}/{max_retries}")
        try:
            inp = driver.find_element(
                By.XPATH,
                f"//input[@name='searchForm:relevanteselect' and @value='{publicacion}']"
            )
            inp_id = inp.get_attribute("id")
            lbl = driver.find_element(
                By.XPATH,
                f"//label[@for='{inp_id}']"
            )
            lbl.click()
            time.sleep(0.2)
            if inp.is_selected():
                print(f"    [OK] Publicación «{texto}» marcado")
                return
            else:
                print(f"    [WARN] No marcado en intento {intento}")
        except Exception as e:
            print(f"    [WARN] Error en intento {intento}: {e}")
        time.sleep(0.5)

    print(f"[ERROR] No pude marcar Publicación «{texto}» tras {max_retries} intentos")


# ——————————————————————————————————————————————


# ______________________________________________
# funciones para la descargas
def wait_for_results(driver, timeout=30, poll_frequency=0.5):
    """
    Espera hasta que el elemento pagText2 contenga un texto del estilo:
      Resultado: <número> / <total>
    y, opcionalmente, que la tabla de resultados tenga al menos una fila.
    """
    # 1) Esperamos a que el span de pagText2 tenga texto y sea estable
    def pag_loaded(d):
        txt = d.find_element(By.ID, "resultForm:pagText2").text
        # busca algo como "Resultado: 1 /  36842"
        return bool(re.search(r"Resultado\s*:\s*\d+\s*/\s*\d+", txt))

    WebDriverWait(driver, timeout, poll_frequency).until(pag_loaded)
    print(f"[OK] contador de resultados detectado: {driver.find_element(By.ID,'resultForm:pagText2').text}")

    # 2) (Opcional) Esperar a que la tabla tenga al menos 1 fila de datos
    WebDriverWait(driver, timeout, poll_frequency).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "#resultForm\\:jurisTable tbody tr"))
    )
    print("[OK] tabla de resultados poblada con al menos una fila")

app = Flask(__name__)

URL = "https://consultajurisprudencial.ramajudicial.gov.co/WebRelatoria/csj/index.xhtml"

@app.route('/', methods=['GET'])
def index():
    return render_template('filters.html')


@app.route('/search', methods=['POST'])
def search():
    # 1) Capturamos los filtros del formulario
    salas       = request.form.getlist('salas[]')
    ambito      = request.form.getlist('ambito[]')
    asunto      = request.form['asunto']
    publicacion = request.form['publicacion']
    start_date  = request.form['start_date']
    end_date    = request.form['end_date']
    providencia = request.form['providencia']

    # 2) Lanzamos Selenium
    driver = open_browser()
    driver.get(URL)

    # 3) Aplicamos cada filtro en la página externa
    
    set_salas(driver, salas)
    set_ambito(driver, ambito)
    set_asunto(driver, asunto)
    set_publicacion(driver, publicacion)
    set_fecha(driver, start_date, end_date)
    set_tipo_providencia(driver, providencia)

    

    # 4) Pulsamos el botón “Buscar” de la página externa
    boton_buscar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "searchForm:searchButton"))
    )
    boton_buscar.click()

    # 5) esperar a que terminen de cargarse los resultados
    wait_for_results(driver)

    # 6) paginar y descargar
    paginate_and_download(driver, max_pages=5, out_folder="descargas")


    # 7) Dejamos la ventana abierta para que el usuario la vea
    return ("<p>Consulta iniciada en la nueva ventana del navegador.<br>"
            "Cuando termines, puedes cerrar manualmente Selenium.</p>")

if __name__ == '__main__':
    app.run(debug=True)
