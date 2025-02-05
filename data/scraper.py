import pandas
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def scrape():

    url = "https://understat.com/league/EPL"
    driver = webdriver.Firefox()
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    
    # Get League Table.
    wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[3]/div[3]/div/div[2]/div/table/tbody")))
    tables = pandas.read_html(driver.page_source)
    leagueData = tables[0]


    # Get Player Data.
    for i in range(1, 53):
        # Change Page, if selector reaches 5 then keep selecting field to go next.
        if i >= 5:
            driver.find_element("xpath", "/html/body/div[1]/div[3]/div[4]/div/div[2]/div[1]/ul/li[5]").click()
        next = driver.find_element("xpath", "/html/body/div[1]/div[3]/div[4]/div/div[2]/div[1]/ul/li["+ str(i) +"]")
        driver.execute_script("argumements[0].click", next)
        
        # Get Table
        wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[3]/div[3]/div/div[2]/div/table/tbody")))
        players = pandas.read_html(driver.page_source)
        playersData = players[1]
        print(playersData)
        i+=1


    driver.close()
    return leagueData

if __name__ == "__main__":
    scrape()
