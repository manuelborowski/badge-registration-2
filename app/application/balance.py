from app import data as dl
import sys, requests, base64, pandas as pd, re, inspect

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def balance_get(key, startdate, enddate):
    try:
        locations = dl.settings.get_configuration_setting("location-profiles")
        if key not in locations:
            log.error(f'{inspect.currentframe().f_code.co_name}: {key} is not a valid key')
            return f"{key} is not a valid key", "error.txt"
        else:
            location = locations[key]
        if "school" not in location:
            log.error(f'{inspect.currentframe().f_code.co_name}: {key} has no school parameter')
            return f"{key} has no school parameter", "error.txt"
        else:
            school = location["school"].upper()
        startdate = startdate.split("T")[0]
        enddate = enddate.split("T")[0]
        db_students = dl.models.get_m(dl.student.Student)
        leerlingnummers = [s.leerlingnummer for s in db_students if s.school == school]
        registrations = dl.models.get_m(dl.registration.Registration, [("time_in", ">=", startdate), ("time_in", "<=", f"{enddate}T23:59"), ("location", "=", key)])
        lln2data = {}
        for registation in registrations:
            if registation.leerlingnummer in leerlingnummers:
                if registation.leerlingnummer in lln2data:
                    lln2data[registation.leerlingnummer]["nbr"] += 1
                else:
                    lln2data[registation.leerlingnummer] = {"nbr": 1, "price": registation.prijs_per_item}
        data = [f"{k};{v['nbr']};{v['price']/100}" for k, v in lln2data.items()]
        data_text = "\n".join(data)
        filename = f"{school}-{location['locatie']}-{startdate}-{enddate}.txt"
        return data_text, filename
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return f"error: {str(e)}", "error.txt"

maand2index_nl = ["jan", "feb", "mrt", "apr", "jun", "jul", "aug", "sept", "okt", "nov", "dec"]
maand2index_en = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
papercut_data = {}

def papercut_upload(files):
    try:
        global papercut_data
        papercut_data["data"] = []
        for file in files:
            lines = file.read().decode("iso_8859_1")
            lines = lines.split("\n")

            lines.pop(0) # comment
            date = lines.pop(0)
            #line 1 contains start and end date
            try:
                if "From date" in date:
                    # English format
                    # From date = Sep 1, 2024 12:00:00 AM, To date = Dec 4, 2024 11:59:59 PM"
                    [m, d, y] = list(re.findall(r"From date = (\w+) (\d+), (\d+)", date)[0])
                    m = maand2index_en.index(m) + 1
                    papercut_data["startdate"] = f"{y}{m:02}{int(d):02}"
                    [m, d, y] = list(re.findall(r"To date = (\w+) (\d+), (\d+)", date)[0])
                    m = maand2index_en.index(m) + 1
                    papercut_data["enddate"] = f"{y}{m:02}{int(d):02}"
                else:
                    # Dutch format
                    # Vanaf datum = 16-mrt-2024 0:00:00, Tot datum = 21-jun-2024 23:59:59"
                    [d, m, y] = re.search(r"Vanaf datum = (.*) 0:00:00", date).group(1).split("-")
                    m = maand2index_nl.index(m) + 1
                    papercut_data["startdate"] = f"{y}{m:02}{int(d):02}"
                    [d, m, y] = re.search(r"Tot datum = (.*) 23:59", date).group(1).split("-")
                    m = maand2index_nl.index(m) + 1
                    papercut_data["enddate"] = f"{y}{m:02}{int(d):02}"
            except Exception as e:
                return {"status": False, "data": f"Kan datum info in 2de lijn niet interpreteren:<br>{date}"}

            split_character = "," if "From date" in date else ";"
            header = lines.pop(0) # header
            for total_pages_index, f in enumerate(header.split(split_character)):
                if f == "Totaal aantal afgedrukte Pagina's" or f == "Total Printed Pages":
                    break
            students = dl.models.get_m(dl.student.Student, )
            username2student = {s.username.lower(): s for s in students}
            for line in lines:
                fields = line.split(split_character)
                if fields[0].lower() in username2student:
                    student = username2student[fields[0].lower()]
                    if student.klascode[0] in ["1", "2"]:
                        deelschool = "sum"
                    elif student.instellingsnummer == "30593":
                        deelschool = "sul"
                    else:
                        deelschool = "sui"
                    papercut_data["data"].append({"leerlingnummer": student.leerlingnummer, "deelschool": deelschool, "nbr_pages": fields[total_pages_index]})
                else:
                    log.info(f"Not found, {fields[0].lower()}")
        return {"status": True, "data": "downloaded"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}


def papercut_export(type):
    try:
        global papercut_data
        data = []
        for item in papercut_data["data"]:
            if item["deelschool"] == type:
                data.append(f"{item['leerlingnummer']};{item['nbr_pages']};0.05")
        data_text = "\n".join(data)
        filename = f"{type}-afdrukken-{papercut_data['startdate']}-{papercut_data['enddate']}.txt"
        return data_text, filename
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return f"error: {str(e)}", "error.txt"

