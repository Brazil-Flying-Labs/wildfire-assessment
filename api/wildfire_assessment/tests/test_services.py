import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_assessment.models import (
    AnalysisRun,
    AreaOfInterest,
    Country,
    UserCountry,
    UserProfile,
)
from wildfire_assessment.svc import analytics
from wildfire_assessment.svc import area_of_interest as aoi_service
from wildfire_assessment.svc import aws
from wildfire_assessment.svc import dashboard as dashboard_service
from wildfire_assessment.svc import processor

User = get_user_model()


class ProcessorTests(TestCase):
    def setUp(self):
        self.fire_id = 42
        self.execution_id = "exec-123"
        self.pre_fire_date = "2023-01-01"
        self.post_fire_date = "2023-01-10"
        self.polygon_path = "sample.geojson"
        self.email = "user@example.com"
        self.reserve_name = "Reserve Test"

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_fire_assessment_uses_visual_urls_when_available(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_unlink,
    ):
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "visual": {
                "DNBR_AREA_STATISTICS": {"url": "http://example.com/stats.json"},
                "RGB_PRE_FIRE_VISUAL": {"url": "http://example.com/pre.jpg"},
                "RGB_POST_FIRE_VISUAL": {"url": "http://example.com/post.jpg"},
                "DNDVI_VISUAL": {"url": "http://example.com/dndvi.jpg"},
                "DNBR_VISUAL": {"url": "http://example.com/dnbr.jpg"},
                "RBR_VISUAL": {"url": "http://example.com/rbr.jpg"},
            },
            "statistics": {
                "DNBR_AREA_STATISTICS": {"url": "http://example.com/stats.json"}
            },
        }
        mock_assessment.return_value = assessment_instance

        result = processor.process_fire_assessment(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
        )

        mock_download.assert_called_once_with(self.polygon_path)
        mock_assessment.assert_called_once()
        mock_unlink.assert_called_once()
        self.assertIn("severity_map", result)
        self.assertIn("rgb_pre_fire_visual_jpg", result)
        self.assertIn("rgb_post_fire_visual_jpg", result)
        self.assertIn("dndvi_visual_jpg", result)
        self.assertIn("dnbr_visual_jpg", result)
        self.assertIn("rbr_visual_jpg", result)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_notifies_user(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.side_effect = [
            [{"state": "RUNNING"}],
            [{"state": "COMPLETED"}],
        ]

        status = processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
        )

        self.assertEqual(status, "COMPLETED")
        mock_send_email.assert_called_once()
        mock_unlink.assert_called_once()
        called_kwargs = mock_send_email.call_args.kwargs
        self.assertEqual(called_kwargs["to_address"], self.email)
        self.assertIn(self.reserve_name, called_kwargs["body"])

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_uses_user_language_preference(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Test that email is sent in user's preferred language."""
        # Create a user with Portuguese language preference
        user = User.objects.create_user(
            username="testuser",
            email=self.email,
            password="testpass",
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.default_language = "pt-BR"
        profile.save()

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        status = processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
        )

        self.assertEqual(status, "COMPLETED")
        mock_send_email.assert_called_once()
        called_kwargs = mock_send_email.call_args.kwargs
        # Should use Portuguese subject
        self.assertEqual(
            called_kwargs["subject"],
            "Wildfire Analyser - Produto Científico Pronto",
        )
        # Body should be in Portuguese
        self.assertIn("está pronto para download", called_kwargs["body"])

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    @patch("wildfire_assessment.svc.processor.UserProfile")
    def test_process_scientific_deliverable_falls_back_on_user_lookup_error(
        self,
        mock_profile_model,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Test that email falls back to English when user lookup fails."""
        # Make UserProfile.objects.filter raise an exception
        mock_profile_model.objects.filter.side_effect = Exception("Database error")

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        status = processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
        )

        self.assertEqual(status, "COMPLETED")
        mock_send_email.assert_called_once()
        called_kwargs = mock_send_email.call_args.kwargs
        # Should fall back to English subject
        self.assertEqual(
            called_kwargs["subject"],
            "Wildfire Analyser - Scientific Deliverable Ready",
        )

    @patch("wildfire_assessment.svc.processor.Deliverable")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_invalid_deliverable(
        self, mock_secret, mock_enum
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_enum.__getitem__.side_effect = KeyError

        with self.assertRaises(ValueError):
            processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name="UNKNOWN",
                email=self.email,
                reserve_name=self.reserve_name,
            )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.Deliverable")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_unmapped_deliverable(
        self,
        mock_secret,
        mock_deliverable,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        _mock_send,
        mock_unlink,
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        sentinel = object()
        mock_deliverable.__getitem__.return_value = sentinel
        mock_deliverable.RGB_PRE_FIRE = object()
        mock_deliverable.RGB_POST_FIRE = object()
        mock_deliverable.DNBR = object()
        mock_deliverable.RBR = object()
        mock_deliverable.DNDVI = object()

        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [[{"state": "COMPLETED"}]]

        with self.assertRaises(ValueError):
            processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name="RGB_PRE_FIRE",
                email=self.email,
                reserve_name=self.reserve_name,
            )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_missing_statuses(
        self, mock_secret, mock_download, mock_assessment, mock_ee, _mock_sleep, mock_unlink
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = []

        with self.assertRaises(RuntimeError):
            processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name=Deliverable.DNBR.name,
                email=self.email,
                reserve_name=self.reserve_name,
            )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_failed_status(
        self, mock_secret, mock_download, mock_assessment, mock_ee, _mock_sleep, mock_unlink
    ):
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [
            {"state": "FAILED", "error_message": "boom"}
        ]

        with self.assertRaises(RuntimeError):
            processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name=Deliverable.DNBR.name,
                email=self.email,
                reserve_name=self.reserve_name,
            )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_deliverable_keys(
        self, mock_secret, mock_download, mock_assessment, mock_ee, _mock_sleep, mock_send, mock_unlink
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        for deliverable in [
            Deliverable.RGB_PRE_FIRE,
            Deliverable.RGB_POST_FIRE,
            Deliverable.DNBR,
            Deliverable.RBR,
            Deliverable.DNDVI,
        ]:
            assessment_instance = MagicMock()
            assessment_instance.run.return_value = {
                "scientific": {
                    deliverable.name: {
                        "gee_task_id": "task-1",
                        "url": "http://files/test",
                    }
                }
            }
            mock_assessment.return_value = assessment_instance
            mock_ee.data.getTaskStatus.side_effect = [[{"state": "COMPLETED"}]]

            status = processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name=deliverable.name,
                email=self.email,
                reserve_name=self.reserve_name,
            )
            self.assertEqual(status, "COMPLETED")
            mock_send.assert_called()


class AwsUtilsTests(TestCase):
    @patch("wildfire_assessment.svc.aws.boto3.Session")
    def test_get_boto3_session_success(self, mock_session):
        session = MagicMock()
        mock_session.return_value = session
        self.assertEqual(aws.get_boto3_session(), session)

    @patch("wildfire_assessment.svc.aws.boto3.Session")
    def test_get_boto3_session_profile_not_found(self, mock_session):
        mock_session.side_effect = aws.ProfileNotFound(profile="default")
        with self.assertRaises(ValueError):
            aws.get_boto3_session()

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_get_secret_manager_secret(self, mock_session):
        client = MagicMock()
        client.get_secret_value.return_value = {"SecretString": "secret"}
        mock_session.return_value.client.return_value = client
        secret = aws.get_aws_secret_manager_secret("my-secret")
        self.assertEqual(secret, "secret")

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_get_secret_manager_secret_failure(self, mock_session):
        client = MagicMock()
        client.get_secret_value.side_effect = aws.ClientError(
            error_response={"Error": {"Code": "404", "Message": "NotFound"}},
            operation_name="GetSecretValue",
        )
        mock_session.return_value.client.return_value = client
        with self.assertRaises(ValueError):
            aws.get_aws_secret_manager_secret("missing")

    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_get_gee_private_key_json_stripping(self, mock_secret):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "'{\\\"key\\\":123}'"}
        )
        key = processor.get_gee_private_key_json()
        self.assertFalse(key.startswith("'"))
        self.assertEqual(json.loads(key)["key"], 123)


class AreaOfInterestServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="svcuser", password="pw")
        self.country = Country.objects.create(name="Svc Country", code="SV")
        self.area = AreaOfInterest.objects.create(
            name="Svc Area",
            polygon_path="svc.geojson",
            country=self.country,
        )

    # -- delete_polygon_file --------------------------------------------------

    def test_delete_polygon_file_empty_path(self):
        self.assertFalse(aoi_service.delete_polygon_file(""))

    def test_delete_polygon_file_none_path(self):
        self.assertFalse(aoi_service.delete_polygon_file(None))

    # -- user_can_access_area -------------------------------------------------

    def test_user_can_access_area_true(self):
        UserCountry.objects.create(user=self.user, country=self.country)
        self.assertTrue(aoi_service.user_can_access_area(self.user, self.area))

    def test_user_can_access_area_false(self):
        self.assertFalse(aoi_service.user_can_access_area(self.user, self.area))

    # -- save_analysis_run ----------------------------------------------------

    def test_save_analysis_run_with_string_severity_map(self):
        severity = {"Total Burned Area": {"area_ha": 42.5}}
        result = {"severity_map": json.dumps(severity)}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertEqual(run.severity_data, severity)
        self.assertEqual(float(run.total_burned_ha), 42.5)
        self.assertEqual(run.status, "completed")

    def test_save_analysis_run_with_dict_severity_map(self):
        severity = {"Total Burned Area": {"area_ha": 10.0}, "High": {}}
        result = {"severity_map": severity}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertEqual(run.severity_data, severity)
        self.assertEqual(float(run.total_burned_ha), 10.0)

    def test_save_analysis_run_without_severity_map(self):
        result = {"s3_urls": {}}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertIsNone(run.severity_data)
        self.assertIsNone(run.total_burned_ha)

    def test_save_analysis_run_with_invalid_severity_map_json(self):
        result = {"severity_map": "{invalid json"}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertIsNone(run.severity_data)
        self.assertIsNone(run.total_burned_ha)

    def test_save_analysis_run_severity_without_total_burned(self):
        severity = {"High": {"area_ha": 5.0}}
        result = {"severity_map": severity}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertEqual(run.severity_data, severity)
        self.assertIsNone(run.total_burned_ha)

    # -- image storage ---------------------------------------------------------

    @patch("wildfire_assessment.svc.area_of_interest.upload_image_to_s3")
    @patch("wildfire_assessment.svc.area_of_interest.requests.get")
    def test_save_analysis_run_downloads_and_stores_images(self, mock_get, mock_upload):
        mock_response = MagicMock()
        mock_response.content = b"\xff\xd8image-data"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = {
            "severity_map": '{"Total Burned Area": {"area_ha": 42.5}}',
            "rgb_pre_fire_visual_jpg": "http://example.com/pre.jpg",
            "rgb_post_fire_visual_jpg": "http://example.com/post.jpg",
            "dndvi_visual_jpg": "http://example.com/dndvi.jpg",
            "dnbr_visual_jpg": "http://example.com/dnbr.jpg",
            "rbr_visual_jpg": "http://example.com/rbr.jpg",
        }

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertEqual(mock_get.call_count, 5)
        self.assertEqual(mock_upload.call_count, 5)
        self.assertIsNotNone(run.rgb_pre_fire_image)
        self.assertIsNotNone(run.rgb_post_fire_image)
        self.assertTrue(run.rgb_pre_fire_image.endswith("/pre_fire_rgb.jpg"))

    def test_save_analysis_run_without_image_urls(self):
        result = {"severity_map": '{"Total Burned Area": {"area_ha": 10.0}}'}

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertIsNone(run.rgb_pre_fire_image)
        self.assertIsNone(run.rbr_image)

    @patch("wildfire_assessment.svc.area_of_interest.upload_image_to_s3")
    @patch("wildfire_assessment.svc.area_of_interest.requests.get")
    def test_save_analysis_run_image_download_failure(self, mock_get, mock_upload):
        mock_get.side_effect = Exception("Network error")

        result = {
            "severity_map": '{"Total Burned Area": {"area_ha": 10.0}}',
            "rgb_pre_fire_visual_jpg": "http://example.com/pre.jpg",
        }

        run = aoi_service.save_analysis_run(
            self.user, self.area, "2024-01-01", "2024-01-15", result
        )

        self.assertIsNone(run.rgb_pre_fire_image)
        mock_upload.assert_not_called()

    # -- delete_polygon_file with S3 ------------------------------------------

    @patch("wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3")
    def test_delete_polygon_file_calls_s3(self, mock_delete):
        mock_delete.return_value = True
        result = aoi_service.delete_polygon_file("test.geojson")
        self.assertTrue(result)
        mock_delete.assert_called_once_with("test.geojson")

    @patch("wildfire_assessment.svc.area_of_interest.delete_polygon_from_s3")
    def test_delete_polygon_file_s3_failure(self, mock_delete):
        mock_delete.return_value = False
        result = aoi_service.delete_polygon_file("test.geojson")
        self.assertFalse(result)


class S3PolygonTests(TestCase):
    """Tests for S3 polygon upload/download/delete functions."""

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_upload_polygon_to_s3(self, mock_session):
        client = MagicMock()
        mock_session.return_value.client.return_value = client
        geojson = {"type": "Polygon", "coordinates": []}

        aws.upload_polygon_to_s3("test.geojson", geojson)

        client.put_object.assert_called_once()
        call_kwargs = client.put_object.call_args.kwargs
        self.assertEqual(call_kwargs["Key"], "polygons/test.geojson")
        self.assertEqual(call_kwargs["ContentType"], "application/json")

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_upload_polygon_to_s3_with_string_data(self, mock_session):
        client = MagicMock()
        mock_session.return_value.client.return_value = client

        aws.upload_polygon_to_s3("test.geojson", '{"type": "Polygon"}')

        client.put_object.assert_called_once()
        call_kwargs = client.put_object.call_args.kwargs
        self.assertEqual(call_kwargs["Body"], '{"type": "Polygon"}')

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_download_polygon_from_s3(self, mock_session):
        client = MagicMock()
        mock_session.return_value.client.return_value = client
        body_mock = MagicMock()
        body_mock.read.return_value = b'{"type": "Polygon"}'
        client.get_object.return_value = {"Body": body_mock}

        content = aws.download_polygon_from_s3("test.geojson")

        self.assertEqual(content, '{"type": "Polygon"}')
        client.get_object.assert_called_once()
        call_kwargs = client.get_object.call_args.kwargs
        self.assertEqual(call_kwargs["Key"], "polygons/test.geojson")

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_delete_polygon_from_s3_success(self, mock_session):
        client = MagicMock()
        mock_session.return_value.client.return_value = client

        result = aws.delete_polygon_from_s3("test.geojson")

        self.assertTrue(result)
        client.delete_object.assert_called_once()
        call_kwargs = client.delete_object.call_args.kwargs
        self.assertEqual(call_kwargs["Key"], "polygons/test.geojson")

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_delete_polygon_from_s3_failure(self, mock_session):
        client = MagicMock()
        client.delete_object.side_effect = Exception("S3 error")
        mock_session.return_value.client.return_value = client

        result = aws.delete_polygon_from_s3("test.geojson")

        self.assertFalse(result)


class S3ImageTests(TestCase):
    """Tests for S3 image upload and pre-signed URL functions."""

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_upload_image_to_s3(self, mock_session):
        client = MagicMock()
        mock_session.return_value.client.return_value = client

        aws.upload_image_to_s3("run123/pre_fire_rgb.jpg", b"\xff\xd8image")

        client.put_object.assert_called_once()
        call_kwargs = client.put_object.call_args.kwargs
        self.assertEqual(call_kwargs["Key"], "images/run123/pre_fire_rgb.jpg")
        self.assertEqual(call_kwargs["ContentType"], "image/jpeg")
        self.assertEqual(call_kwargs["Body"], b"\xff\xd8image")

    @patch("wildfire_assessment.svc.aws.get_boto3_session")
    def test_get_presigned_image_url(self, mock_session):
        client = MagicMock()
        client.generate_presigned_url.return_value = "https://s3.example.com/signed"
        mock_session.return_value.client.return_value = client

        url = aws.get_presigned_image_url("run123/pre_fire_rgb.jpg")

        self.assertEqual(url, "https://s3.example.com/signed")
        client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={
                "Bucket": mock_session.return_value.client.return_value
                and aws.settings.S3_BUCKET_NAME,
                "Key": "images/run123/pre_fire_rgb.jpg",
            },
            ExpiresIn=3600,
        )


class AnalyticsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="analyst", email="analyst@example.com", password="pw"
        )
        self.user2 = User.objects.create_user(
            username="analyst2", email="analyst2@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Analytics Country", code="AN")
        self.area = AreaOfInterest.objects.create(
            name="Analytics Area", polygon_path="a.geojson", country=self.country
        )
        self.area2 = AreaOfInterest.objects.create(
            name="Analytics Area 2", polygon_path="b.geojson", country=self.country
        )
        self.run1 = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-06-01",
            post_fire_date="2024-06-15",
            total_burned_ha=100.0,
            status="completed",
        )
        self.run2 = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area2,
            pre_fire_date="2024-07-01",
            post_fire_date="2024-07-15",
            total_burned_ha=50.5,
            status="completed",
        )
        self.run3 = AnalysisRun.objects.create(
            user=self.user2,
            area_of_interest=self.area,
            pre_fire_date="2024-08-01",
            post_fire_date="2024-08-15",
            total_burned_ha=200.0,
            status="completed",
        )

    def test_get_analytics_summary(self):
        summary = analytics.get_analytics_summary()
        self.assertEqual(summary["total_analyses"], 3)
        self.assertEqual(summary["total_users"], 2)
        self.assertEqual(float(summary["total_burned_ha"]), 350.5)
        self.assertEqual(summary["total_areas_analyzed"], 2)

    def test_get_analytics_summary_empty(self):
        AnalysisRun.objects.all().delete()
        summary = analytics.get_analytics_summary()
        self.assertEqual(summary["total_analyses"], 0)
        self.assertEqual(summary["total_users"], 0)
        self.assertIsNone(summary["total_burned_ha"])

    def test_get_user_stats(self):
        stats = analytics.get_user_stats()
        self.assertEqual(len(stats), 2)
        # First user has 2 analyses (ordered by -analysis_count)
        top_user = stats[0]
        self.assertEqual(top_user["analysis_count"], 2)
        self.assertEqual(top_user["areas_analyzed"], 2)

    def test_get_monthly_stats(self):
        stats = analytics.get_monthly_stats()
        self.assertIsInstance(stats, list)
        # Results are now per month+user
        if stats:
            self.assertIn("user__email", stats[0])

    def test_get_top_areas(self):
        areas = analytics.get_top_areas(limit=10)
        # Now grouped by area+user: user1 has area+area2, user2 has area = 3 rows
        self.assertEqual(len(areas), 3)
        self.assertIn("user__email", areas[0])

    def test_get_daily_run_counts(self):
        counts = analytics.get_daily_run_counts()
        self.assertIsInstance(counts, list)
        # All 3 runs were created today so expect 1 day entry
        self.assertEqual(len(counts), 1)
        self.assertEqual(counts[0]["count"], 3)
        self.assertIn("day", counts[0])

    def test_get_daily_run_counts_empty(self):
        AnalysisRun.objects.all().delete()
        counts = analytics.get_daily_run_counts()
        self.assertEqual(counts, [])

    def test_get_recent_analyses(self):
        recent = analytics.get_recent_analyses(limit=2)
        self.assertEqual(len(recent), 2)
        # Most recent first
        self.assertEqual(recent[0]["user__email"], "analyst2@example.com")


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dashuser", email="dash@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Dash Country", code="DC")
        UserCountry.objects.create(user=self.user, country=self.country)
        self.area = AreaOfInterest.objects.create(
            name="Dash Area", polygon_path="d.geojson", country=self.country
        )

    def test_totals_sum_all_user_runs(self):
        """All runs by the user should be summed."""
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={
                "Total Area": {"area_ha": 500.0},
                "Total Burned Area": {"area_ha": 50.0},
            },
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={
                "Total Area": {"area_ha": 999.0},
                "Total Burned Area": {"area_ha": 999.0},
            },
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(float(stats["total_analyzed_ha"]), 1499.0)
        self.assertEqual(float(stats["total_burned_ha"]), 1049.0)

    def test_totals_missing_severity_key(self):
        """Run with severity_data that lacks the expected key."""
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            severity_data={"Unburned": {"area_ha": 100.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertIsNone(stats["total_analyzed_ha"])
        self.assertIsNone(stats["total_burned_ha"])

    def test_totals_non_dict_severity(self):
        """Run with non-dict severity_data."""
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-03-01",
            post_fire_date="2024-03-15",
            severity_data="not a dict",
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertIsNone(stats["total_analyzed_ha"])

    def test_severity_breakdown_aggregates_across_runs(self):
        """severity_breakdown sums area_ha per severity class across all runs."""
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={
                "Unburned": {"area_ha": 100.0},
                "Low Severity": {"area_ha": 50.0},
                "High Severity": {"area_ha": 20.0},
            },
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            severity_data={
                "Unburned": {"area_ha": 200.0},
                "High Severity": {"area_ha": 40.0},
            },
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        breakdown = {
            item["label"]: float(item["area_ha"])
            for item in stats["severity_breakdown"]
        }
        self.assertEqual(breakdown["Unburned"], 300.0)
        self.assertEqual(breakdown["High Severity"], 60.0)
        self.assertEqual(breakdown["Low Severity"], 50.0)

    def test_severity_breakdown_empty(self):
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(stats["severity_breakdown"], [])

    def test_area_comparison(self):
        area2 = AreaOfInterest.objects.create(
            name="Area2", polygon_path="d2.geojson", country=self.country
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 100.0}},
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=area2,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 200.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        comparison = stats["area_comparison"]
        self.assertEqual(len(comparison), 2)
        self.assertEqual(comparison[0]["area_name"], "Area2")
        self.assertEqual(float(comparison[0]["total_burned_ha"]), 200.0)

    def test_average_burn_severity(self):
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={
                "Unburned": {"area_ha": 50.0},
                "High Severity": {"area_ha": 50.0},
            },
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        # (0*50 + 3*50) / (50+50) = 1.50
        self.assertEqual(float(stats["average_burn_severity"]), 1.50)

    def test_average_burn_severity_none_when_no_data(self):
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertIsNone(stats["average_burn_severity"])

    def test_most_analyzed_area(self):
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(
            stats["most_analyzed_area"]["area_name"], "Dash Area"
        )
        self.assertEqual(stats["most_analyzed_area"]["run_count"], 2)

    def test_most_analyzed_area_none_when_empty(self):
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertIsNone(stats["most_analyzed_area"])

    def test_largest_fire(self):
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 50.0}},
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            severity_data={"Total Burned Area": {"area_ha": 500.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(stats["largest_fire"]["area_name"], "Dash Area")
        self.assertEqual(float(stats["largest_fire"]["burned_ha"]), 500.0)

    def test_largest_fire_none_when_empty(self):
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertIsNone(stats["largest_fire"])
