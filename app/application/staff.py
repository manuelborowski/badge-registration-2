import inspect, requests
from app.data.models import get_m, update_m, add_m, delete_m
from app.data.staff import Staff
from app import data as dl

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app

log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def update(data):
    try:
        student = dl.models.get(Staff, ("id", "=", data["id"]))
        del data["id"]
        if ("rfid" in data):
            staff_rfid = dl.models.get(Staff, ("rfid", "=", data["rfid"]))
            if staff_rfid and student.id != staff_rfid.id:
                return {"status": "warning", "msg": f"RFID bestaat al voor personeel {staff_rfid.naam} {staff_rfid.voornaam}"}
        ret = dl.models.update(Staff, student, data)
        if (ret):
            return ret.to_dict()
        return {"status": "warning", "msg": f"Onbekende fout"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Fout: {str(e)}"}

def cron_staff_load_from_sdh(opaque=None, **kwargs):
    try:
        log.info(f"{inspect.currentframe().f_code.co_name}, START")
        updated_staff = []
        new_staff = []
        deleted_staff = []
        sdh_url = app.config["SDH_GET_STAFF_URL"]
        sdh_key = app.config["SDH_GET_API_KEY"]
        res = requests.get(sdh_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_staffs = res.json()
            if sdh_staffs['status']:
                db_staffs = get_m(Staff)
                db_code2staff = {s.code: s for s in db_staffs} if db_staffs else {}
                for staff in sdh_staffs["data"]:
                    update = {}
                    if staff["code"] in db_code2staff:
                        # update existing staff
                        db_staff = db_code2staff[staff["code"]]
                        if db_staff.voornaam != staff["voornaam"]:
                            update["voornaam"] = staff["voornaam"]
                        if db_staff.naam != staff["naam"]:
                            update["naam"] = staff["naam"]
                        if db_staff.rfid != staff["rfid"]:
                            update["rfid"] = staff["rfid"]
                        if db_staff.extra != staff["extra"]:
                            update["extra"] = staff["extra"]
                        if db_staff.ss_internal_nbr != staff["ss_internal_nbr"] if staff["ss_internal_nbr"] is not None else "":
                            update["ss_internal_nbr"] = staff["ss_internal_nbr"]
                        if update:
                            update.update({"item": db_staff})
                            updated_staff.append(update)
                        del db_code2staff[staff["code"]]
                    else:
                        # new staff
                        new_staff.append({"code": staff["code"], "voornaam": staff["voornaam"], "naam": staff["naam"],
                                          "ss_internal_nbr": staff["ss_internal_nbr"], "rfid": staff["rfid"], "extra": staff["extra"]})
                # removed staff
                for staff in db_code2staff.values():
                    deleted_staff.append(staff)
                log.info(f'{inspect.currentframe().f_code.co_name}, new/updated/deleted {len(new_staff)}/{len(updated_staff)}/{len(deleted_staff)} staff')
                update_m(Staff, updated_staff)
                add_m(Staff, new_staff)
                delete_m(Staff, objs=deleted_staff)
            else:
                log.info(f'{inspect.currentframe().f_code.co_name}, error retrieving staff from SDH, {sdh_staffs["data"]}')
        else:
            log.error(f'{inspect.currentframe().f_code.co_name}: api call to {sdh_url} returned {res.status_code}')
        log.info(f"{inspect.currentframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

