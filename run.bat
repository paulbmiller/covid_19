echo Downloading new data...
@ECHO OFF
curl -LJO https://raw.githubusercontent.com/openZH/covid_19/master/COVID19_Fallzahlen_CH_total.csv
python analysis.py