# Tablet Scraper 1.1.2
It's a web scraping tool which extracts the customer contact details of the shipment report from Tablet website.

## Author: Sk Khurshid Alam

## How to install:
* Make sure python is installed
* Double click on `install.bat` file

## How to run:
*Note: Before running the script, please configure the configuration file: **settings.config***
* Follow the below steps to run the scraper.

## How to run without offset francise code, with visible mode and with VPN on:
* Double click on `run.bat`

## How to run with offset francise code, with invisible mode and with VPN off:
* Open cmd prompt/terminal
* Execute `run.bat -c <FranciseCode> -inviz -vpn_off`

## To know usages:
* Open cmd prompt/terminal
* Execute `run.bat --help`

*Note: Before you procced to **Start?**, you may need to turn on (if the script fails to turn on) the VPN (it's a browser extension) installed in the browser (rendered by this script)*

## Consolidate the customer data:
#### After the data scraping is completed, consoldation of the customer data (unique customer by mobile number) of each francise can be achived using below instruction. 
* Double click on `data_consolidate.bat`

*Note: All the consolidated files would be stored within the **archive > consoldated** folder.*
