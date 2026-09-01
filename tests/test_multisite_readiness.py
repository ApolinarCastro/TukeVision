"""Phase 11 Test Suite: Sustained Production & Repeatable Multisite Readiness.

Validates deployment packaging, validation, isolation, operator routing,
maintenance windows, upgrades, backups, and multi-site E2E.
"""

import unittest
from datetime import datetime, timezone

from src.multisite.contract import (
    DEPLOYMENT_STATUS_ACTIVE,
    DEPLOYMENT_STATUS_VALIDATED,
    DRIFT_STATUS_DRIFT_DETECTED,
    DRIFT_STATUS_IN_SYNC,
    MAINTENANCE_STATUS_ACTIVE,
    MAINTENANCE_STATUS_COMPLETED,
    UPGRADE_STATUS_ROLLED_BACK,
    UPGRADE_STATUS_VERIFIED,
    VALIDATION_RESULT_INVALID,
    VALIDATION_RESULT_VALID,
    MaintenanceWindow,
    RepeatableDeploymentPackage,
    SiteDeploymentProfile,
    SiteTemplate,
    UpgradeRecord,
)
from src.multisite.service import (
    DeploymentValidator,
    MultiSiteDeploymentError,
    MultiSiteManager,
    MultiSiteSecurityError,
)


class TestRepeatableDeployment(unittest.TestCase):
    """Tests for repeatable packaging, schema validation, and reproducibility."""

    def test_deployment_package_validation_and_secrets_rejection(self):
        # Valid package
        valid_pkg = RepeatableDeploymentPackage(
            package_id="PKG-NICOPOLY-01",
            schema_version="2.0.0",
            software_version="3.11.0",
            site_configuration={"site_id": "SITE-A", "name": "Nicopoly Store 01"},
            camera_definitions=[{"camera_id": "CAM-01"}, {"camera_id": "CAM-02"}],
            zones=[{"zone_id": "Z1"}],
            calibration_refs={"CAM-01": "CAL-01"},
            rules=[{"rule_id": "R1"}],
            roles={"admin": ["ALL"]},
            retention={"retention_days": 30},
            privacy={"level": "ANONYMIZED"},
            security={"firewall": "ACTIVE"},
            action_policy={"policy": "DEFAULT_DENY"},
            health_configuration={"ping_sec": 5},
            recovery_configuration={"auto_restart": True},
        )
        status, issues = DeploymentValidator.validate_package(valid_pkg)
        self.assertEqual(status, VALIDATION_RESULT_VALID)
        self.assertEqual(len(issues), 0)

        # Invalid package with secret leak
        leaky_pkg = RepeatableDeploymentPackage(
            package_id="PKG-LEAK-01",
            schema_version="2.0.0",
            software_version="3.11.0",
            site_configuration={"password": "plaintext_admin_pass"},
            camera_definitions=[{"camera_id": "CAM-01"}],
            zones=[],
            calibration_refs={},
            rules=[],
            roles={"admin": ["ALL"]},
            retention={"retention_days": 30},
            privacy={},
            security={},
            action_policy={},
            health_configuration={},
            recovery_configuration={},
        )
        status, issues = DeploymentValidator.validate_package(leaky_pkg)
        self.assertEqual(status, VALIDATION_RESULT_INVALID)
        self.assertTrue(any("credential or secret" in issue for issue in issues))

    def test_deployment_reproducibility_and_idempotency(self):
        pkg1 = RepeatableDeploymentPackage(
            package_id="PKG-REPRO-01",
            schema_version="2.0.0",
            software_version="3.11.0",
            site_configuration={"site_id": "SITE-A"},
            camera_definitions=[{"camera_id": "CAM-01"}],
            zones=[{"zone_id": "Z1"}],
            calibration_refs={},
            rules=[],
            roles={"admin": ["ALL"]},
            retention={"retention_days": 15},
            privacy={},
            security={},
            action_policy={},
            health_configuration={},
            recovery_configuration={},
        )
        pkg2 = RepeatableDeploymentPackage(
            package_id="PKG-REPRO-02",
            schema_version="2.0.0",
            software_version="3.11.0",
            site_configuration={"site_id": "SITE-A"},
            camera_definitions=[{"camera_id": "CAM-01"}],
            zones=[{"zone_id": "Z1"}],
            calibration_refs={},
            rules=[],
            roles={"admin": ["ALL"]},
            retention={"retention_days": 15},
            privacy={},
            security={},
            action_policy={},
            health_configuration={},
            recovery_configuration={},
        )
        self.assertEqual(pkg1.package_hash, pkg2.package_hash)

    def test_new_site_bootstrap_no_code_fork(self):
        manager = MultiSiteManager()
        template = SiteTemplate(
            template_id="TMPL-RETAIL-01",
            site_type="RETAIL_STORE",
            schema_version="2.0.0",
            default_retention_days=30,
        )
        profile_b = manager.bootstrap_new_site(
            template=template,
            site_id="SITE-B",
            site_name="Secondary Retail Branch",
            camera_ids=["CAM-B01", "CAM-B02"],
            zone_ids=["ZONE-B1"],
        )
        self.assertEqual(profile_b.site_id, "SITE-B")
        self.assertEqual(profile_b.status, DEPLOYMENT_STATUS_VALIDATED)
        self.assertTrue(len(profile_b.configuration_hash) > 0)


