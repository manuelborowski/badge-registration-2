import datetime, inspect, base64, requests, io, pandas as pd
import app.application
from app import app, data as dl, application as al
from app.application.smartschool import send_message as ss_send_message
from flask import make_response
from app.application.sms import send_sms
from app.data.models import get, get_m, commit, update, update_m, add, add_m, delete_m
from app.data.student import Student
from app.data.staff import Staff
from app.data.reservation import Reservation
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
        if location_key == "new-rfid":
            reservation_margin = app.config["RESERVATION_MARGIN"]
            minimum_reservation_time = now - datetime.timedelta(seconds=reservation_margin)
            reservations = get_m(Reservation, [("valid", "=", False), ("timestamp", ">", minimum_reservation_time)])
            if reservations:
                reservation = reservations[0]
                if reservation.item == "rfid":
                    rfid = rfid.upper()
                    reservation.data = rfid
                    reservation.valid = True
                    student = get(Student, [("leerlingnummer", "=", reservation.leerlingnummer)])
                    student.rfid = rfid
                    commit()
                    if app.config["SDH_PUSH_RESERVATION_ON_THE_FLY"]:
                        ret = al.student.push_reservations_to_server()
                        if len(ret["data"]["errors"]) == 0:
                            log.info(f'{inspect.currentframe().f_code.co_name}:  Add reservation and push to SDH for {student.leerlingnummer}, {student.naam} {student.voornaam}')
                            return [{"to": "ip", "type": "alert-popup", "data": f"Student {student.naam} {student.voornaam} heeft nu RFID code {rfid}<br>Student kan ook al afdrukken met de badge"}]
                        else:
                            log.error(f'{inspect.currentframe().f_code.co_name}:  Add reservation and push to SDH for {student.leerlingnummer}, {student.naam} {student.voornaam}, returned error: {ret["data"]["errors"][0]}')
                            return [{"to": "ip", "type": "alert-popup", "data": f"<b>Foutmelding</b>: {ret["data"]["errors"][0]}"}]
                    else:
                        log.info(f'{inspect.currentframe().f_code.co_name}:  Add reservation for {student.leerlingnummer}, {student.naam} {student.voornaam} {location_key}')
                        return [{"to": "ip", "type": "alert-popup", "data": f"Student {student.naam} {student.voornaam} heeft nu RFID code {rfid}"}]
            log.info(f'{inspect.currentframe().f_code.co_name}:  No valid reservation for {location_key}')
            return [{"to": "ip", "type": "alert-popup", "data": f"Nieuwe RFID niet gelukt.  Misschien te lang gewacht met scannen, probeer nogmaals"}]

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
        inout = location["inout"] if "inout" in location else None

        # Staff specific registrations
        if "table" in location and location["table"] == "staff":
            staff = get(Staff, ("rfid", "=", rfid))
            if staff:
                log.info(f'{inspect.currentframe().f_code.co_name}:  Add registration for {staff.code}, {staff.naam} {staff.voornaam} {location_key}')
                if location["type"] == "timeregistration":
                    registrations = get_m(Registration, [("leerlingnummer", "=", staff.code), ("location", "=", location_key), ("time_in", ">", today)], order_by="id")
                    last_registration = registrations[-1] if len(registrations) > 0 else None
                    if last_registration and backoff:
                        if (now - (last_registration.time_in if last_registration.time_out == None else last_registration.time_out)).seconds < backoff:
                            return [{"to": "ip", 'type': 'alert-popup', "data": f"Sorry, u moet langer wachten om terug te scannen"}]
                    if last_registration and last_registration.time_out is None:
                        update(Registration, last_registration, {"time_out": now})
                        log.info(f'{inspect.currentframe().f_code.co_name}: Badge out, {staff.code} at {now}')
                        ret_location = {"to": "location", 'type': 'update-items-in-list-of-registrations',
                                        'data': {"status": True, "data": [{"id": last_registration.id, "time_out": str(now)}]}}
                        return {"status": "warning", "msg":f"{staff.voornaam} {staff.naam}<br>"
                                          f"Je bent IN gescand om {last_registration.time_in}<br>"
                                          f"Je bent UIT gescand om {last_registration.time_out}"}

                        return [ret_location, ret_ip]
                    else:
                        ret_location = {"to": "location", 'type': 'update-list-of-registrations',
                                        'data': {"status": True, "date": str(today), "action": "add",
                                                 "data": [{"leerlingnummer": staff.code, "naam": staff.naam, "voornaam": staff.voornaam, "klascode": staff.code, "time_out": ""}]
                                                 }}
                        registration = add(Registration, {"leerlingnummer": staff.code, "location": location_key, "time_in": now})  # copy extra to text1
                        if registration:
                            ret_location["data"]["data"][0].update({"timestamp": str(now), "id": registration.id})
                            ret_ip = {"to": "ip", 'type': 'alert-popup', "data": f"{staff.voornaam} {staff.naam}<br>Je bent IN gescand om {now}<br>"}
                            return [ret_location, ret_ip]
            log.info(f'{inspect.currentframe().f_code.co_name}: rfid {rfid} not found in table: staff')
            return [{"to": "ip", 'type': 'alert-popup', "data": f"Kan personeelslid met rfid {rfid} niet vinden in database"}]

        # student specific registrations
        if rfid:
            student = get(Student, [("rfid", "=", rfid)])
        elif leerlingnummer:
            student = get(Student, [("leerlingnummer", "=", leerlingnummer)])
        else:
            return [{"to": "ip", 'type': 'alert-popup', "data": "Geen RFID of leerlingnummer gevonden"}]
        if student:
            photo_obj = get(Photo, ("id", "=", student.foto_id))
            photo = base64.b64encode(photo_obj.photo).decode('utf-8') if photo_obj else ''
            log.info(f'{inspect.currentframe().f_code.co_name}:  Add registration for {student.leerlingnummer}, {student.naam} {student.voornaam} {location_key}')
            ret_location = {'type': 'update-list-of-registrations', "data": {"action": "add", "data": [{"student": student.to_dict(), "photo": photo}]}}

            if location["type"] == "nietverplicht":
                registrations = get_m(Registration, [("leerlingnummer", "=", student.leerlingnummer), ("location", "=", location_key), ("time_in", ">", today)], order_by="id")
                if registrations:
                    last_registration = registrations[-1]
                    if last_registration.time_out is None:
                        update(Registration, last_registration, {"time_out": now})
                        log.info(f'{inspect.currentframe().f_code.co_name}: Badge out, {student.leerlingnummer} at {now}')
                        return {'type': 'update-list-of-registrations', 'data': {"status": True, "action": "delete", "data": [{"id": last_registration.id}]}}
                registration = add(Registration, {"leerlingnummer": student.leerlingnummer, "location": location_key, "time_in": now})
                if registration:
                    log.info(f'{inspect.currentframe().f_code.co_name}: Badge in, {student.leerlingnummer} at {now}')
                    ret_location["data"][0].update({"timestamp": str(registration.time_in), "id": registration.id, })
                    return {'type': 'update-list-of-registrations', 'data': ret_location}
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
                        return [{"to": "ip", 'type': 'alert-popup', "data": f"Student {student.naam} {student.voornaam} heeft het maximum aantal van {max_qty} artikel(s) bereikt"}]
                    current_qty += 1
                    mask = mask[:day_index + 6] + str(current_qty) + mask[day_index + 7:]
                    update(Student, student, {location["dagmasker"]: mask})
                registration = add(Registration, {"person_id": student.leerlingnummer, "location": location_key, "time_in": now, "prijs_per_item": artikel["prijs-per-item"], "aantal_items": nbr_items, "person_type": "student"})
                if registration:
                    log.info(f'{inspect.currentframe().f_code.co_name}: Verkoop({location["locatie"]}), {student.leerlingnummer} at {now}, price-per-item {artikel["prijs-per-item"]}, nbr items {nbr_items}')


                    ret_location["data"]["data"][0].update({"registration": registration.to_dict()})
                    al.socketio.send_to_room(ret_location["data"], location_key)
                    return {"status": "ok", "msg": f"student {student.naam} {student.voornaam} heeft gescand om {registration.time_in}"}

                    return [ret_location, ret_ip]

            # When a student is too late in, scan its badge.  An sms is sent to the parents and a why-too-late reason needs to be added
            # If the student returns with a valid proof of being late, tick the registration as being acknowledged/finished
            # text1: remark
            # flag1: remark is acknowledged
            # flag2: sms is sent
            if location["type"] == "sms":
                registration = add(Registration, {"leerlingnummer": student.leerlingnummer, "location": location_key, "time_in": now})
                if registration:
                    sms_sent = False
                    if "auto" in location and location["auto"]:  # send sms when badge is scanned
                        sms_sent = __send_sms(registration, location, student)
                    auto_remark = location["auto_remark"] if "auto_remark" in location else False
                    ret_location["data"]["data"][0].update({"id": registration.id, "remark": "", "remark_ack": False, "sms_sent": sms_sent, "auto_remark": auto_remark})
                    return [ret_location, ret_ip]
            # When a student needs to hand in its cellphone, its badge is scanned.
            # Depending on the number of times, a rule is invoked to color the scan and/or send smartschool messages
            # aantal_items: store the sequence-counter
            # flag1: message sent
            if location["type"] == "cellphone":
                if student.school not in location["school"]:
                    return [{"to": "ip", 'type': 'alert-popup', "data": f"Student {student.naam} {student.voornaam} zit in een andere school, {student.school}"}]
                last_registration = get(Registration, [("leerlingnummer", "=", student.leerlingnummer), ("location", "=", location_key)], order_by="-id")
                if last_registration:
                    sequence_counter = last_registration.aantal_items + 1
                else:
                    sequence_counter = 1
                registration = add(Registration, {"leerlingnummer": student.leerlingnummer, "location": location_key, "time_in": now, "aantal_items": sequence_counter})
                if registration:
                    message_sent = False
                    if "auto" in location and location["auto"]:  # send message when badge is scanned
                        message_sent = __send_ss_message(registration, location, student)
                    ret_location["data"]["data"][0].update({"id": registration.id, "sequence_ctr": sequence_counter, "message_sent": message_sent})
                    return [ret_location, ret_ip]

            if location["type"] == "toilet":
                last_registration = get(Registration, [("leerlingnummer", "=", student.leerlingnummer), ("location", "=", location_key)], order_by="-id")
                if last_registration:
                    sequence_counter = last_registration.aantal_items + 1
                else:
                    sequence_counter = 1
                registration = add(Registration, {"leerlingnummer": student.leerlingnummer, "location": location_key, "time_in": now, "aantal_items": sequence_counter})
                if registration:
                    ret_location["data"]["data"][0].update({"id": registration.id, "sequence_ctr": sequence_counter})
                    return [ret_location, ret_ip]

            log.info(f'{inspect.currentframe().f_code.co_name}:  {student.leerlingnummer} could not make a registration')
            return [{"to": "ip", "type": "alert-popup", "data": "Kan geen nieuwe registratie maken"}]
        log.info(f'{inspect.currentframe().f_code.co_name}:  rif/leerlingnummer {rfid}/{leerlingnummer} not found in database')
        return [{"to": "ip", "type": "alert-popup", "data": f"Kan student met rfid {rfid} / leerlingnummer {leerlingnummer} niet vinden in database"}]
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Foutmelding: {e}"}

