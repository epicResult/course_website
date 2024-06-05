from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Set up the WebDriver (e.g., Chrome)
driver = webdriver.Chrome()

# Open the registration page
driver.get("http://localhost:5000/register")

# Fill the registration form
driver.find_element(By.NAME, "Username").send_keys("testuser")
driver.find_element(By.NAME, "First_Name").send_keys("Test")
driver.find_element(By.NAME, "Last_Name").send_keys("User")
driver.find_element(By.NAME, "User_type").send_keys("student")
driver.find_element(By.NAME, "Password").send_keys("password")

# Submit the form
driver.find_element(By.NAME, "Password").send_keys(Keys.RETURN)

# Wait for the response and check if registration was successful
time.sleep(2)
assert "Registration successful! Please login now:" in driver.page_source

driver.quit()