class TestMultiSiteIsolationAndSecurity(unittest.TestCase):
    """Tests for multi-site data, action, experience, and operator isolation."""

    def setUp(self):
        self.manager = MultiSiteManager()
        template = SiteTemplate(template_id="TMPL-01", site_type="STORE", schema_version="2.0.0")
        self.profile_a = self.manager.bootstrap_new_site(
            template, "SITE-A", "Store A", ["CAM-A01"], ["Z-A1"]
        )
        self.profile_b = self.manager.bootstrap_new_site(
            template, "SITE-B", "Store B", ["CAM-B01"], ["Z-B1"]
        )
        self.manager.activate_site("SITE-A")
        self.manager.activate_site("SITE-B")

    def test_site_data_isolation_and_cross_site_access_denial(self):
        # Insert event in Site A
        self.manager.site_data_stores["SITE-A"]["events"].append({"event_id": "EVT-A-01"})

        # Site A querying Site A succeeds
        res_a = self.manager.query_site_data("SITE-A", "SITE-A", "events")
        self.assertEqual(len(res_a), 1)

        # Site B querying Site A fails closed
        with self.assertRaises(MultiSiteSecurityError):
            self.manager.query_site_data("SITE-B", "SITE-A", "events")

    def test_multisite_action_isolation(self):
        action_payload = {"action_id": "ACT-01", "type": "ALERT_DISPATCH"}
        # Site A executing action on Site A succeeds
        res = self.manager.execute_site_action("SITE-A", "SITE-A", action_payload)
        self.assertEqual(res["status"], "VERIFIED")

        # Site A attempting to execute action on Site B fails closed
        with self.assertRaises(MultiSiteSecurityError):
            self.manager.execute_site_action("SITE-A", "SITE-B", action_payload)

    def test_operator_scope_and_routing(self):
        operators = [
            {"operator_id": "OP-01", "allowed_site_ids": ["SITE-A"], "status": "ACTIVE"},
            {"operator_id": "OP-02", "allowed_site_ids": ["SITE-B"], "status": "ACTIVE"},
        ]

        # OP-01 querying Site A succeeds
        events_a = self.manager.query_site_data(
            "SITE-A", "SITE-A", "events", operator_allowed_sites=["SITE-A"]
        )
        self.assertIsNotNone(events_a)

        # OP-01 querying Site B is denied
        with self.assertRaises(MultiSiteSecurityError):
            self.manager.query_site_data(
                "SITE-A", "SITE-B", "events", operator_allowed_sites=["SITE-A"]
            )

        # Routing investigation for Site B selects OP-02
        routed = self.manager.route_operator_investigation("SITE-B", {"inv_id": "INV-01"}, operators)
        self.assertEqual(routed, "OP-02")


