import inspect, requests, base64, datetime
from app.data.student import Student
from app.data.photo import Photo
from app.data.models import get_m, add_m, update_m, delete_m, get, add

#logging on file level
import logging
from app import MyLogFilter, top_log_handle, app, application as al, data as dl
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())

def cron_student_load_from_sdh(opaque=None, **kwargs):
    log.info(f'{inspect.currentframe().f_code.co_name}, START')
    updated_students = []
    nbr_updated = 0
    new_students = []
    deleted_students = []
    try:
        # check for new, updated or deleted students
        sdh_student_url = app.config["SDH_GET_STUDENT_URL"]
        sdh_key = app.config["SDH_GET_API_KEY"]
        res = requests.get(sdh_student_url, headers={'x-api-key': sdh_key})
        if res.status_code == 200:
            sdh_students = res.json()
            if sdh_students['status']:
                log.info(f'{inspect.currentframe().f_code.co_name}, retrieved {len(sdh_students["data"])} students from SDH')
                db_students = get_m(Student)
                db_leerlingnummer_to_student = {s.leerlingnummer: s for s in db_students}
                for sdh_student in sdh_students["data"]:
                    soep_changed = False
                    if sdh_student["leerlingnummer"] in db_leerlingnummer_to_student:
                        # check for changed rfid or classgroup
                        db_student = db_leerlingnummer_to_student[sdh_student["leerlingnummer"]]
                        update = {}
                        if db_student.rfid != sdh_student["rfid"]:
                            update["rfid"] = sdh_student["rfid"]
                        if db_student.klascode != sdh_student["klascode"]:
                            update["klascode"] = sdh_student["klascode"]
                            update["instellingsnummer"] = sdh_student["instellingsnummer"]
                        if db_student.middag != sdh_student["middag"]:
                            update["middag"] = sdh_student["middag"]
                        if db_student.username != sdh_student["username"]:
                            update["username"] = sdh_student["username"]
                        if sdh_student["soep"] != "":
                            soep = sdh_student["soep"][:2] + "0" + sdh_student["soep"][2:]
                            if db_student.soep[:5] != soep:
                                update["soep"] = soep + "/00000"
                                soep_changed = True
                        if db_student.lpv1_gsm != sdh_student["lpv1_gsm"]:
                            update["lpv1_gsm"] = sdh_student["lpv1_gsm"]
                        if db_student.lpv2_gsm != sdh_student["lpv2_gsm"]:
                            update["lpv2_gsm"] = sdh_student["lpv2_gsm"]
                        if db_student.foto_id != sdh_student["foto_id"]:
                            update["foto_id"] = sdh_student["foto_id"]
                        if db_student.instellingsnummer != sdh_student["instellingsnummer"]:
                            update["instellingsnummer"] = sdh_student["instellingsnummer"]
                        if db_student.roepnaam != sdh_student["roepnaam"]:
                            update["roepnaam"] = sdh_student["roepnaam"]
                        if update:
                            update.update({"item": db_student})
                            updated_students.append(update)
                            log.info(f'{inspect.currentframe().f_code.co_name}, Update student {db_student.leerlingnummer}, update {update}')
                            nbr_updated += 1
                        if db_student.soep != "" and not soep_changed: #reset soep quantity counters
                            updated_students.append({"item": db_student, "soep": db_student.soep[:5] + "/00000"})
                        del(db_leerlingnummer_to_student[sdh_student["leerlingnummer"]])
                    else:
                        new_student = {"leerlingnummer": sdh_student["leerlingnummer"], "klascode": sdh_student["klascode"], "naam": sdh_student["naam"], "roepnaam": sdh_student["roepnaam"],
                                             "voornaam": sdh_student["voornaam"], "middag": sdh_student["middag"], "rfid": sdh_student["rfid"], "foto_id": sdh_student["foto_id"],
                                             "lpv1_gsm": sdh_student["lpv1_gsm"], "lpv2_gsm": sdh_student["lpv2_gsm"], "instellingsnummer": sdh_student["instellingsnummer"], "username": sdh_student["username"]}
                        if sdh_student["soep"] != "":
                            new_student["soep"] = sdh_student["soep"][:2] + "0" + sdh_student["soep"][2:] + "/00000"
                        new_students.append(new_student)
                        log.info(f'{inspect.currentframe().f_code.co_name}, New student {sdh_student["leerlingnummer"]}')
                deleted_students = [v for (k, v) in db_leerlingnummer_to_student.items()]
                for student in deleted_students:
                    log.info(f'{inspect.currentframe().f_code.co_name}, Delete student {student.leerlingnummer}')
                deleted_photo_ids = [v.foto_id for (k, v) in db_leerlingnummer_to_student.items()]
                add_m(Student, new_students)
                update_m(Student, updated_students)
                delete_m(Student, objs=deleted_students)
                delete_m(Photo, deleted_photo_ids)
                log.info(f'{inspect.currentframe().f_code.co_name}, students add {len(new_students)}, update {nbr_updated}, delete {len(deleted_students)}')
            else:
                log.info(f'{inspect.currentframe().f_code.co_name}, error retrieving students from SDH, {sdh_students["data"]}')
        else:
            log.error(f'{inspect.currentframe().f_code.co_name}: api call to {sdh_student_url} returned {res.status_code}')

        # check for all students if their photo is changed (different size)
        sdh_photo_size_url = app.config["SDH_GET_PHOTO_SIZE_URL"]
        db_students = get_m(Student)
        photo_ids = [str(s.foto_id) for s in db_students]
        sliced_photo_ids = al.common.slice_list(photo_ids, 200)
        photos_to_check = []
        db_photo_sizes = dl.photo.photo_get_size_m()
        id_to_photo_size = {p[0]: p[5] for p in db_photo_sizes}
        for slice in sliced_photo_ids:
            res = requests.get(sdh_photo_size_url, params={"ids": ",".join(slice)}, headers={'x-api-key': sdh_key})
            if res.status_code == 200:
                sdh_photo_data = res.json()
                if sdh_photo_data["status"]:
                    log.info(f'{inspect.currentframe().f_code.co_name}, retrieved {len(sdh_photo_data["data"])} photo sizes from SDH')
                    for sdh_photo in sdh_photo_data["data"]:
                        if sdh_photo["id"] in id_to_photo_size:
                            if sdh_photo["size"] != id_to_photo_size[sdh_photo["id"]]:
                                photos_to_check.append(sdh_photo["id"])
                        else:
                            photos_to_check.append(sdh_photo["id"])
                    log.info(f'{inspect.currentframe().f_code.co_name}, {len(photos_to_check)} photos to check')
                else:
                    log.info(f'{inspect.currentframe().f_code.co_name}, error retrieving photo sizes from SDH, {sdh_photo_data["data"]}')
            else:
                log.error(f'{inspect.currentframe().f_code.co_name}: api call to {sdh_photo_size_url} returned {res.status_code}')

        # get the changed photos
        if photos_to_check:
            sdh_photo_url = app.config["SDH_GET_PHOTO_URL"]
            photo_ids = [str(p) for p in photos_to_check]
            sliced_photo_ids = al.common.slice_list(photo_ids, 200)
            for slice in sliced_photo_ids:
                res = requests.get(sdh_photo_url, params={"ids": ",".join(slice)}, headers={'x-api-key': sdh_key})
                if res.status_code == 200:
                    sdh_photo_data = res.json()
                    if sdh_photo_data["status"]:
                        update_photos = []
                        new_photos = []
                        log.info(f'{inspect.currentframe().f_code.co_name}, retrieved {len(sdh_photo_data["data"])} photos from SDH')
                        for sdh_photo in sdh_photo_data["data"]:
                            id = sdh_photo["id"]
                            decoded_photo = base64.b64decode(sdh_photo["photo"].encode("ascii"))
                            if id in id_to_photo_size:
                                photo = get(Photo, {"id": id})
                                update_photos.append({"item": photo, "photo": decoded_photo})
                                log.info(f'{inspect.currentframe().f_code.co_name}, Update photo {id}')
                            else:
                                new_photos.append({"id": id, "photo": decoded_photo})
                                log.info(f'{inspect.currentframe().f_code.co_name}, New photo {id}')
                        add_m(Photo, new_photos)
                        update_m(Photo, update_photos)
                        log.info(f'{inspect.currentframe().f_code.co_name}, {len(update_photos)} photos to update, {len(new_photos)} new photos')
                    else:
                        log.info(f'{inspect.currentframe().f_code.co_name}, error retrieving photos from SDH, {sdh_photo_data["data"]}')
                else:
                    log.error(f'{inspect.currentframe().f_code.co_name}: api call to {sdh_photo_url} returned {res.status_code}')
        log.info(f"{inspect.currentframe().f_code.co_name}, STOP")
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return 0, 0, 0
    return len(new_students), nbr_updated, len(deleted_students)

