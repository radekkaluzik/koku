#
# Copyright 2021 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Test the OCPCloudParquetReportSummaryUpdaterTest."""
import datetime
import decimal
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from tenant_schemas.utils import schema_context

from api.models import Provider
from api.utils import DateHelper
from masu.database.ocp_report_db_accessor import OCPReportDBAccessor
from masu.database.provider_db_accessor import ProviderDBAccessor
from masu.processor.ocp.ocp_cloud_parquet_summary_updater import OCPCloudParquetReportSummaryUpdater
from masu.test import MasuTestCase
from masu.util.ocp.common import get_cluster_alias_from_cluster_id
from masu.util.ocp.common import get_cluster_id_from_provider


class OCPCloudParquetReportSummaryUpdaterTest(MasuTestCase):
    """Test cases for the OCPCloudParquetReportSummaryUpdaterTest class."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class with required objects."""
        super().setUpClass()
        cls.dh = DateHelper()

    def setUp(self):
        """Set up tests."""
        super().setUp()
        self.today = self.dh.today

    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider")
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AWSReportDBAccessor.populate_ocp_on_aws_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AWSReportDBAccessor.populate_ocp_on_aws_cost_daily_summary_presto"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.aws_get_bills_from_provider")
    def test_update_aws_summary_tables(
        self,
        mock_utility,
        mock_delete,
        mock_ocpall_proj_summ,
        mock_ocpall_summ,
        mock_ocpall_persp,
        mock_ocp_on_aws,
        mock_tag_summary,
        mock_map,
        mock_cluster_info,
    ):
        """Test that summary tables are properly run for an OCP provider."""
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        # this is a yes or no check so true is fine
        mock_cluster_info.return_value = True
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.aws_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpaws_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id

        mock_map.return_value = {self.ocpaws_provider_uuid: (self.aws_provider_uuid, Provider.PROVIDER_AWS)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_aws_summary_tables(self.ocpaws_provider_uuid, self.aws_test_provider_uuid, start_date, end_date)
        distribution = None
        mock_ocp_on_aws.assert_called_with(
            start_date,
            end_date,
            self.ocpaws_provider_uuid,
            self.aws_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
        )

    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider")
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AzureReportDBAccessor.populate_ocp_on_azure_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AzureReportDBAccessor.populate_ocp_on_azure_cost_daily_summary_presto"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.azure_get_bills_from_provider")
    def test_update_azure_summary_tables(
        self,
        mock_utility,
        mock_delete,
        mock_ocpall_proj_summ,
        mock_ocpall_summ,
        mock_ocpall_persp,
        mock_ocp_on_azure,
        mock_tag_summary,
        mock_map,
        mock_cluster_info,
    ):
        """Test that summary tables are properly run for an OCP provider."""
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        # this is basically a yes or no check so true is fine
        mock_cluster_info.return_value = True
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.azure_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpazure_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id
        mock_map.return_value = {self.ocpazure_provider_uuid: (self.azure_provider_uuid, Provider.PROVIDER_AZURE)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_azure_summary_tables(
            self.ocpazure_provider_uuid, self.azure_test_provider_uuid, start_date, end_date
        )
        distribution = None
        mock_ocp_on_azure.assert_called_with(
            start_date,
            end_date,
            self.ocpazure_provider_uuid,
            self.azure_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
        )

    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider")
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AzureReportDBAccessor.populate_ocp_on_azure_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AzureReportDBAccessor.populate_ocp_on_azure_cost_daily_summary_presto"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.azure_get_bills_from_provider")
    def test_update_azure_summary_tables_with_string_dates(
        self,
        mock_utility,
        mock_delete,
        mock_ocpall_proj_summ,
        mock_ocpall_summ,
        mock_ocpall_persp,
        mock_ocp_on_azure,
        mock_tag_summary,
        mock_map,
        mock_cluster_info,
    ):
        """Test that summary tables are properly run for an OCP provider."""
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        # this is a yes or no check so true is fine
        mock_cluster_info.return_value = True
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.azure_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpazure_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id
        mock_map.return_value = {self.ocpazure_provider_uuid: (self.azure_provider_uuid, Provider.PROVIDER_AZURE)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_azure_summary_tables(
            self.ocpazure_provider_uuid, self.azure_test_provider_uuid, str(start_date), str(end_date)
        )
        distribution = None
        mock_ocp_on_azure.assert_called_with(
            start_date,
            end_date,
            self.ocpazure_provider_uuid,
            self.azure_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
        )

    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_ui_summary_tables"
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_cost_daily_summary_presto"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.back_populate_ocp_on_gcp_daily_summary_trino"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.gcp_get_bills_from_provider")
    def test_update_gcp_summary_tables(
        self,
        mock_utility,
        mock_delete,
        mock_back_populate,
        mock_ocp_on_gcp,
        mock_ui_tables,
        mock_tag_summary,
        mock_map,
        mock_ocpallproj,
        mock_ocpall,
        mock_ocpallui,
    ):
        """Test that summary tables are properly run for a gcp provider."""
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.gcp_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpgcp_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id
        mock_map.return_value = {self.ocpgcp_provider_uuid: (self.gcp_provider_uuid, Provider.PROVIDER_GCP)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_gcp_summary_tables(self.ocpgcp_provider_uuid, self.gcp_test_provider_uuid, start_date, end_date)
        cluster_id = get_cluster_id_from_provider(self.ocpgcp_provider_uuid)
        cluster_alias = get_cluster_alias_from_cluster_id(cluster_id)
        sql_params = {
            "schema_name": self.schema_name,
            "start_date": start_date,
            "end_date": end_date,
            "source_uuid": self.gcp_test_provider_uuid,
            "cluster_id": cluster_id,
            "cluster_alias": cluster_alias,
            "source_type": "GCP",
        }
        distribution = None
        mock_ocp_on_gcp.assert_called_with(
            start_date,
            end_date,
            self.ocpgcp_provider_uuid,
            cluster_id,
            self.gcp_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
        )
        mock_ui_tables.assert_called_with(sql_params)

        mock_tag_summary.assert_called_with([str(bill.id) for bill in fake_bills], start_date, end_date)

    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_nodes_for_cluster"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.summarize_ocp_on_gcp_by_node", return_value=True)
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_ui_summary_tables"
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_cost_daily_summary_presto_by_node"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.back_populate_ocp_on_gcp_daily_summary_trino"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.gcp_get_bills_from_provider")
    def test_update_gcp_summary_tables_unleash_node(
        self,
        mock_utility,
        mock_delete,
        mock_back_populate,
        mock_ocp_on_gcp,
        mock_ui_tables,
        mock_tag_summary,
        mock_map,
        mock_ocpallproj,
        mock_ocpall,
        mock_ocpallui,
        mock_unleash,
        mock_nodes,
    ):
        """Test that summary tables are properly run for a gcp provider."""
        node_name = "node1"
        mock_nodes.return_value = [[node_name]]
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.gcp_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpgcp_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id
        mock_map.return_value = {self.ocpgcp_provider_uuid: (self.gcp_provider_uuid, Provider.PROVIDER_GCP)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_gcp_summary_tables(self.ocpgcp_provider_uuid, self.gcp_test_provider_uuid, start_date, end_date)
        cluster_id = get_cluster_id_from_provider(self.ocpgcp_provider_uuid)
        cluster_alias = get_cluster_alias_from_cluster_id(cluster_id)
        sql_params = {
            "schema_name": self.schema_name,
            "start_date": start_date,
            "end_date": end_date,
            "source_uuid": self.gcp_test_provider_uuid,
            "cluster_id": cluster_id,
            "cluster_alias": cluster_alias,
            "source_type": "GCP",
        }
        distribution = None
        mock_ocp_on_gcp.assert_called_with(
            start_date,
            end_date,
            self.ocpgcp_provider_uuid,
            cluster_id,
            self.gcp_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
            node_name,
            1,
        )
        mock_ui_tables.assert_called_with(sql_params)

        mock_tag_summary.assert_called_with([str(bill.id) for bill in fake_bills], start_date, end_date)

    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_ui_summary_tables"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_daily_summary"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.populate_ocp_on_all_project_daily_summary"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_updater_base.OCPCloudUpdaterBase.get_infra_map_from_providers")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_tags_summary_table"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_ui_summary_tables"
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.populate_ocp_on_gcp_cost_daily_summary_presto"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.back_populate_ocp_on_gcp_daily_summary_trino"  # noqa: E501
    )
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.GCPReportDBAccessor.delete_line_item_daily_summary_entries_for_date_range_raw"  # noqa: E501
    )
    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.gcp_get_bills_from_provider")
    def test_update_gcp_summary_tables_with_string_dates(
        self,
        mock_utility,
        mock_delete,
        mock_back_populate,
        mock_ocp_on_gcp,
        mock_ui_tables,
        mock_tag_summary,
        mock_map,
        mock_ocpallproj,
        mock_ocpall,
        mock_ocpallui,
    ):
        """Test that summary tables are properly run for a gcp provider."""
        fake_bills = MagicMock()
        fake_bills.__iter__.return_value = [Mock(), Mock()]
        first = Mock()
        bill_id = 1
        first.return_value.id = bill_id
        fake_bills.first = first
        mock_utility.return_value = fake_bills
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)

        with ProviderDBAccessor(self.gcp_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with OCPReportDBAccessor(self.schema_name) as accessor:
            report_period = accessor.report_periods_for_provider_uuid(self.ocpgcp_provider_uuid, start_date)
        with schema_context(self.schema_name):
            current_ocp_report_period_id = report_period.id
        mock_map.return_value = {self.ocpgcp_provider_uuid: (self.gcp_provider_uuid, Provider.PROVIDER_GCP)}
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_gcp_summary_tables(
            self.ocpgcp_provider_uuid, self.gcp_test_provider_uuid, str(start_date), str(end_date)
        )
        cluster_id = get_cluster_id_from_provider(self.ocpgcp_provider_uuid)
        cluster_alias = get_cluster_alias_from_cluster_id(cluster_id)
        distribution = None
        mock_ocp_on_gcp.assert_called_with(
            start_date,
            end_date,
            self.ocpgcp_provider_uuid,
            cluster_id,
            self.gcp_test_provider_uuid,
            current_ocp_report_period_id,
            bill_id,
            decimal.Decimal(0),
            distribution,
        )
        sql_params = {
            "schema_name": self.schema_name,
            "start_date": start_date,
            "end_date": end_date,
            "source_uuid": self.gcp_test_provider_uuid,
            "cluster_id": cluster_id,
            "cluster_alias": cluster_alias,
            "source_type": "GCP",
        }
        mock_ui_tables.assert_called_with(sql_params)

        mock_tag_summary.assert_called_with([str(bill.id) for bill in fake_bills], start_date, end_date)

    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AzureReportDBAccessor.populate_ocp_on_azure_cost_daily_summary_presto"  # noqa: E501
    )
    def test_update_azure_summary_tables_with_no_cluster_info(self, mock_ocp_on_azure, mock_cluster_info):
        """Test that azure summary tables are not updated when there is no cluster info."""
        # this is a yes or no check so false is fine
        mock_cluster_info.return_value = False
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)
        with ProviderDBAccessor(self.azure_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_azure_summary_tables(
            self.ocpazure_provider_uuid, self.azure_test_provider_uuid, str(start_date), str(end_date)
        )
        mock_ocp_on_azure.assert_not_called()

    @patch("masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider")
    @patch(
        "masu.processor.ocp.ocp_cloud_parquet_summary_updater.AWSReportDBAccessor.populate_ocp_on_aws_cost_daily_summary_presto"  # noqa: E501
    )
    def test_update_aws_summary_tables_with_no_cluster_info(self, mock_ocp_on_aws, mock_cluster_info):
        """Test that aws summary tables are not updated when there is no cluster info."""
        # this is a yes or no check so false is fine
        mock_cluster_info.return_value = False
        start_date = self.dh.today.date()
        end_date = start_date + datetime.timedelta(days=1)
        with ProviderDBAccessor(self.aws_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
        updater.update_aws_summary_tables(
            self.ocpaws_provider_uuid, self.aws_test_provider_uuid, str(start_date), str(end_date)
        )
        mock_ocp_on_aws.assert_not_called()

    def test_update_aws_summary_tables_no_report_period(self):
        start_date = "1900-12-30"
        end_date = "1900-12-31"
        with ProviderDBAccessor(self.aws_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with patch(
            "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider",
            return_value="goo-goo-cluster",
        ):
            updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
            with self.assertLogs("masu.processor.ocp.ocp_cloud_parquet_summary_updater", level="INFO") as _logger:
                updater.update_aws_summary_tables(
                    self.ocpaws_provider_uuid, self.aws_test_provider_uuid, start_date, end_date
                )
                found_it = False
                for log_line in _logger.output:
                    found_it = "No report period for AWS provider" in log_line
                    if found_it:
                        break
                self.assertTrue(found_it)

    def test_update_azure_summary_tables_no_report_period(self):
        start_date = "1900-12-30"
        end_date = "1900-12-31"
        with ProviderDBAccessor(self.azure_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with patch(
            "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider",
            return_value="goo-goo-cluster",
        ):
            updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
            with self.assertLogs("masu.processor.ocp.ocp_cloud_parquet_summary_updater", level="INFO") as _logger:
                updater.update_azure_summary_tables(
                    self.ocpazure_provider_uuid, self.azure_test_provider_uuid, start_date, end_date
                )
                found_it = False
                for log_line in _logger.output:
                    found_it = "No report period for Azure provider" in log_line
                    if found_it:
                        break
                self.assertTrue(found_it)

    def test_update_gcp_summary_tables_no_report_period(self):
        start_date = "1900-12-30"
        end_date = "1900-12-31"
        with ProviderDBAccessor(self.gcp_provider_uuid) as provider_accessor:
            provider = provider_accessor.get_provider()
        with patch(
            "masu.processor.ocp.ocp_cloud_parquet_summary_updater.OCPReportDBAccessor.get_cluster_for_provider",
            return_value="goo-goo-cluster",
        ):
            updater = OCPCloudParquetReportSummaryUpdater(schema="org1234567", provider=provider, manifest=None)
            with self.assertLogs("masu.processor.ocp.ocp_cloud_parquet_summary_updater", level="INFO") as _logger:
                updater.update_gcp_summary_tables(
                    self.ocpgcp_provider_uuid, self.gcp_test_provider_uuid, start_date, end_date
                )
                found_it = False
                for log_line in _logger.output:
                    found_it = "No report period for GCP provider" in log_line
                    if found_it:
                        break
                self.assertTrue(found_it)
