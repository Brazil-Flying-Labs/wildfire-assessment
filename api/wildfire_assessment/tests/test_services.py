import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from wildfire_analyser.fire_assessment.deliverables import Deliverable
from wildfire_assessment.models import UserProfile
from wildfire_assessment.svc import aws, processor

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

    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_fire_assessment_uses_visual_urls_when_available(
        self,
        mock_secret,
        mock_assessment,
    ):
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
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

        mock_assessment.assert_called_once()
        self.assertIn("severity_map", result)
        self.assertIn("rgb_pre_fire_visual_jpg", result)
        self.assertIn("rgb_post_fire_visual_jpg", result)
        self.assertIn("dndvi_visual_jpg", result)
        self.assertIn("dnbr_visual_jpg", result)
        self.assertIn("rbr_visual_jpg", result)

    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_notifies_user(
        self,
        mock_secret,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
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
        called_kwargs = mock_send_email.call_args.kwargs
        self.assertEqual(called_kwargs["to_address"], self.email)
        self.assertIn(self.reserve_name, called_kwargs["body"])

    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_uses_user_language_preference(
        self,
        mock_secret,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
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

    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    @patch("wildfire_assessment.svc.processor.UserProfile")
    def test_process_scientific_deliverable_falls_back_on_user_lookup_error(
        self,
        mock_profile_model,
        mock_secret,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        mock_send_email,
    ):
        """Test that email falls back to English when user lookup fails."""
        # Make UserProfile.objects.filter raise an exception
        mock_profile_model.objects.filter.side_effect = Exception("Database error")

        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
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

    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.Deliverable")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_unmapped_deliverable(
        self,
        mock_secret,
        mock_deliverable,
        mock_assessment,
        mock_ee,
        _mock_sleep,
        _mock_send,
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
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

    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_missing_statuses(
        self, mock_secret, mock_assessment, mock_ee, _mock_sleep
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
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

    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_failed_status(
        self, mock_secret, mock_assessment, mock_ee, _mock_sleep
    ):
        mock_secret.return_value = json.dumps({"GEE_PRIVATE_KEY_JSON": "{}"})
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

    @patch("wildfire_assessment.svc.processor.send_gmail_email")
    @patch("wildfire_assessment.svc.processor.time.sleep", return_value=None)
    @patch("wildfire_assessment.svc.processor.ee")
    @patch("wildfire_assessment.svc.processor.PostFireAssessment")
    @patch("wildfire_assessment.svc.processor.get_aws_secret_manager_secret")
    def test_process_scientific_deliverable_deliverable_keys(
        self, mock_secret, mock_assessment, mock_ee, _mock_sleep, mock_send
    ):
        mock_secret.return_value = json.dumps(
            {"GEE_PRIVATE_KEY_JSON": "{}", "GMAIL_PWD": "pwd"}
        )
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
