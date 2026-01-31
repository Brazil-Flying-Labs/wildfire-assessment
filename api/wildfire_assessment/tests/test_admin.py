import importlib

import wildfire_assessment.admin as admin_module
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_assessment.models import Country, EcologicalReserve


class AdminTests(TestCase):
    def test_unregister_user_not_registered(self):
        User = get_user_model()
        for model in (User, Country, EcologicalReserve):
            if admin.site.is_registered(model):
                admin.site.unregister(model)

        importlib.reload(admin_module)

        for model in (User, Country, EcologicalReserve):
            self.assertTrue(admin.site.is_registered(model))
