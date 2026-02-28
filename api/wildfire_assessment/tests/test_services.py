import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_assessment.models import (
    AnalysisRun,
    AreaOfInterest,
    Country,
    Notification,
    UserCountry,
    UserProfile,
)
from wildfire_assessment.svc import analytics
from wildfire_assessment.svc import area_of_interest as aoi_service
from wildfire_assessment.svc import aws
from wildfire_assessment.svc import dashboard as dashboard_service
from wildfire_assessment.svc import notification as notification_service
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
            user_id=user.id,
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
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_missing_statuses(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_unlink,
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
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_unlink,
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
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send,
        mock_unlink,
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
    def setUp(self):
        self.pre_fire_date = "2024-01-01"
        self.post_fire_date = "2024-01-15"
        self.polygon_path = "test-polygon.geojson"
        self.email = "test@example.com"
        self.reserve_name = "Test Reserve"

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

    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_get_gee_private_key_json_control_characters(self, mock_secret):
        """Literal newlines in the private key are re-escaped for valid JSON."""
        # Simulate what happens when Secrets Manager stores the GEE JSON as a
        # nested string: the inner \\n becomes literal \n after outer json.loads().
        inner = '{"type":"service_account","private_key":"-----BEGIN-----\\nKEY\\n-----END-----\\n"}'
        parsed_inner = json.loads(inner)  # private_key now has literal \n
        raw_with_newlines = json.dumps(parsed_inner)  # properly escaped
        # Break it by replacing \\n with real newlines (simulating the bug)
        broken = raw_with_newlines.replace("\\n", "\n")
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": broken})
        result = processor.get_gee_private_key_json()
        parsed = json.loads(result)
        self.assertEqual(parsed["type"], "service_account")
        self.assertIn("BEGIN", parsed["private_key"])

    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_get_gee_private_key_json_dict_value(self, mock_secret):
        """Test when GEE_PRIVATE_KEY_JSON is already a dict (not a string)."""
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": {"key": "value"}}
        )
        result = processor.get_gee_private_key_json()
        self.assertEqual(result, {"key": "value"})

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_updates_analysis_run(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Test that analysis_run_id triggers DB update with URL and task ID clearance."""
        user = User.objects.create_user(
            username="runuser", email=self.email, password="pw"
        )
        country = Country.objects.create(name="Run Country", code="RN")
        area = AreaOfInterest.objects.create(
            name="Run Area", polygon_path="run.geojson", country=country
        )
        analysis_run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_task_id="old-task-id",
        )

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        result_status = processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
            analysis_run_id=analysis_run.id,
        )

        self.assertEqual(result_status, "COMPLETED")
        analysis_run.refresh_from_db()
        self.assertEqual(analysis_run.scientific_dnbr_url, "http://files/dnbr.tif")
        self.assertIsNone(analysis_run.scientific_dnbr_task_id)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_db_update_failure(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Test that DB update failure is handled gracefully."""
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        with patch.object(AnalysisRun.objects, "filter") as mock_filter:
            mock_filter.return_value.update.side_effect = Exception("DB error")
            result_status = processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name=Deliverable.DNBR.name,
                email=self.email,
                reserve_name=self.reserve_name,
                analysis_run_id=999,
            )
        # Should still complete despite DB error
        self.assertEqual(result_status, "COMPLETED")

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_creates_notification(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Test that a Notification record is created when deliverable completes."""
        User = get_user_model()
        user = User.objects.create_user(
            username="notifuser", email=self.email, password="pw"
        )
        country = Country.objects.create(name="Notif Country", code="NF")
        area = AreaOfInterest.objects.create(
            name="Notif Area", polygon_path="notif.geojson", country=country
        )
        analysis_run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        self.assertEqual(Notification.objects.count(), 0)

        processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
            analysis_run_id=analysis_run.id,
            user_id=user.id,
        )

        self.assertEqual(Notification.objects.count(), 1)
        notif = Notification.objects.first()
        self.assertEqual(notif.user, user)
        self.assertEqual(notif.analysis_run, analysis_run)
        self.assertEqual(notif.notification_type, "deliverable_ready")
        self.assertEqual(notif.deliverable_name, "DNBR")
        self.assertIn("Notif Area", notif.message)
        self.assertFalse(notif.is_read)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_push_notification")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_sends_push_notification(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_send_push,
        mock_unlink,
    ):
        """Push notification is sent alongside in-app notification."""
        user = User.objects.create_user(
            username="pushuser", email=self.email, password="pw"
        )
        country = Country.objects.create(name="Push Country", code="PC")
        area = AreaOfInterest.objects.create(
            name="Push Area", polygon_path="push.geojson", country=country
        )
        analysis_run = AnalysisRun.objects.create(
            user=user,
            area_of_interest=area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
            analysis_run_id=analysis_run.id,
            user_id=user.id,
        )

        mock_send_push.assert_called_once_with(
            user_id=user.id,
            title="Deliverable Ready",
            body=f"Scientific DNBR deliverable for Push Area is ready to download.",
            data={"analysis_run_id": analysis_run.id},
        )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_no_notification_without_run_id(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """No notification is created when analysis_run_id is not provided."""
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        processor.process_scientific_deliverable(
            pre_fire_date=self.pre_fire_date,
            post_fire_date=self.post_fire_date,
            polygon_path=self.polygon_path,
            deliverable_name=Deliverable.DNBR.name,
            email=self.email,
            reserve_name=self.reserve_name,
        )

        self.assertEqual(Notification.objects.count(), 0)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_notification_creation_failure(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Notification creation failure is handled gracefully."""
        User = get_user_model()
        user = User.objects.create_user(
            username="failnotif", email=self.email, password="pw"
        )

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        with patch("wildfire_assessment.svc.processor.Notification") as mock_notif:
            mock_notif.objects.create.side_effect = Exception("DB error")
            result = processor.process_scientific_deliverable(
                pre_fire_date=self.pre_fire_date,
                post_fire_date=self.post_fire_date,
                polygon_path=self.polygon_path,
                deliverable_name=Deliverable.DNBR.name,
                email=self.email,
                reserve_name=self.reserve_name,
                analysis_run_id=999,
                user_id=user.id,
            )

        self.assertEqual(result, "COMPLETED")


class ProcessorCacheInvalidationTests(TestCase):
    """Tests for dashboard cache invalidation in processor."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.user = User.objects.create_user(
            username="cacheproc", email="cacheproc@example.com", password="pw"
        )
        self.country = Country.objects.create(name="CacheProc Country", code="CP")
        self.area = AreaOfInterest.objects.create(
            name="CacheProc Area",
            polygon_path="cacheproc.geojson",
            country=self.country,
        )
        self.analysis_run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
        )

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_successful_deliverable_invalidates_dashboard_cache(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Successful deliverable completion clears the user's dashboard cache."""
        from django.core.cache import cache

        cache.set(f"dashboard_{self.user.id}", {"cached": True}, timeout=60)
        self.assertIsNotNone(cache.get(f"dashboard_{self.user.id}"))

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        processor.process_scientific_deliverable(
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            polygon_path="cacheproc.geojson",
            deliverable_name=Deliverable.DNBR.name,
            email="cacheproc@example.com",
            reserve_name="CacheProc Reserve",
            analysis_run_id=self.analysis_run.id,
            user_id=self.user.id,
        )

        self.assertIsNone(cache.get(f"dashboard_{self.user.id}"))

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_successful_deliverable_without_user_id_does_not_invalidate(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
        mock_unlink,
    ):
        """Without user_id, dashboard cache is not invalidated."""
        from django.core.cache import cache

        cache.set(f"dashboard_{self.user.id}", {"cached": True}, timeout=60)

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {
                "DNBR": {"gee_task_id": "task-1", "url": "http://files/dnbr.tif"}
            }
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [{"state": "COMPLETED"}]

        processor.process_scientific_deliverable(
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            polygon_path="cacheproc.geojson",
            deliverable_name=Deliverable.DNBR.name,
            email="cacheproc@example.com",
            reserve_name="CacheProc Reserve",
        )

        # Cache should still exist since no user_id was provided
        self.assertIsNotNone(cache.get(f"dashboard_{self.user.id}"))


class ProcessorErrorPersistenceTests(TestCase):
    """Tests for error persistence when scientific deliverable tasks fail."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="erruser", email="err@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Err Country", code="ER")
        self.area = AreaOfInterest.objects.create(
            name="Err Area",
            polygon_path="err.geojson",
            country=self.country,
        )
        self.analysis_run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            scientific_dnbr_task_id="old-task-id",
        )
        self.base_kwargs = {
            "pre_fire_date": "2024-01-01",
            "post_fire_date": "2024-01-15",
            "polygon_path": "err.geojson",
            "deliverable_name": Deliverable.DNBR.name,
            "email": "err@example.com",
            "reserve_name": "Err Reserve",
            "analysis_run_id": None,  # set per test
        }

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_gee_failure_persists_error(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_unlink,
    ):
        """GEE FAILED state persists error and clears task_id."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [
            {"state": "FAILED", "error_message": "GEE computation error"}
        ]

        with self.assertRaises(RuntimeError):
            processor.process_scientific_deliverable(
                **{**self.base_kwargs, "analysis_run_id": self.analysis_run.id}
            )

        self.analysis_run.refresh_from_db()
        self.assertIsNotNone(self.analysis_run.scientific_dnbr_error)
        self.assertIn("GEE computation error", self.analysis_run.scientific_dnbr_error)
        self.assertIn("GEE task FAILED", self.analysis_run.scientific_dnbr_error)
        self.assertIsNone(self.analysis_run.scientific_dnbr_task_id)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_gee_cancelled_state_persists_error(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_unlink,
    ):
        """GEE CANCELLED state persists error and clears task_id."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [
            {"state": "CANCELLED", "error_message": "Task was cancelled"}
        ]

        with self.assertRaises(RuntimeError) as ctx:
            processor.process_scientific_deliverable(
                **{**self.base_kwargs, "analysis_run_id": self.analysis_run.id}
            )

        self.assertIn("GEE task CANCELLED", str(ctx.exception))
        self.analysis_run.refresh_from_db()
        self.assertIsNotNone(self.analysis_run.scientific_dnbr_error)
        self.assertIn("CANCELLED", self.analysis_run.scientific_dnbr_error)
        self.assertIsNone(self.analysis_run.scientific_dnbr_task_id)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_unexpected_gee_state_persists_error(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_unlink,
    ):
        """Unexpected GEE state persists error and clears task_id."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.return_value = {
            "scientific": {"DNBR": {"gee_task_id": "task-1", "url": ""}}
        }
        mock_assessment.return_value = assessment_instance
        mock_ee.data.getTaskStatus.return_value = [
            {"state": "SOME_UNKNOWN_STATE"}
        ]

        with self.assertRaises(RuntimeError) as ctx:
            processor.process_scientific_deliverable(
                **{**self.base_kwargs, "analysis_run_id": self.analysis_run.id}
            )

        self.assertIn("GEE task SOME_UNKNOWN_STATE", str(ctx.exception))
        self.assertIn("Unknown error", str(ctx.exception))
        self.analysis_run.refresh_from_db()
        self.assertIsNotNone(self.analysis_run.scientific_dnbr_error)
        self.assertIn("SOME_UNKNOWN_STATE", self.analysis_run.scientific_dnbr_error)
        self.assertIsNone(self.analysis_run.scientific_dnbr_task_id)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_generic_exception_persists_error(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_unlink,
    ):
        """Generic exception during run() persists error and clears task_id."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.side_effect = RuntimeError("PostFireAssessment crash")
        mock_assessment.return_value = assessment_instance

        with self.assertRaises(RuntimeError):
            processor.process_scientific_deliverable(
                **{**self.base_kwargs, "analysis_run_id": self.analysis_run.id}
            )

        self.analysis_run.refresh_from_db()
        self.assertIsNotNone(self.analysis_run.scientific_dnbr_error)
        self.assertIn(
            "PostFireAssessment crash", self.analysis_run.scientific_dnbr_error
        )
        self.assertIsNone(self.analysis_run.scientific_dnbr_task_id)

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_error_without_analysis_run_id_does_not_fail(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_unlink,
    ):
        """Error without analysis_run_id should not try to persist."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.side_effect = RuntimeError("boom")
        mock_assessment.return_value = assessment_instance

        with self.assertRaises(RuntimeError):
            processor.process_scientific_deliverable(
                **{**self.base_kwargs, "analysis_run_id": None}
            )

    @patch("wildfire_assessment.svc.processor.os.unlink")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.download_polygon_from_s3")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_error_persistence_db_failure_still_raises(
        self,
        mock_secret,
        mock_download,
        mock_assessment,
        mock_unlink,
    ):
        """If DB update in error handler fails, original exception is still raised."""
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
        mock_download.return_value = '{"type": "Polygon"}'
        assessment_instance = MagicMock()
        assessment_instance.run.side_effect = RuntimeError("original error")
        mock_assessment.return_value = assessment_instance

        with patch.object(AnalysisRun.objects, "filter") as mock_filter:
            mock_filter.return_value.update.side_effect = Exception("DB down")
            with self.assertRaises(RuntimeError) as ctx:
                processor.process_scientific_deliverable(
                    **{
                        **self.base_kwargs,
                        "analysis_run_id": self.analysis_run.id,
                    }
                )
            self.assertIn("original error", str(ctx.exception))


