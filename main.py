# main.py (extracto)

import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

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



def main():
    driver = open_browser()
    driver.get("https://consultajurisprudencial.ramajudicial.gov.co/WebRelatoria/csj/index.xhtml")

    set_fecha(driver, "01/01/1990", "01/07/2025")
    set_tipo_providencia(driver, "SENTENCIA")

    
    input("Presiona Enter para cerrar...\n")
    driver.quit()

if __name__ == "__main__":
    main()