class TestMultiSiteOperationsAndMaintenance(unittest.TestCase):
    """Tests for maintenance windows, health isolation, upgrades, backups, and drift."""

    def setUp(self):
        self.manager = MultiSiteManager()
        template = SiteTemplate(template_id="TMPL-01", site_type="STORE", schema_version="2.0.0")
        self.profile_a = self.manager.bootstrap_new_site(
            template, "SITE-A", "Store A", ["CAM-A01"], ["Z-A1"]
        )
        self.profile_b = self.manager.bootstrap_new_site(
            template, "SITE-B", "Store B", ["CAM-B01"], ["Z-B1"]
        )

    def test_multisite_health_isolation(self):
        self.manager.health.record_site_health("SITE-A", {"camera": "HEALTHY", "perception": "HEALTHY"})
        self.manager.health.record_site_health("SITE-B", {"camera": "DEGRADED", "perception": "HEALTHY"})

        # Site B is DEGRADED, Site A remains HEALTHY in site record
        self.assertEqual(self.manager.health.sites["SITE-A"]["camera"], "HEALTHY")
        self.assertEqual(self.manager.health.sites["SITE-B"]["camera"], "DEGRADED")
        self.assertEqual(self.manager.health.overall_status, "DEGRADED")

    def test_controlled_maintenance_lifecycle(self):
        window = MaintenanceWindow(
            maintenance_id="MNT-20260829-01",
            site_ids=["SITE-A"],
            reason="Firmware upgrade",
            requested_by="engineer",
            approved_by="admin",
            planned_start="2026-08-29T02:00:00Z",
            planned_end="2026-08-29T03:00:00Z",
            affected_components=["CAMERA_STREAM"],
            rollback_ref="RB-MNT-01",
        )
        self.manager.schedule_maintenance(window)
        self.manager.start_maintenance(window.maintenance_id)
        self.assertEqual(window.status, MAINTENANCE_STATUS_ACTIVE)

        self.manager.complete_maintenance(window.maintenance_id)
        self.assertEqual(window.status, MAINTENANCE_STATUS_COMPLETED)

    def test_upgrade_and_fail_safe_rollback(self):
        rec_success = UpgradeRecord(
            upgrade_id="UPG-01",
            from_version="3.11.0",
            to_version="3.12.0",
            site_ids=["SITE-A", "SITE-B"],
            precheck_ref="CHK-01",
            migration_ref="MIG-01",
            validation_ref="VAL-01",
            rollback_ref="RB-01",
        )
        res = self.manager.apply_upgrade(rec_success, simulate_failure=False)
        self.assertEqual(res.status, UPGRADE_STATUS_VERIFIED)
        self.assertEqual(self.manager.software_version, "3.12.0")

        # Failed upgrade triggers rollback
        rec_fail = UpgradeRecord(
            upgrade_id="UPG-02",
            from_version="3.12.0",
            to_version="3.13.0",
            site_ids=["SITE-A"],
            precheck_ref="CHK-02",
            migration_ref="MIG-02",
            validation_ref="VAL-02",
            rollback_ref="RB-02",
        )
        res_fail = self.manager.apply_upgrade(rec_fail, simulate_failure=True)
        self.assertEqual(res_fail.status, UPGRADE_STATUS_ROLLED_BACK)
        self.assertEqual(self.manager.software_version, "3.12.0")

    def test_backup_and_restore_verification(self):
        manifest = self.manager.create_backup(["SITE-A", "SITE-B"])
        self.assertEqual(manifest.status, "VALIDATED")
        self.assertTrue(len(manifest.hashes) > 0)
        self.assertNotIn("password", manifest.included_stores)

        restored = self.manager.verify_and_restore_backup(manifest)
        self.assertTrue(restored)

    def test_configuration_drift_and_rollback(self):
        # Initial check in sync
        drift = self.manager.check_configuration_drift("SITE-A")
        self.assertEqual(drift.status, DRIFT_STATUS_IN_SYNC)

        # Mutate configuration
        self.profile_a.camera_ids.append("CAM-A99")
        drift_mutated = self.manager.check_configuration_drift("SITE-A")
        self.assertEqual(drift_mutated.status, DRIFT_STATUS_DRIFT_DETECTED)

        # Rollback
        self.profile_a.camera_ids.remove("CAM-A99")
        drift_restored = self.manager.check_configuration_drift("SITE-A")
        self.assertEqual(drift_restored.status, DRIFT_STATUS_IN_SYNC)


if __name__ == "__main__":
    unittest.main()
