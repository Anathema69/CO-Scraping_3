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

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def set_tipo_providencia(driver, opcion_texto, max_retries=3, wait=5):
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



# main.py (fragmento)

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# — tus funciones open_browser, expand_section, set_fecha, set_tipo_providencia … —


def set_salas(driver, salas):
    """
    Selecciona en el filtro 'Sala' todas las opciones de la lista `salas`.
    salas: lista de strings exactos, p.ej. ["SALA PLENA","SALA DE CASACIÓN CIVIL"]
    """
    if not salas:
        return

    expand_section(driver, "searchForm:set-sala")

    groups = ["scivil", "slaboral", "spenal", "splena"]
    for sala in salas:
        encontrada = False
        for grp in groups:
            menu_id = f"searchForm:{grp}"
            # click al trigger para abrir el menú
            try:
                trig = driver.find_element(
                    By.CSS_SELECTOR,
                    f"#{menu_id.replace(':','\\:')} .ui-selectcheckboxmenu-trigger"
                )
                trig.click()
                # esperamos el panel
                panel = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, f"{menu_id}_panel"))
                )
                # dentro del panel, buscamos el item
                items = panel.find_elements(By.CSS_SELECTOR, ".ui-selectcheckboxmenu-item")
                for it in items:
                    if it.text.strip() == sala:
                        it.click()
                        encontrada = True
                        break
                # cerramos el menú
                trig.click()
                if encontrada:
                    break
            except Exception:
                continue

        if not encontrada:
            print(f"[WARN] No encontré la sala «{sala}» en ningún grupo")
    print(f"[OK] Salas seleccionadas: {salas}")


def set_ambito(driver, temas):
    """
    Marca los checkboxes de 'Ámbito Temático' según la lista `temas`.
    temas: lista de strings, p.ej. ["CONSTITUCIONAL","NEGOCIOS_GENERALES"]
    """
    if not temas:
        return

    # Ambito está dentro del mismo fieldset 'set-sala'
    expand_section(driver, "searchForm:set-sala")

    for tema in temas:
        try:
            chk = driver.find_element(
                By.XPATH,
                f"//input[@name='searchForm:j_idt154' and @value='{tema}']"
            )
            if not chk.is_selected():
                chk.click()
        except Exception:
            print(f"[WARN] Ámbito no encontrado: {tema}")

    print(f"[OK] Ámbito temático: {temas}")


def set_asunto(driver, asunto):
    """
    Selecciona el radio button de 'Tipo de Asunto'.
    asunto: uno de "ASUNTOS DE SALA", "TUTELA", "TODO"
    """
    if not asunto or asunto == "TODO":
        return

    expand_section(driver, "searchForm:set-tutela")
    try:
        r = driver.find_element(
            By.XPATH,
            f"//input[@name='searchForm:tutelaselect' and @value='{asunto}']"
        )
        r.click()
        print(f"[OK] Tipo de asunto: {asunto}")
    except Exception as e:
        print(f"[WARN] No pude marcar asunto «{asunto}»: {e}")


def set_publicacion(driver, publicacion):
    """
    Selecciona el radio button de 'Publicación'.
    publicacion: "RELEVANTE", "PUBLICADA", o "" (todas)
    """
    # si es vacío o valor no esperado, dejamos el default ("Todas")
    if not publicacion or publicacion not in ("RELEVANTE","PUBLICADA"):
        return

    expand_section(driver, "searchForm:set-relevante")
    try:
        r = driver.find_element(
            By.XPATH,
            f"//input[@name='searchForm:relevanteselect' and @value='{publicacion}']"
        )
        r.click()
        print(f"[OK] Publicación: {publicacion}")
    except Exception as e:
        print(f"[WARN] No pude marcar publicación «{publicacion}»: {e}")


# ——————————————————————————————————————————————

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
    providencias= request.form.getlist('providencia[]')

    # 2) Lanzamos Selenium
    driver = open_browser()
    driver.get(URL)

    # 3) Aplicamos cada filtro en la página externa
    # Nota: asumo que tendrás que escribir funciones análogas a set_tipo_providencia
    #       para set_salas, set_ambito, set_asunto y set_publicacion.
    set_salas(driver, salas)
    set_ambito(driver, ambito)
    set_asunto(driver, asunto)
    set_publicacion(driver, publicacion)
    set_fecha(driver, start_date, end_date)

    for prov in providencias:
        set_tipo_providencia(driver, prov)

    # 4) Pulsamos el botón “Buscar” de la página externa
    boton_buscar = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "searchForm:searchButton"))
    )
    boton_buscar.click()

    # 5) Dejamos la ventana abierta para que el usuario la vea
    return ("<p>Consulta iniciada en la nueva ventana del navegador.<br>"
            "Cuando termines, puedes cerrar manualmente Selenium.</p>")

if __name__ == '__main__':
    app.run(debug=True)
