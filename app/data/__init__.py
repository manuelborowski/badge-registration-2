__all__ = ["user", "models", "settings", "datatables", "registration", "photo", "staff", "student", "entra", "reservation"]

import app.data.user
import app.data.models
import app.data.settings
import app.data.datatables
import app.data.photo
import app.data.registration
import app.data.staff
import app.data.student
import app.data.entra
import app.data.reservation

from app import login_manager
@login_manager.user_loader
def load_user(user_id):
    return app.data.user.load_user(user_id)