class CleanupStaleDeliverablesTests(TestCase):
    """Tests for the cleanup_stale_deliverables periodic task."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="cleanupuser", email="cleanup@example.com", password="pw"
        )
        self.country = Country.objects.create(name="Cleanup Country", code="CL")
        self.area = AreaOfInterest.objects.create(
            name="Cleanup Area",
            polygon_path="cleanup.geojson",
            country=self.country,
        )

    def _create_run(self, completed_minutes_ago=60, **kwargs):
        run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            status="completed",
            **kwargs,
        )
        # Override auto_now_add completed_at
        completed_at = timezone.now() - timedelta(minutes=completed_minutes_ago)
        AnalysisRun.objects.filter(id=run.id).update(completed_at=completed_at)
        run.refresh_from_db()
        return run

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_failed_task(self, mock_async_cls):
        """FAILURE state: persist error from result, clear task_id."""
        run = self._create_run(
            scientific_dnbr_task_id="celery-task-1",
        )
        mock_result = SimpleNamespace(state="FAILURE", result=RuntimeError("Task boom"))
        mock_async_cls.return_value = mock_result

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertIsNone(run.scientific_dnbr_task_id)
        self.assertIsNotNone(run.scientific_dnbr_error)
        self.assertIn("Task boom", run.scientific_dnbr_error)

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_pending_task(self, mock_async_cls):
        """PENDING state: task is gone (container killed, etc.) → mark as error."""
        run = self._create_run(
            scientific_rgb_pre_fire_task_id="celery-task-2",
        )
        mock_result = SimpleNamespace(state="PENDING", result=None)
        mock_async_cls.return_value = mock_result

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertIsNone(run.scientific_rgb_pre_fire_task_id)
        self.assertIsNotNone(run.scientific_rgb_pre_fire_error)
        self.assertIn("no longer running", run.scientific_rgb_pre_fire_error)

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_started_task_left_alone(self, mock_async_cls):
        """STARTED state: task is still running, do not clean up."""
        run = self._create_run(
            scientific_dndvi_task_id="celery-task-3",
        )
        mock_result = SimpleNamespace(state="STARTED", result=None)
        mock_async_cls.return_value = mock_result

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertEqual(run.scientific_dndvi_task_id, "celery-task-3")
        self.assertIsNone(run.scientific_dndvi_error)

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_skips_recent_runs(self, mock_async_cls):
        """Runs completed less than 30 minutes ago are skipped."""
        run = self._create_run(
            completed_minutes_ago=10,
            scientific_dnbr_task_id="celery-task-4",
        )
        mock_async_cls.return_value = SimpleNamespace(state="PENDING", result=None)

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        # Should NOT have been cleaned up
        self.assertEqual(run.scientific_dnbr_task_id, "celery-task-4")
        self.assertIsNone(run.scientific_dnbr_error)

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_multiple_deliverables(self, mock_async_cls):
        """Multiple stale deliverables on same run are all cleaned up."""
        run = self._create_run(
            scientific_dnbr_task_id="task-a",
            scientific_rbr_task_id="task-b",
        )

        def mock_async(task_id):
            if task_id == "task-a":
                return SimpleNamespace(state="FAILURE", result=RuntimeError("A failed"))
            return SimpleNamespace(state="PENDING", result=None)

        mock_async_cls.side_effect = mock_async

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertIsNone(run.scientific_dnbr_task_id)
        self.assertIn("A failed", run.scientific_dnbr_error)
        self.assertIsNone(run.scientific_rbr_task_id)
        self.assertIn("no longer running", run.scientific_rbr_error)

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_failure_no_result(self, mock_async_cls):
        """FAILURE state with no result uses fallback error message."""
        run = self._create_run(
            scientific_dnbr_task_id="celery-task-5",
        )
        mock_result = SimpleNamespace(state="FAILURE", result=None)
        mock_async_cls.return_value = mock_result

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertIsNone(run.scientific_dnbr_task_id)
        self.assertEqual(run.scientific_dnbr_error, "Task failed")

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_db_error_handled_gracefully(self, mock_async_cls):
        """DB update failure during cleanup is handled gracefully."""
        run = self._create_run(
            scientific_dnbr_task_id="celery-task-6",
        )
        mock_async_cls.return_value = SimpleNamespace(
            state="FAILURE", result=RuntimeError("boom")
        )

        with patch.object(AnalysisRun.objects, "filter") as mock_filter:
            # First call for the queryset, second for the update
            real_filter = AnalysisRun.objects.__class__.filter

            call_count = [0]

            def side_effect(*args, **kwargs):
                call_count[0] += 1
                qs = real_filter(AnalysisRun.objects, *args, **kwargs)
                if call_count[0] > 1:
                    # The update call inside cleanup
                    mock_qs = MagicMock()
                    mock_qs.update.side_effect = Exception("DB down")
                    return mock_qs
                return qs

            mock_filter.side_effect = side_effect

            # Should not raise
            processor.cleanup_stale_deliverables()

    @patch("wildfire_assessment.svc.processor.AsyncResult")
    def test_cleanup_skips_non_completed_runs(self, mock_async_cls):
        """Runs with status != 'completed' are not cleaned up."""
        run = AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            status="running",
            scientific_dnbr_task_id="celery-task-7",
        )
        AnalysisRun.objects.filter(id=run.id).update(
            completed_at=timezone.now() - timedelta(minutes=60)
        )
        mock_async_cls.return_value = SimpleNamespace(state="PENDING", result=None)

        processor.cleanup_stale_deliverables()

        run.refresh_from_db()
        self.assertEqual(run.scientific_dnbr_task_id, "celery-task-7")
        self.assertIsNone(run.scientific_dnbr_error)


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

    # -- get_area_geojson -----------------------------------------------------

    def test_get_area_geojson_empty_path(self):
        """Test that empty polygon path returns None."""
        result = aoi_service.get_area_geojson("")
        self.assertIsNone(result)

    def test_get_area_geojson_none_path(self):
        """Test that None polygon path returns None."""
        result = aoi_service.get_area_geojson(None)
        self.assertIsNone(result)

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon_from_s3")
    def test_get_area_geojson_success(self, mock_download):
        """Test successful geojson download and parsing."""
        mock_download.return_value = '{"type": "Polygon", "coordinates": []}'
        result = aoi_service.get_area_geojson("test.geojson")
        self.assertEqual(result, {"type": "Polygon", "coordinates": []})

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon_from_s3")
    def test_get_area_geojson_s3_failure(self, mock_download):
        """Test that S3 download failure returns None."""
        mock_download.side_effect = Exception("S3 error")
        result = aoi_service.get_area_geojson("test.geojson")
        self.assertIsNone(result)

    @patch("wildfire_assessment.svc.area_of_interest.download_polygon_from_s3")
    def test_get_area_geojson_invalid_json(self, mock_download):
        """Test that invalid JSON returns None."""
        mock_download.return_value = "not valid json"
        result = aoi_service.get_area_geojson("test.geojson")
        self.assertIsNone(result)


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

    def test_get_user_analysis_counts_no_filter(self):
        counts = analytics.get_user_analysis_counts()
        self.assertEqual(len(counts), 2)
        top = counts[0]
        self.assertEqual(top["analysis_count"], 2)
        self.assertIn("user__first_name", top)
        self.assertIn("user__last_name", top)

    def test_get_user_analysis_counts_with_date_range(self):
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        yesterday = date.today() - timedelta(days=1)
        counts = analytics.get_user_analysis_counts(
            start_date=yesterday, end_date=tomorrow
        )
        self.assertEqual(len(counts), 2)

    def test_get_user_analysis_counts_excludes_outside_range(self):
        from datetime import date, timedelta

        future = date.today() + timedelta(days=10)
        counts = analytics.get_user_analysis_counts(start_date=future, end_date=future)
        self.assertEqual(len(counts), 0)

    def test_get_user_analysis_counts_empty(self):
        AnalysisRun.objects.all().delete()
        counts = analytics.get_user_analysis_counts()
        self.assertEqual(counts, [])


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
        self.assertEqual(stats["most_analyzed_area"]["area_name"], "Dash Area")
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

    def test_severity_trend(self):
        """Test severity_trend returns per-run weighted severity with ISO timestamps."""
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
        trend = stats["severity_trend"]
        self.assertIsInstance(trend, list)
        self.assertGreaterEqual(len(trend), 1)
        self.assertIn("created_at", trend[0])
        self.assertIn("avg_severity", trend[0])
        # (0*50 + 3*50) / (50+50) = 1.50
        self.assertEqual(trend[0]["avg_severity"], 1.50)

    def test_severity_trend_empty(self):
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(stats["severity_trend"], [])

    def test_severity_trend_skips_non_dict_data(self):
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data="not a dict",
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(stats["severity_trend"], [])

    def test_areas_geo_with_centroid(self):
        """Test _areas_geo returns geo data for areas with centroids.

        Note: geometry is no longer included in dashboard response;
        it's now lazy-loaded via the /area_of_interest/{id}/geojson/ endpoint.
        """
        self.area.centroid_lat = -15.5
        self.area.centroid_lng = -47.8
        self.area.save()
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 100.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        geo = stats["areas_geo"]
        self.assertEqual(len(geo), 1)
        self.assertEqual(geo[0]["name"], "Dash Area")
        self.assertEqual(geo[0]["lat"], -15.5)
        self.assertEqual(geo[0]["lng"], -47.8)
        self.assertEqual(geo[0]["total_burned_ha"], 100.0)
        self.assertEqual(geo[0]["run_count"], 1)
        # Geometry is now lazy-loaded, not included in dashboard response
        self.assertIsNone(geo[0]["geometry"])

    def test_areas_geo_skips_area_without_centroid(self):
        """Test that areas without centroids are excluded."""
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 100.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        self.assertEqual(stats["areas_geo"], [])

    def test_areas_geo_geometry_is_none(self):
        """Test that geometry is None in dashboard (lazy-loaded via separate endpoint)."""
        self.area.centroid_lat = -15.5
        self.area.centroid_lng = -47.8
        self.area.save()
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 100.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        geo = stats["areas_geo"]
        self.assertEqual(len(geo), 1)
        # Geometry is lazy-loaded via /area_of_interest/{id}/geojson/
        self.assertIsNone(geo[0]["geometry"])

    def test_areas_geo_multiple_runs_same_area(self):
        """Test aggregation across multiple runs for the same area."""
        self.area.centroid_lat = -15.5
        self.area.centroid_lng = -47.8
        self.area.save()
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 100.0}},
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=self.area,
            pre_fire_date="2024-02-01",
            post_fire_date="2024-02-15",
            severity_data={"Total Burned Area": {"area_ha": 200.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        geo = stats["areas_geo"]
        self.assertEqual(len(geo), 1)
        self.assertEqual(geo[0]["total_burned_ha"], 300.0)
        self.assertEqual(geo[0]["run_count"], 2)
        # Geometry is lazy-loaded via /area_of_interest/{id}/geojson/
        self.assertIsNone(geo[0]["geometry"])

    def test_areas_geo_empty_polygon_path(self):
        """Test that areas with empty polygon_path have null geometry."""
        area2 = AreaOfInterest.objects.create(
            name="No Path",
            polygon_path="",
            country=self.country,
            centroid_lat=-10.0,
            centroid_lng=-40.0,
        )
        AnalysisRun.objects.create(
            user=self.user,
            area_of_interest=area2,
            pre_fire_date="2024-01-01",
            post_fire_date="2024-01-15",
            severity_data={"Total Burned Area": {"area_ha": 50.0}},
        )
        stats = dashboard_service.get_dashboard_stats(self.user)
        geo = stats["areas_geo"]
        self.assertEqual(len(geo), 1)
        # Geometry is lazy-loaded via /area_of_interest/{id}/geojson/
        self.assertIsNone(geo[0]["geometry"])


class DashboardCacheInvalidationTests(TestCase):
    """Tests for invalidate_dashboard_cache helper."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def tearDown(self):
        from django.core.cache import cache

        cache.clear()

    def test_invalidate_dashboard_cache_clears_entry(self):
        from django.core.cache import cache

        cache.set("dashboard_42", {"total_analyses": 5}, timeout=60)
        self.assertIsNotNone(cache.get("dashboard_42"))

        dashboard_service.invalidate_dashboard_cache(42)
        self.assertIsNone(cache.get("dashboard_42"))

    def test_invalidate_dashboard_cache_noop_when_missing(self):
        """Calling invalidate on a non-existent key does not raise."""
        dashboard_service.invalidate_dashboard_cache(999)