def registration_delete(ids):
    try:
        delete_m(Registration, ids)
        ret = {
            "status": True,
            "action": "delete",
            "data": [{"id": id} for id in ids]
        }
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {str(e)}"}

def registration_zero_counters(location, date):
    try:
        registrations = get_m(Registration, [("location", "=", location), ("time_in", "<", date)])
        for registration in registrations:
            registration.active = False
        registrations = get_m(Registration, [("location", "=", location), ("time_in", ">=", date)])
        aantal_items_cache = {}
        for registration in registrations:
            if registration.leerlingnummer in aantal_items_cache:
                registration.aantal_items -= aantal_items_cache[registration.leerlingnummer]
            else:
                aantal_items_cache[registration.leerlingnummer] = registration.aantal_items - 1
                registration.aantal_items = 1
        commit()
        ret = {"status": True, "data": "Ok, tellers zijn op nul gezet"}
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": f"Fout, {str(e)}"}

# filters priority (high to low)
# search
# sms/cellphone specific
# period

def registration_get(location_key=None, view_layout=None, period=None):
    try:
        locations = get_configuration_setting("location-profiles")
        location = locations[location_key]
        type = location["type"]
        ret = []
        time_low = time_high = selected_day = None
        flag1 = flag2 = None
        # ignore period filter when the sms-specific or cellphone-specific is used
        if period in ["last-2-months", "last-4-months", "last-week"]:
            delta = 60 if period == "last-2-months" else 120 if period == "last-4-months" else 7
            time_low = datetime.datetime.now() - datetime.timedelta(days=delta)
        if "table" in location and location["table"] == "staff":
            # Staff specific data
            ret.update({"headers": ["Naam", "Code", "Tijd in", "Startuur", "Verschil", "Tijd uit", "Einduur", "Verschil", "Dagverschil", "Opmerking"]})
            registrations = dl.registration.registration_staff_get(location_key, search=search, time_low=time_low, time_high=time_high)
            staff_cache = {}
            for tuple in registrations:
                registration = tuple[0]
                staff = tuple[1]
                item = {"person": staff.to_dict(), "registration": registration}
                # weekday = registration.time_in.weekday()
                # key = f"{staff.code}{weekday}"
                # if key not in staff_cache:
                #     slices = staff.extra.split(",")
                #     if slices and len(slices) == 10:
                #         staff_cache[key] = {"startuur": slices[weekday * 2], "einduur": slices[weekday * 2 + 1]}
                #     else:
                #         staff_cache[key] = {"startuur": "", "einduur": ""}
                # item.update({"startuur": staff_cache[key]["startuur"], "einduur": staff_cache[key]["einduur"]})

                ret["data"].append(item)
        else:
            # Student specific data
            include_foto = view_layout == "tile"
            # if search == None:
            #     if type == "sms":
            #         flag1 = False if filters["sms-specific-select"] == "no-ack" else None
            #         flag2 = False if filters["sms-specific-select"] == "no-sms-sent" else None
            #     elif type == "cellphone":
            #         flag1 = False if filters["cellphone-specific-select"] == "no-message-sent" else None
            #     if flag1 != None or flag2 != None:
            #         time_low = time_high = selected_day = None
            registrations = dl.registration.registration_student_photo_get(location_key, time_low=time_low, time_high=time_high, flag1=flag1, flag2=flag2, include_foto=include_foto)
            for tuple in registrations:
                registration = tuple[0]
                student = tuple[1]
                item = student.to_dict()
                item.update(registration.to_dict())
                if include_foto:
                    photo = tuple[2]
                    item.update({"photo": base64.b64encode(photo.photo).decode('utf-8') if photo and photo.photo else ''})
                # if type == "sms":
                #     item.update({"remark": registration.text1, "remark_ack": registration.flag1, "sms_sent": registration.flag2, })
                # elif type == "cellphone":
                #     item.update({"sequence_ctr": registration.aantal_items, "message_sent": registration.flag1})
                # elif type == "toilet":
                #     item.update({"sequence_ctr": registration.aantal_items})
                ret.append(item)

            # if search != None:
            #     ret.update({"search": True})
            # elif selected_day != None:
            #     ret.update({"date": selected_day})

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

def api_registration_send_message(ids, location_key):
    try:
        location_settings = get_configuration_setting("location-profiles")
        if location_key not in location_settings:
            log.info(f'{inspect.currentframe().f_code.co_name}:  {location_key} is not valid')
            return {"status": False, "data": f"Locatie {location_key} is niet geldig"}
        location = location_settings[location_key]
        data = []
        for id in ids:
            registration = get(Registration, ("id", "=", id))
            student = get(Student, [("leerlingnummer", "=", registration.leerlingnummer)])
            if student:
                if location["type"] == "sms":
                    data.append({"id": id, "sms_sent": __send_sms(registration, location, student)})
                if location["type"] == "cellphone":
                    data.append({"id": id, "ss_message_sent": __send_ss_message(registration, location, student)})
            else:
                log.error(f'{inspect.currentframe().f_code.co_name}: could not find student fore registration {id}')
        return {"status": True, "data": data}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}

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
        return registration.flag1
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


