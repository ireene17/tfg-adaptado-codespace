import pandas as pd
import time
import random
import os 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TrustpilotScraper:
    def __init__(self, headless=False): #esto esta asi para que aparezca la interfaz de chrome y asi iniciar sesion manualmente en trustpilot y que se escaneen mas de 10pags de reseñas
        self.options = Options()
        
        profile_path = os.path.join(os.getcwd(), "chrome_profile")
        self.options.add_argument(f"user-data-dir={profile_path}")
        
        if headless:
            self.options.add_argument("--headless=new")
            
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = None

    def _configurar_driver(self):
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=self.options)
        
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'})
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _limpiar_input(self, negocio_o_url):
        if "/" in negocio_o_url:
            slug = negocio_o_url.split("/")[-1].split("?")[0]
        else:
            slug = negocio_o_url
        return slug.strip().lower()

    def extraer_reseñas(self, negocio_o_url, max_pages=30):
        slug = self._limpiar_input(negocio_o_url)
        self._configurar_driver() 
        
        data = []
        try:
            print(f"\n Iniciando scraper de {slug}................")
            
            for page in range(1, max_pages + 1):
                url = f"https://es.trustpilot.com/review/{slug}?page={page}"
                self.driver.get(url)
                
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article"))
                    )
                except:
                    print(f"scraper detenido en la pag {page} .")
                    break

                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(random.uniform(0.5, 1.5))
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(0.5, 1))

                reviews = self.driver.find_elements(By.CSS_SELECTOR, "article")
                if not reviews:
                    print(f"No se han encontrado reseñas en la pagina {page}.")
                    break

                for review in reviews:
                    try:
                        selectors = [
                            "p[data-body-typography='true']", 
                            "p[data-service-review-text-typography='true']",
                            "div.styles_reviewCardInner__90_iR p"
                        ]
                        
                        text = ""
                        for s in selectors:
                            try:
                                element = review.find_element(By.CSS_SELECTOR, s)
                                text = element.text.strip()
                                if text: break
                            except:
                                continue
                        
                        if len(text) > 10:
                            data.append(text)
                    except:
                        continue
                
                print(f"*********pagina {page} extraida. Total reseñas: {len(data)}")
                
        finally:
            if self.driver:
                self.driver.quit()
        
        print(f"scraping finalizado... {len(data)} reseñas en total.\n")
        return pd.DataFrame(data, columns=["review"])

def scrape_trustpilot(negocio_o_url):
    scraper = TrustpilotScraper(headless=False) 
    df = scraper.extraer_reseñas(negocio_o_url, max_pages=30)
    return df

def obtener_nombre_limpio(texto):
        nombre = texto.split("/")[-1].split("?")[0]
        if "www." in nombre:
            nombre = nombre.split("www.")[-1]
        nombre = nombre.split(".")[0]
        return nombre.capitalize()
