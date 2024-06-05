from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Set up the WebDriver (e.g., Chrome)
driver = webdriver.Chrome()

# Login first
driver.get("http://localhost:5000/login")
driver.find_element(By.NAME, "Username").send_keys("testuser")
driver.find_element(By.NAME, "Password").send_keys("password")
driver.find_element(By.NAME, "Password").send_keys(Keys.RETURN)

# Wait for login
time.sleep(2)

# Open the add regrade page
driver.get("http://localhost:5000/add_regrade")

# Fill the regrade form
driver.find_element(By.NAME, "assessment_name").send_keys("Test Assessment")
driver.find_element(By.NAME, "description").send_keys("Regrade request description")

# Submit the form
driver.find_element(By.NAME, "description").send_keys(Keys.RETURN)

# Wait for the response and check if regrade was submitted
time.sleep(2)
assert "Regrade submitted!" in driver.page_source

driver.quit()

