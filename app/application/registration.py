import datetime, inspect, base64, requests, io, pandas as pd, json, re
import app.application
from app import app, data as dl, application as al
from app.application.smartschool import send_message as ss_send_message
from flask import make_response
from app.application.sms import send_sms
from app.data.models import get, get_m, commit, update, update_m, add, add_m, delete_m, delete, commit
from app.data.student import Student
from app.data.staff import Staff
from app.data.registration import Registration
from app.data.photo import Photo
from app.data.settings import get_configuration_setting

# logging on file level
import logging
from app import MyLogFilter, top_log_handle

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

# depending on the "to" parameter, return values are sent to:
# ip: only to the client/terminal the registration came from.  Used for alerts, messages, ... due to registering
# location: all the clients/terminals that display/are set to said location
# broadcast: all the clients/terminals
def registration_add(params):
    try:
        location_key = params["location_key"]
        timestamp = params["timestamp"] if "timestamp" in params else None
        leerlingnummer = params["leerlingnummer"] if "leerlingnummer" in params else None
        rfid = params["rfid"] if "rfid" in params else None
        if timestamp:
            now = datetime.datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
        else:
            now = datetime.datetime.now()
        now = now.replace(microsecond=0)
        today = now.date()

        if location_key == "test":
            student = get(Student, [("rfid", "=", rfid)])
            if student:
                log.info(f'{inspect.currentframe().f_code.co_name}: test, {student.leerlingnummer} at {now}')
                return [{
                    "to": "location", 'type': 'update-list-of-registrations',
                    "data": {"status": True, "date": str(today), "action": "add",
                             "data": [{"leerlingnummer": student.leerlingnummer, "naam": student.naam, "voornaam": student.voornaam, "klascode": student.klascode, "timestamp": str(now)}]}}]
            else:
                return {"status": "warning", "msg": f"Badge met code {rfid} niet in database"}

        location_settings = get_configuration_setting("location-profiles")
        if location_key not in location_settings:
            log.info(f'{inspect.currentframe().f_code.co_name}:  {location_key} is not valid')
            return {"status": "warning", "msg": f"Locatie {location_key} is niet geldig"}

        location = location_settings[location_key]
        backoff = location["backoff"] if "backoff" in location else None

        # Staff specific registrations
        if "table" in location and location["table"] == "staff":
            staff = get(Staff, ("rfid", "=", rfid))
            if staff:
                log.info(f'{inspect.currentframe().f_code.co_name}:  Add registration for {staff.code}, {staff.naam} {staff.voornaam} {location_key}')
                if location["type"] == "timeregistration":
                    registrations = get_m(Registration, [("person_id", "=", staff.code), ("location", "=", location_key), ("time_in", ">", today)], order_by="id")
                    last_registration = registrations[-1] if len(registrations) > 0 else None
                    if last_registration and backoff:
                        if (now - (last_registration.time_in if last_registration.time_out == None else last_registration.time_out)).seconds < backoff:
                            return {"status": "warning", "msg": f"Sorry, u moet langer wachten om terug te scannen"}
                    if last_registration and last_registration.time_out is None:
                        text1 = ""
                        weekday = now.weekday()
                        slices = staff.extra.split(",")
                        stop = slices[weekday * 2 + 1] if slices and len(slices) == 10 else None
                        if stop:
                            in_time = last_registration.text1.split(",")[1]
                            [h, m, s] = in_time.split(":")
                            in_delta_time = datetime.timedelta(hours=abs(int(h)), minutes=int(m), seconds=int(s))
                            if in_time[0] == "-":
                                in_delta_time *= -1
                            [ hour, minute ] = stop.split(":")
                            out_delta_time = now - now.replace(hour=int(hour), minute=int(minute))
                            total_delta_time = in_delta_time + out_delta_time
                            text1 = f"{stop},{"-" if out_delta_time.days < 0 else ""}{str(abs(out_delta_time))},{"-" if total_delta_time.days < 0 else ""}{str(abs(total_delta_time))}"
                        registration = update(Registration, last_registration, {"time_out": now, "text1": last_registration.text1 + "," + text1})
                        log.info(f'{inspect.currentframe().f_code.co_name}: Badge out, {staff.code} at {now}')
                        al.socketio.send_to_room({"type": "add-registration", "data": staff.to_dict() | registration.to_dict()}, location_key)
                        return {"status": "ok", "msg": f"{staff.naam} {staff.voornaam} heeft UIT gescand om {registration.time_out}", "data": staff.to_dict() | registration.to_dict()}
                    else:
                        text1 = ""
                        weekday = now.weekday()
                        slices = staff.extra.split(",")
                        start = slices[weekday * 2] if slices and len(slices) == 10 else None
                        if start:
                            [ hour, minute ] = start.split(":")
                            delta_time = now.replace(hour=int(hour), minute=int(minute)) - now
                            text1 = f"{start},{"-" if delta_time.days < 0 else ""}{str(abs(delta_time))}"
                        registration = add(Registration, {"person_id": staff.code, "location": location_key, "time_in": now, "text1": text1})  # copy extra to text1
                        if registration:
                            log.info(f'{inspect.currentframe().f_code.co_name}: Badge in, {staff.code} at {now}')
                            al.socketio.send_to_room({"type": "add-registration", "data": staff.to_dict() | registration.to_dict()}, location_key)
                            return {"status": "ok", "msg": f"{staff.naam} {staff.voornaam} heeft IN gescand om {registration.time_in}", "data": staff.to_dict() | registration.to_dict()}
            log.info(f'{inspect.currentframe().f_code.co_name}: rfid {rfid} not found in table: staff')
            return {"status": "warning", "msg": f"Kan personeelslid met rfid {rfid} niet vinden in database"}

        # student specific registrations
        if rfid:
            student = get(Student, [("rfid", "=", rfid)])
        elif leerlingnummer:
            student = get(Student, [("leerlingnummer", "=", leerlingnummer)])
        else:
            return {"status": "warning", "msg": "Geen RFID of leerlingnummer gevonden"}
        if student:
            photo_obj = get(Photo, ("id", "=", student.foto_id))
            photo = base64.b64encode(photo_obj.photo).decode('utf-8') if photo_obj else ''
            if location["type"] == "verkoop":
                artikel = get_configuration_setting("artikel-profiles")[location["artikel"]]
                nbr_items = 1
                if "dagmasker" in location:
                    mask = getattr(student, location["dagmasker"])
                    if mask == "":
                        log.info(f'{inspect.currentframe().f_code.co_name}:  {student.leerlingnummer}, cannot have this artikel')
                        return {"status": "warning", "msg": f"Student {student.naam} {student.voornaam} is niet ingeschreven voor dit artikel"}
                    day_index = datetime.datetime.now().weekday()
                    if day_index > 4:
                        return [{"to": "ip", 'type': 'alert-popup', "data": f"Dit kan alleen gescand worden tijdens weekdagen"}]
                    max_qty = int(mask[day_index])
                    current_qty = int(mask[day_index + 6])
                    if current_qty >= max_qty:
                        log.info(f'{inspect.currentframe().f_code.co_name}:  {student.leerlingnummer}, dagmasker, exceeded quantity {current_qty}/{max_qty} ')
                        return {"status": "warning", "msg": f"Student {student.naam} {student.voornaam} heeft het maximum aantal van {max_qty} artikel(s) bereikt"}
                    current_qty += 1
                    mask = mask[:day_index + 6] + str(current_qty) + mask[day_index + 7:]
                    update(Student, student, {location["dagmasker"]: mask})
                registration = add(Registration, {"person_id": student.leerlingnummer, "location": location_key, "time_in": now, "prijs_per_item": artikel["prijs-per-item"], "aantal_items": nbr_items})
            # When a student is too late in, scan its badge.  An sms is sent to the parents and a why-too-late reason needs to be added
            # If the student returns with a valid proof of being late, tick the registration as being acknowledged/finished
            # text1: remark
            # flag1: sms is sent
            # flag2: remark is acknowledged

            # When a student needs to hand in its cellphone or needs to go to the toilet during lesson time, its badge is scanned.
            # Depending on the number of times, a rule is invoked to color the scan and/or send smartschool messages
            # aantal_items: store the sequence-counter
            # flag1: message sent
            elif location["type"] in ["cellphone", "toilet", "sms"]:
                if student.school not in location["school"]:
                    return {"status": "warning", "msg": f"Student {student.naam} {student.voornaam} zit in een andere school, {student.school}"}
                last_registration = get(Registration, [("person_id", "=", student.leerlingnummer), ("location", "=", location_key)], order_by="-id")
                if last_registration:
                    sequence_counter = last_registration.aantal_items + 1
                else:
                    sequence_counter = 1
                registration = add(Registration, {"person_id": student.leerlingnummer, "location": location_key, "time_in": now, "aantal_items": sequence_counter})
            else:
                return {"status": "warning", "msg": f"Locatie ({location_key}) niet gekend"}
            if registration:
                log.info(f'{inspect.currentframe().f_code.co_name}: {registration}')
                al.socketio.send_to_room({"type": "add-registration", "data": student.to_dict() | registration.to_dict() | {"photo": photo}},  location_key)
                return {"status": "ok", "msg": f"student {student.naam} {student.voornaam} heeft gescand om {registration.time_in}"}

            log.info(f'{inspect.currentframe().f_code.co_name}:  {student.leerlingnummer} could not make a registration')
            return {"status": "warning", "msg": "Kan geen nieuwe registratie maken"}
        log.info(f'{inspect.currentframe().f_code.co_name}:  rif/leerlingnummer {rfid}/{leerlingnummer} not found in database')
        return {"status": "warning", "msg": f"Kan student met rfid {rfid} / leerlingnummer {leerlingnummer} niet vinden in database"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Foutmelding: {e}"}

# delete a single registration.  Check for later registrations (same person and location) and if applicable (sms, cellphone, ...) adjust the "aantal_items" counter to make sure they reflect the correct status.
def registration_delete(id):
    try:
        registration = get(Registration, ("id", "=", id))
        if registration:
            later_registrations = get_m(Registration, [("time_in", ">", registration.time_in), ("location", "=", registration.location), ("person_id", "=", registration.person_id)])
            for later_registration in later_registrations:
               if later_registration.aantal_items > 1:
                   later_registration.aantal_items -= 1
            commit()
            delete(Registration, id)
            return {"status": "ok", "msg": f"Registratie verwijderd", "data": {"status": True}}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Fout, {str(e)}"}

def registration_zero_counters(location, date):
    try:
        date = f"{date} 23:59" # consider the end of the day, else the <= below does not work properly
        registrations = get_m(Registration, [("location", "=", location), ("time_in", "<=", date)])
        for registration in registrations:
            registration.active = False
        registrations = get_m(Registration, [("location", "=", location), ("time_in", ">", date)])
        aantal_items_cache = {}
        for registration in registrations:
            if registration.person_id in aantal_items_cache:
                registration.aantal_items -= aantal_items_cache[registration.person_id]
            else:
                aantal_items_cache[registration.person_id] = registration.aantal_items - 1
                registration.aantal_items = 1
        commit()
        ret = {"status": "ok", "msg": "tellers zijn op nul gezet"}
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Fout, {str(e)}"}

# filters priority (high to low)
# search
# sms/cellphone specific
# period

def registration_get(location_key=None, view_layout=None, period=None):
    try:
        locations = get_configuration_setting("location-profiles")
        location = locations[location_key]
        ret = []
        time_low = time_high = None
        flag1 = flag2 = None
        if period in ["last-2-months", "last-4-months", "last-week"]:
            delta = 60 if period == "last-2-months" else 120 if period == "last-4-months" else 7
            time_low = datetime.datetime.now() - datetime.timedelta(days=delta)
        if "table" in location and location["table"] == "staff":
            # Staff specific data
            registrations = dl.registration.registration_staff_get(location_key, time_low=time_low, time_high=time_high)
            for tuple in registrations:
                item = tuple[1].to_dict() | tuple[0].to_dict()
                ret.append(item)
        else:
            # Student specific data
            include_foto = view_layout == "tile"
            registrations = dl.registration.registration_student_photo_get(location_key, time_low=time_low, time_high=time_high, flag1=flag1, flag2=flag2, include_foto=include_foto)
            for tuple in registrations:
                item = tuple[1].to_dict() | tuple[0].to_dict()
                if include_foto:
                    item.update({"photo": base64.b64encode(tuple[2].photo).decode('utf-8') if tuple[2] and tuple[2].photo else ''})
                ret.append(item)
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {'status': False, 'message': str(e)}

def clear_all_registrations(location):
    try:
        now = datetime.datetime.now()
        today = now.replace(hour=0, minute=0, second=0)
        registrations = get_m(Registration, [("location", "=", location), ("time_in", ">", today), ("time_out", "=", None)], order_by="id")
        clear_registrations = [{"item": r, "time_out": now} for r in registrations]
        update_m(Registration, clear_registrations)
        return True
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return False

def get_balance(location_key, startdate, enddate):
    try:
        locations = get_configuration_setting("location-profiles")
        if location_key not in locations:
            log.error(f'{inspect.currentframe().f_code.co_name}: {location_key} is not a valid key')
            return f"{location_key} is not a valid key", "error.txt"
        else:
            location = locations[location_key]
        if "school" not in location:
            log.error(f'{inspect.currentframe().f_code.co_name}: {location} has no school parameter')
            return f"{location} has no school parameter", "error.txt"
        else:
            school = location["school"]
        startdate = startdate.split("T")[0]
        enddate = enddate.split("T")[0]
        db_students = dl.models.get_m(Student)
        leerlingnummers = [s.leerlingnummer for s in db_students if s.school == school]
        registrations =  dl.models.get_m(Registration, [("time_in", ">=", startdate), ("time_in", "<=", f"{enddate}T23:59"), ("location", "=", location_key)])
        lln2data = {}
        for registation in registrations:
            if registation.person_id in leerlingnummers:
                if registation.person_id in lln2data:
                    lln2data[registation.person_id]["nbr"] += 1
                else:
                    lln2data[registation.person_id] = {"nbr": 1, "price": registation.prijs_per_item}
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
                return {"status": "warning", "msg": f"Kan datum info in 2de lijn niet interpreteren:<br>{date}"}

            split_character = "," if "From date" in date else ";"
            header = lines.pop(0) # header
            for total_pages_index, f in enumerate(header.split(split_character)):
                if f == "Totaal aantal afgedrukte Pagina's" or f == "Total Printed Pages":
                    break
            students = dl.models.get_m(Student)
            username2student = {s.username.lower(): s for s in students}
            for line in lines:
                fields = line.split(split_character)
                if fields[0].lower() in username2student:
                    student = username2student[fields[0].lower()]
                    papercut_data["data"].append({"leerlingnummer": student.leerlingnummer, "deelschool": student.school, "nbr_pages": fields[total_pages_index]})
                else:
                    log.info(f"Not found, {fields[0].lower()}")
        return {"status": "ok", "msg": "Download gedaan", "data": {"status": True}}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Fout, {str(e)}"}

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

def api_schoolrekening_get(options):
    try:
        _, filters, _, _ = app.application.models.process_options(options)
        artikel = [v for k, o, v in filters if k == "artikel"][0]
        filters = [(k, o, v) for k, o, v in filters if k != "artikel"]
        locations = get_configuration_setting("location-profiles")
        artikel_profiel = get_configuration_setting("artikel-profiles")[artikel]
        location_keys = [k for k, v in locations.items() if v["type"] == "verkoop" and v["artikel"] == artikel]
        data_out = []
        leerlingnummers = {}
        for key in location_keys:
            filters.append(("location", "=", key))
            registrations = get_m(Registration, filters)
            for item in registrations:
                if item.leerlingnummer in leerlingnummers:
                    leerlingnummers[item.leerlingnummer] += 1
                else:
                    leerlingnummers[item.leerlingnummer] = 1
            filters = filters[:-1]
        info = artikel_profiel["info"]
        prijs_per_item = artikel_profiel["prijs-per-item"]
        for leerlingnummer, nbr in leerlingnummers.items():
            data_out.append({"leerlingnummer": leerlingnummer, "info": info.replace("$aantal$", str(nbr)), "bedrag": prijs_per_item * nbr / 100})
        return {"status": True, "data": data_out}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

def api_registration_update(location_key, ids, fields):
    try:
        location_settings = get_configuration_setting("location-profiles")
        if location_key not in location_settings:
            log.info(f'{inspect.currentframe().f_code.co_name}:  {location_key} is not valid')
            return {"status": False, "data": f"Locatie {location_key} is niet geldig"}
        location = location_settings[location_key]
        data = []
        for id in ids:
            registration = get(Registration, ("id", "=", id))
            new_fields = {}
            item = {}
            if location["type"] == "sms":
                if "remark" in fields:
                    new_fields["text1"] = fields["remark"]
                    item["remark"] = fields["remark"]
                if "remark_ack" in fields:
                    new_fields["flag1"] = fields["remark_ack"]
                    item["remark_ack"] = fields["remark_ack"]
                if item:
                    item["id"] = id
                    data.append(item)
                update(Registration, registration, new_fields)
            else:
                update(Registration, registration, fields)
        return {"status": True, "data": data}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

def registration_send_message(ids):
    try:
        location_settings = get_configuration_setting("location-profiles")
        data = []
        for id in ids:
            registration = get(Registration, ("id", "=", id))
            location = location_settings[registration.location]
            student = get(Student, [("leerlingnummer", "=", registration.person_id)])
            if student:
                if location["type"] == "sms":
                    data.append({"id": id, "sms_sent": __send_sms(registration, location, student)})
                elif location["type"] == "cellphone":
                    if __send_ss_message(registration, location, student):
                        al.socketio.send_to_room({"type": "update-registration", "data": {"id": registration.id, "data": "flag1", "value": True} }, registration.location)
            else:
                log.error(f'{inspect.currentframe().f_code.co_name}: could not find student fore registration {id}')
        return {"status": "ok", "msg": "Berichten verstuurd"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": str(e)}

def api_registration_delete(ids):
    try:
        ret = registration_delete(ids)
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

def api_schoolrekening_artikels_get():
    try:
        artikels = get_configuration_setting("artikel-profiles")
        return {"status": True, "data": [k for k, _ in artikels.items()]}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

def api_schoolrekening_info():
    info_page = get_configuration_setting("api-schoolrekening-info")
    return info_page

# sync registrations from remote (client) into local (server-database).
def sync_registrations_server(data):
    try:
        nbr_doubles = 0
        new_registrations = []
        if data:
            registrations = []
            for d in data:
                try:
                    r0 = datetime.datetime.strptime(d[0], "%Y-%m-%d %H:%M:%S")
                except:
                    r0 = None
                try:
                    r1 = datetime.datetime.strptime(d[1], "%Y-%m-%d %H:%M:%S")
                except:
                    r1 = None
                registrations.append([r0, r1, d[2], d[3]])
            registrations = sorted(registrations, key=lambda x: x[0])
            oldest = registrations[0]
            log.info(f"Oldest, {oldest}")
            db_registrations = get_m(Registration, [("time_in", ">=", oldest[0])])
            db_cache = {str(d.time_in) + d.leerlingnummer + d.location: d for d in db_registrations}

            locations = get_configuration_setting("location-profiles")
            artikels = get_configuration_setting("artikel-profiles")
            location2ppi = {}
            for location, data in locations.items():
                price_per_item = int(artikels[data["artikel"]]["prijs-per-item"]) if "artikel" in data else 0
                location2ppi[location] = price_per_item

            for registration in registrations:
                key = str(registration[0]) + registration[2] + registration[3]
                if key in db_cache:
                    log.info(f'{inspect.currentframe().f_code.co_name}: registration already present, {registration}')
                    nbr_doubles += 1
                    continue
                new_registrations.append({"leerlingnummer": registration[2], "location": registration[3], "time_in": registration[0], "time_out": registration[1], "prijs_per_item": location2ppi[registration[3]]})
            add_m(Registration, new_registrations)
        return len(new_registrations), nbr_doubles
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return 0, 0

# get registrations from local client database and send to remote server
def sync_registrations_client():
    try:
        registrations = get_m(Registration)
        data = [[str(r.time_in), str(r.time_out), r.leerlingnummer, r.location] for r in registrations]
        ret = requests.post(f"{app.config['SYNC_REGISTRATIONS_URL']}/api/sync/registrations/data", headers={'x-api-key': app.config["SYNC_REGISTRATIONS_KEY"]}, json={"data": data})
        if ret.status_code == 200:
            res = ret.json()
            if res["status"]:
                delete_m(Registration, objs=registrations)
                return res["data"]["nbr_new"], res["data"]["nbr_doubles"]
        return 0, 0
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return 0, 0

def __send_sms(registration, location, student, force=False):
    try:
        receiver = ""
        if not registration.flag2 or force:
            text_body = get_configuration_setting("sms-student-too-late")
            text_body = text_body.replace("%%VOORNAAM%%", student.voornaam)
            text_body = text_body.replace("%%NAAM%%", student.naam)
            text_body = text_body.replace("%%TIJD%%", str(registration.time_in))
            enable_send_sms = location["enable_sending"]
            if "force_to" in location:  # overwrite sms receivers
                receiver = location["force_to"]
                send_sms(receiver, text_body, enable_send_sms)
            else:
                if student.lpv1_gsm != "":
                    send_sms(student.lpv1_gsm, text_body, enable_send_sms)
                    receiver += student.lpv1_gsm + "/"
                if student.lpv2_gsm != "":
                    send_sms(student.lpv2_gsm, text_body, enable_send_sms)
                    receiver += student.lpv2_gsm
            # flag2: sms is sent
            update(Registration, registration, {"flag2": True})
            log.info(f'{inspect.currentframe().f_code.co_name}: SMS ({location["locatie"]}), {student.naam} {student.voornaam} at {registration.time_in}, to {receiver}')
        else:
            log.info(f'{inspect.currentframe().f_code.co_name}: SMS ({location["locatie"]}), {student.naam} {student.voornaam} NOT sent')
        return registration.flag2
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return False

def __send_ss_message(registration, location, student, force=False):
    try:
        def __process_template(school, id):
            out = {}
            templates = get_configuration_setting("smartschool-message-templates").split("\n")
            for type in ["ONDERWERP", "INHOUD"]:
                start_subject_tag = f"%%{school.upper()}-{id}-{type}-START%%"
                stop_subject_tag = f"%%{school.upper()}-{id}-{type}-STOP%%"
                msg = None
                for line in templates:
                    if stop_subject_tag in line: break
                    if msg is not None and msg != "": msg += "\n"
                    if msg is not None: msg += line
                    if start_subject_tag in line: msg = ""
                if msg:
                    msg = msg.replace("%%VOORNAAM%%", student.voornaam)
                    msg = msg.replace("%%NAAM%%", student.naam)
                    msg = msg.replace("%%TIJD%%", str(registration.time_in))
                    msg = msg.replace("%%KLAS%%", str(student.klascode))
                    msg = msg.replace("%%AANTAL-OVERTREDINGEN%%", str(registration.aantal_items))
                out[type] = msg
            return out

        if not registration.flag1 or force:
            ss_internal_numbers = get_configuration_setting("ss-internal-numbers")

            rules = location["regel"]
            for rule in rules:
                if rule["operator"] == "=" and registration.aantal_items == rule["limiet"]: break
                if rule["operator"] == "<" and registration.aantal_items < rule["limiet"]: break
                if rule["operator"] == ">" and registration.aantal_items > rule["limiet"]: break
            else:
                rule = None
            if not rule: return False
            school = student.school
            if "force_to" in location:
                tos = location["force_to"]
            else:
                tos = location["to"][school.lower()][rule["bericht_id"]]
            ss_tos = []
            for to in tos:
                if to == "ouders":
                    ss_tos += [{"id": student.leerlingnummer, "coaccount": i} for i in range(3)]
                else:
                    staff = get(Staff, ("code", "=", to))
                    if staff:
                        ss_tos.append({"id": staff.ss_internal_nbr, "coaccount": 0})
                    else:
                        if ss_internal_numbers is not None:
                            if to in ss_internal_numbers:
                                ss_tos.append({"id": ss_internal_numbers[to], "coaccount": 0})
                            else:
                                log.error(f'{inspect.currentframe().f_code.co_name}: Could not find ss internal number of {to}')
                        else:
                            log.error(f'{inspect.currentframe().f_code.co_name}: Could not find ss internal number/or not defined in settings of {to}')
            message = __process_template(school, rule["bericht_id"])
            enable_sending = location["enable_sending"] if "enable_sending" in location else False
            if "from" in location:
                staff = get(Staff, ("code", "=", location["from"]))
                sender = staff.ss_internal_nbr
            else:
                sender = "csu"
            for to in ss_tos:
                ss_send_message(to["id"], sender, message["ONDERWERP"], message["INHOUD"], to["coaccount"], enable_sending)
            # flag1: message is sent
            update(Registration, registration, {"flag1": True})
            log.info(f'{inspect.currentframe().f_code.co_name}: Smartschool ({location["locatie"]}), {student.naam} {student.voornaam} at {registration.time_in}')
        else:
            log.info(f'{inspect.currentframe().f_code.co_name}: Smartschool ({location["locatie"]}), {student.naam} {student.voornaam} NOT sent')
            return False
        return True
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return False

def registration_export(location_key, start_date, stop_date):
    try:
        def __create_line(header, line, cache):
            for staff in header:
                if staff in cache:
                    seconds = cache[staff]
                    if seconds < 0:
                        seconds *= -1
                        sign = "-"
                    else:
                        sign = ""
                    hours = int(seconds / 3600)
                    minutes = int((seconds - hours * 3600) / 60)
                    seconds = seconds - hours * 3600 - minutes * 60
                    time_string = f"{minutes:02d}:{seconds:02d}"
                    if hours > 0:
                        time_string = f"{hours:02d}:{time_string}"
                    line.append(f"{sign}{time_string}")
                else:
                    line.append("")
            return line

        location_settings = get_configuration_setting("location-profiles")
        location = location_settings[location_key]
        registrations_to_export = []
        header = None
        if "table" in location and location["table"] == "staff":
            stop_date = stop_date.replace("00:00:00", "21:59:59")
            registrations = dl.registration.registration_staff_get(location_key, time_low=start_date, time_high=stop_date)
            start_eind_cache = {}
            rows = []
            header = []
            current_day_month = None
            row_cache = {}
            running_total = {}
            for (registration, staff) in registrations:
                registration_day_month = registration.time_in.month * 100 + registration.time_in.day
                if registration_day_month != current_day_month:
                    if current_day_month:
                        rows.append({"datum": f"{current_day_month % 100}/{int(current_day_month / 100)}", "staff": row_cache})
                        row_cache = {}
                    current_day_month = registration_day_month
                if staff.code not in start_eind_cache:
                    slices = staff.extra.split(",")
                    start_eind_cache[staff.code] = []
                    if len(slices) == 10:
                        for weekday in range(5):
                            hour, minute = slices[weekday * 2].split(":")
                            start_eind_cache[staff.code].append(int(hour) * 3600 + int(minute) * 60)
                            hour, minute = slices[weekday * 2 + 1].split(":")
                            start_eind_cache[staff.code].append(int(hour) * 3600 + int(minute) * 60)
                    else:
                        log.error(f'{inspect.currentframe().f_code.co_name}: error, staff {staff.code} start, einduur not correctly configured')
                        return {"data": f"Fout: staff {staff.code} start, einduur niet correct geconfigureerd"}
                key = f"{staff.naam} {staff.voornaam} {staff.code}"
                if key not in header: header.append(key)
                weekday = registration.time_in.weekday()
                if registration.time_out:
                    time_in = registration.time_in.hour * 3600 + registration.time_in.minute * 60 + registration.time_in.second
                    time_out = registration.time_out.hour * 3600 + registration.time_out.minute * 60 + registration.time_out.second
                    row_cache[key] = start_eind_cache[staff.code][weekday * 2] - time_in + time_out - start_eind_cache[staff.code][weekday * 2 + 1]
                    if key in running_total:
                        running_total[key] += row_cache[key]
                    else:
                        running_total[key] = row_cache[key]
            rows.append({"datum": f"{current_day_month % 100}/{int(current_day_month / 100)}", "staff": row_cache})
            registrations_to_export = []
            for row in rows:
                line = [row["datum"]]
                line = __create_line(header, line, row["staff"])
                registrations_to_export.append(line)
            line = ["totaal"]
            line = __create_line(header, line, running_total)
            registrations_to_export.append(line)
            header = ["datum"] + header
        else:
            registrations = dl.registration.registration_student_photo_get(location_key, time_low=start_date, time_high=stop_date)
            for (registration, student) in registrations:
                item = {"naam": student.naam, "voornaam": student.voornaam, "klas": student.klascode, "leerlingnummer": student.leerlingnummer, "tijd": str(registration.time_in)}
                if location["type"] == "cellphone":
                    item.update({"bericht-gestuurd": "JA" if registration.flag1 else "NEE"})
                    item.update({"aantal": registration.aantal_items})
                elif location["type"] == "sms":
                    item.update({"bevestigd": "JA" if registration.flag1 else "NEE"})
                    item.update({"sms-gestuurd": "JA" if registration.flag2 else "NEE"})
                registrations_to_export.append(item)

        if header:
            df = pd.DataFrame(registrations_to_export, columns=header)
        else:
            df = pd.DataFrame(registrations_to_export)
        out = io.BytesIO()
        excel_writer = pd.ExcelWriter(out, engine="xlsxwriter")
        df.to_excel(excel_writer, index=False)
        excel_writer.close()
        res = make_response(out.getvalue())
        res.headers["Content-Disposition"] = f"attachment; filename=export-{location['locatie']}-{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')}.xlsx"
        res.headers["Content-type"] = "data:text/xlsx"
        log.info(f'{inspect.currentframe().f_code.co_name}: Exported registration info, {len(registrations_to_export)} registrations for {location["locatie"]}')
        return res
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"data": f"Fout: {e}"}