class ExtractGeometryTests(TestCase):
    """Tests for _extract_geometry helper function."""

    def test_feature_collection(self):
        data = {
            "type": "FeatureCollection",
            "features": [{"geometry": {"type": "Polygon", "coordinates": []}}],
        }
        result = dashboard_service._extract_geometry(data)
        self.assertEqual(result["type"], "Polygon")

    def test_feature_collection_empty(self):
        data = {"type": "FeatureCollection", "features": []}
        result = dashboard_service._extract_geometry(data)
        self.assertIsNone(result)

    def test_feature(self):
        data = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}}
        result = dashboard_service._extract_geometry(data)
        self.assertEqual(result["type"], "Polygon")

    def test_bare_polygon(self):
        data = {"type": "Polygon", "coordinates": []}
        result = dashboard_service._extract_geometry(data)
        self.assertEqual(result, data)

    def test_bare_multipolygon(self):
        data = {"type": "MultiPolygon", "coordinates": []}
        result = dashboard_service._extract_geometry(data)
        self.assertEqual(result, data)

    def test_unsupported_type(self):
        data = {"type": "Point", "coordinates": [0, 0]}
        result = dashboard_service._extract_geometry(data)
        self.assertIsNone(result)

    def test_missing_type(self):
        data = {"coordinates": [0, 0]}
        result = dashboard_service._extract_geometry(data)
        self.assertIsNone(result)


class NotificationCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cleanup_user", password="pass")
        self.now = timezone.now()

    def _create_notification(self, is_read, age_hours):
        n = Notification.objects.create(
            user=self.user,
            message="test",
            is_read=is_read,
        )
        # Override auto_now_add by updating at DB level
        Notification.objects.filter(pk=n.pk).update(
            created_at=self.now - timedelta(hours=age_hours)
        )
        return n

    def test_deletes_old_read_notifications(self):
        old_read = self._create_notification(is_read=True, age_hours=25)
        deleted = notification_service.delete_old_read_notifications()
        self.assertEqual(deleted, 1)
        self.assertFalse(Notification.objects.filter(pk=old_read.pk).exists())

    def test_preserves_unread_notifications(self):
        old_unread = self._create_notification(is_read=False, age_hours=48)
        deleted = notification_service.delete_old_read_notifications()
        self.assertEqual(deleted, 0)
        self.assertTrue(Notification.objects.filter(pk=old_unread.pk).exists())

    def test_preserves_recent_read_notifications(self):
        recent_read = self._create_notification(is_read=True, age_hours=12)
        deleted = notification_service.delete_old_read_notifications()
        self.assertEqual(deleted, 0)
        self.assertTrue(Notification.objects.filter(pk=recent_read.pk).exists())

    def test_returns_correct_count(self):
        self._create_notification(is_read=True, age_hours=30)
        self._create_notification(is_read=True, age_hours=50)
        self._create_notification(is_read=True, age_hours=10)
        self._create_notification(is_read=False, age_hours=30)
        deleted = notification_service.delete_old_read_notifications()
        self.assertEqual(deleted, 2)
        self.assertEqual(Notification.objects.count(), 2)

    def test_shared_task_calls_service(self):
        self._create_notification(is_read=True, age_hours=25)
        result = notification_service.cleanup_old_read_notifications()
        self.assertEqual(result, 1)
        self.assertEqual(Notification.objects.count(), 0)


class SendPushNotificationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="push_user", email="push@example.com", password="pass"
        )
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.profile.expo_push_token = "ExponentPushToken[abc123]"
        self.profile.save()

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_success(self, mock_urlopen):
        notification_service.send_push_notification(
            user_id=self.user.id,
            title="Test Title",
            body="Test body message",
            data={"analysis_run_id": 42},
        )
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, notification_service.EXPO_PUSH_URL)
        self.assertEqual(req.method, "POST")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["to"], "ExponentPushToken[abc123]")
        self.assertEqual(payload["title"], "Test Title")
        self.assertEqual(payload["body"], "Test body message")
        self.assertEqual(payload["sound"], "default")
        self.assertEqual(payload["data"], {"analysis_run_id": 42})

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_no_data(self, mock_urlopen):
        notification_service.send_push_notification(
            user_id=self.user.id,
            title="Title",
            body="Body",
        )
        mock_urlopen.assert_called_once()
        payload = json.loads(mock_urlopen.call_args[0][0].data.decode("utf-8"))
        self.assertNotIn("data", payload)

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_no_token(self, mock_urlopen):
        self.profile.expo_push_token = None
        self.profile.save()
        notification_service.send_push_notification(
            user_id=self.user.id,
            title="Title",
            body="Body",
        )
        mock_urlopen.assert_not_called()

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_empty_token(self, mock_urlopen):
        self.profile.expo_push_token = ""
        self.profile.save()
        notification_service.send_push_notification(
            user_id=self.user.id,
            title="Title",
            body="Body",
        )
        mock_urlopen.assert_not_called()

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_no_profile(self, mock_urlopen):
        user2 = User.objects.create_user(
            username="noprofile", email="np@example.com", password="pass"
        )
        UserProfile.objects.filter(user=user2).delete()
        notification_service.send_push_notification(
            user_id=user2.id,
            title="Title",
            body="Body",
        )
        mock_urlopen.assert_not_called()

    @patch("wildfire_assessment.svc.notification.urllib.request.urlopen")
    def test_send_push_notification_http_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        # Should not raise — errors are swallowed
        notification_service.send_push_notification(
            user_id=self.user.id,
            title="Title",
            body="Body",
        )
