from app import app
from app.data.settings import get_configuration_setting, set_configuration_setting
import sys, requests

#logging on file level
import logging
from app import MyLogFilter, top_log_handle
log = logging.getLogger(f"{top_log_handle}.{__name__}")
log.addFilter(MyLogFilter())


def get_locations():
    try:
        locations = get_configuration_setting("location-profiles")
        ret = {k: l["locatie"] for k, l in locations.items()}
        return ret
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {}


def get_locations_articles():
    try:
        locations = get_configuration_setting("location-profiles")
        articles = get_configuration_setting("artikel-profiles")
        ret = {"locations": locations, "articles": articles}
        return {"status": True, "data": ret}
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return {"status": False, "data": str(e)}


#get locations from remote server
def sync_locations_articles_client():
    try:
        ret = requests.get(f"{app.config['SYNC_REGISTRATIONS_URL']}/api/location_article/get", headers={'x-api-key': app.config["SYNC_REGISTRATIONS_KEY"]})
        if ret.status_code == 200:
            res = ret.json()
            if res["status"]:
                locations = res["data"]["locations"]
                articles = res["data"]["articles"]
                set_configuration_setting("location-profiles", locations)
                set_configuration_setting("artikel-profiles", articles)
                return len(locations), len(articles)
            log.error(f'{inspect.currentframe().f_code.co_name}: {res}')
        log.error(f'{inspect.currentframe().f_code.co_name}: {ret.status_code}')
        return 0, 0
    except Exception as e:
        log.error(f'{inspect.currentframe().f_code.co_name}: {e}')
        return 0, 0
