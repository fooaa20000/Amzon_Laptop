import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
}

def get_data(pageNo, retries=3, delay=5):
    url = f"https://www.amazon.eg/-/en/s?k=laptop&page={pageNo}&language=en_AE"
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
            soup = BeautifulSoup(response.text, 'lxml')
            break  # If successful, break out of the loop
        except requests.exceptions.RequestException as e:
            print(f"Error fetching page {pageNo} (attempt {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay)  # Wait before retrying
            else:
                return pd.DataFrame(), pd.DataFrame()  # Return empty DataFrames if all retries fail

    devs = []
    views = []
    prices = []
    links = []
    details = []  # List to store details

    for d in soup.find_all('div', attrs={'class': 'sg-col-inner'}): 
        # Extract device name, reviews, price, link, etc.
        dev_name_tag = d.find('h2')
        dev_name = dev_name_tag.text.strip() if dev_name_tag else "N/A"
        view_tag = d.find('span', class_='a-size-base s-underline-text')
        view = view_tag.text.strip() if view_tag else "Unknown"
        link_tag = d.find('a', class_='a-link-normal s-line-clamp-4 s-link-style a-text-normal')
        link = "https://www.amazon.eg" + link_tag['href'] if link_tag and 'href' in link_tag.attrs else "N/A"
        price_tag = d.find('span', class_='a-price-whole')
        price = float(re.sub(r'[^\d.]', '', price_tag.text.strip())) if price_tag else None
        
        if dev_name != "N/A" and link != "N/A":  # Check for valid product and link
            devs.append(dev_name)
            views.append(view)
            prices.append(price)
            links.append(link)
            details.append(det(dev_name, link))  # Extract additional details
            time.sleep(1)  # Avoid too many requests in a short time

    # Create DataFrame for general info
    df = pd.DataFrame({
        "Device Name": devs,
        "Reviews": views,
        "Price (EGP)": prices,
        "Product Link": links
    })

    df = df.drop_duplicates(subset=['Device Name'], keep='first')

    # Combine details with general info
    details_df = pd.concat(details, ignore_index=True) if details else pd.DataFrame()

    return df, details_df

def det(dev, lin):
    try:
        response = requests.get(lin, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
    except Exception as e:
        print(f"Error fetching page {lin}: {e}")
        return pd.DataFrame()

    data = {
        "Device": [dev],
        "Brand": ["Unknown"],
        "Model": ["Unknown"],
        "Screen": ["Unknown"],
        "Color": ["Unknown"],
        "HDD": ["Unknown"],
        "CPU": ["Unknown"],
        "RAM": ["Unknown"],
        "OS": ["Unknown"],
        "Special Features": ["Unknown"],
        "Graphics": ["Unknown"]
    }
    
    specs = {
        "po-brand": "Brand",
        "po-model_name": "Model",
        "po-display.size": "Screen",
        "po-color": "Color",
        "po-hard_disk.size": "HDD",
        "po-cpu_model.family": "CPU",
        "po-ram_memory.installed_size": "RAM",
        "po-operating_system": "OS",
        "po-special_feature": "Special Features",
        "po-graphics_description": "Graphics"
    }

    for key, value in specs.items():
        tag = soup.find('tr', attrs={'class': f'a-spacing-small {key}'})
        if tag:
            td = tag.find('td', attrs={'class': 'a-span9'})
            if td:
                data[value] = [td.text.strip()]

    return pd.DataFrame(data)

# جلب البيانات من الصفحات 1 إلى 10
df_general_all, df_details_all = pd.DataFrame(), pd.DataFrame()

for page in range(1, 11):  # Fetch data from pages 1 to 10
    print(f"Fetching page {page}...")
    df_general, df_details = get_data(page)
    if not df_general.empty and not df_details.empty:
        df_general_all = pd.concat([df_general_all, df_general], ignore_index=True)
        df_details_all = pd.concat([df_details_all, df_details], ignore_index=True)
    else:
        print(f"Skipping page {page} due to errors or empty data.")

# حفظ البيانات في ملف Excel
with pd.ExcelWriter("amazon_laptops.xlsx") as writer:
    df_general_all.to_excel(writer, sheet_name="General Info", index=False)
    df_details_all.to_excel(writer, sheet_name="Details", index=False)

print("Data saved successfully in 'amazon_laptops.xlsx'")
