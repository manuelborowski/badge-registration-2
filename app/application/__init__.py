__all__ = ["user", "socketio", "datatables", "common", "settings", "cron", "models", "email", "student", "staff", "registration"]

import app.application.user
import app.application.socketio
import app.application.datatables
import app.application.common
import app.application.settings
import app.application.models
import app.application.email
import app.application.staff
import app.application.student
import app.application.registration

from app.application.student import cron_student_load_from_sdh
# tag, cront-task, label, help
cron_table = [
   ('SDH-STUDENT-UPLOAD', cron_student_load_from_sdh, 'VAN SDH, upload studenten', ''),
]

import app.application.cron