def update(data):
    try:
        student = dl.models.get(Student, ("id", "=", data["id"]))
        del data["id"]
        if ("rfid" in data):
            student_rfid = dl.models.get(Student, ("rfid", "=", data["rfid"]))
            if student_rfid and student.id != student_rfid.id:
                return {"status": "warning", "msg": f"RFID bestaat al voor leerling {student_rfid.naam} {student_rfid.voornaam}"}
        ret = dl.models.update(Student, student, data)
        if (ret):
            push_new_rfid_to_sdh(student.leerlingnummer, ret.rfid)
            return ret.to_dict()
        return {"status": "warning", "msg": f"Onbekende fout"}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": "error", "msg": f"Fout: {str(e)}"}


def klassen_get_unique():
    klassen = get_m(Student, fields=['klascode'])
    klassen = list(set([k[0] for k in klassen]))
    klassen.sort()
    return klassen

def push_new_rfid_to_sdh(leerlingnummer, rfid):
    try:
        sdh_student_url = app.config["SDH_SET_STUDENT_URL"]
        sdh_key = app.config["SDH_SET_API_KEY"]
        sdh_test = app.config["SDH_SET_TEST"]
        res = requests.post(sdh_student_url, headers={'x-api-key': sdh_key}, json={"leerlingnummer": leerlingnummer, "rfid": rfid, "test": sdh_test})
        if res.status_code == 200:
            data = res.json()
            if data["status"]:
                log.info(f'{inspect.currentframe().f_code.co_name}: Updated student RFID to SDH, {leerlingnummer}, {rfid}')
            else:
                log.info(f'{inspect.currentframe().f_code.co_name}: SDH returned, {data["data"]}')
        else:
            log.error(f'{inspect.currentframe().f_code.co_name}: api call to {sdh_student_url} returned {res.status_code}')
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')

############ datatables: student overview list #########
def format_data(db_list, total_count=None, filtered_count=None):
    out = []
    for student in db_list:
        em = student.to_dict()
        em.update({
            'row_action': student.id,
            'DT_RowId': student.id
        })
        out.append(em)
    return total_count, filtered_count, out


