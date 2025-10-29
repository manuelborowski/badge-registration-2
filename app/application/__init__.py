__all__ = ["user", "socketio", "datatables", "common", "settings", "cron", "models",]

import app.application.user
import app.application.socketio
import app.application.datatables
import app.application.common
import app.application.settings
import app.application.models

# tag, cront-task, label, help
cron_table = [
#    ('SDH-PERSON-UPDATE', person_cron_load_from_sdh, 'VAN SDH, upload studenten en personeel', ''),
]

import app.application.cron