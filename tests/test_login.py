from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Set up the WebDriver (e.g., Chrome)
driver = webdriver.Chrome()

# Open the login page
driver.get("http://localhost:5000/login")

# Fill the login form
driver.find_element(By.NAME, "Username").send_keys("testuser")
driver.find_element(By.NAME, "Password").send_keys("password")

# Submit the form
driver.find_element(By.NAME, "Password").send_keys(Keys.RETURN)

# Wait for the response and check if login was successful
time.sleep(2)
assert "You Already logged in!" not in driver.page_source  # Checking that it's not already logged in message
assert "Please check your login details and try again." not in driver.page_source  # Checking for incorrect login message

driver.quit()

