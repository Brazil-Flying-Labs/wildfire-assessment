from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_assessment.models import Country, UserCountry


class CountryModelTests(TestCase):
    def test_str_representation(self):
        country = Country.objects.create(name="Chile", code="CL")
        self.assertEqual(str(country), "CL - Chile")

    def test_user_country_str(self):
        user = get_user_model().objects.create(username="tester")
        country = Country.objects.create(name="Peru", code="PE")
        user_country = UserCountry.objects.create(user=user, country=country)
        self.assertEqual(str(user_country), "tester - PE")
