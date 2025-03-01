#
# Copyright 2021 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Test the Report views."""
import datetime
import random
from decimal import Decimal
from unittest import skip
from unittest.mock import patch
from urllib.parse import quote_plus
from urllib.parse import urlencode

from dateutil import relativedelta
from django.db.models import Count
from django.db.models import DecimalField
from django.db.models import F
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import HttpRequest
from django.http import QueryDict
from django.urls import reverse
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.test import APIClient
from tenant_schemas.utils import tenant_context

from api.iam.test.iam_test_case import IamTestCase
from api.models import User
from api.query_handler import TruncDayString
from api.report.ocp.view import OCPCpuView
from api.report.ocp.view import OCPMemoryView
from api.tags.ocp.queries import OCPTagQueryHandler
from api.tags.ocp.view import OCPTagView
from api.utils import DateHelper
from koku.database import KeyDecimalTransform
from reporting.models import OCPUsageLineItemDailySummary


class OCPReportViewTest(IamTestCase):
    """Tests the report view."""

    @classmethod
    def setUpClass(cls):
        """Set up the test class."""
        super().setUpClass()
        cls.dh = DateHelper()
        cls.ten_days_ago = cls.dh.n_days_ago(cls.dh._now, 9)

    def setUp(self):
        """Set up the customer view tests."""
        super().setUp()

        self.report_ocp_cpu = {
            "group_by": {"project": ["*"]},
            "filter": {"resolution": "monthly", "time_scope_value": "-1", "time_scope_units": "month"},
            "data": [
                {
                    "date": "2018-10",
                    "projects": [
                        {
                            "project": "default",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "default",
                                    "limit": "null",
                                    "usage": 0.119385,
                                    "request": 9.506666,
                                }
                            ],
                        },
                        {
                            "project": "metering",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "metering",
                                    "limit": "null",
                                    "usage": 4.464511,
                                    "request": 53.985832,
                                }
                            ],
                        },
                        {
                            "project": "monitoring",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "monitoring",
                                    "limit": "null",
                                    "usage": 7.861343,
                                    "request": 17.920067,
                                }
                            ],
                        },
                        {
                            "project": "openshift-web-console",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "openshift-web-console",
                                    "limit": "null",
                                    "usage": 0.862687,
                                    "request": 4.753333,
                                }
                            ],
                        },
                    ],
                }
            ],
            "total": {"pod_usage_cpu_core_hours": 13.307928, "pod_request_cpu_core_hours": 86.165898},
        }
        self.report_ocp_mem = {
            "group_by": {"project": ["*"]},
            "filter": {"resolution": "monthly", "time_scope_value": "-1", "time_scope_units": "month"},
            "data": [
                {
                    "date": "2018-10",
                    "projects": [
                        {
                            "project": "default",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "default",
                                    "memory_usage_gigabytes": 0.162249,
                                    "memory_requests_gigabytes": 1.063302,
                                }
                            ],
                        },
                        {
                            "project": "metering",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "metering",
                                    "memory_usage_gigabytes": 5.899788,
                                    "memory_requests_gigabytes": 7.007081,
                                }
                            ],
                        },
                        {
                            "project": "monitoring",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "monitoring",
                                    "memory_usage_gigabytes": 3.178287,
                                    "memory_requests_gigabytes": 4.153526,
                                }
                            ],
                        },
                        {
                            "project": "openshift-web-console",
                            "values": [
                                {
                                    "date": "2018-10",
                                    "project": "openshift-web-console",
                                    "memory_usage_gigabytes": 0.068988,
                                    "memory_requests_gigabytes": 0.207677,
                                }
                            ],
                        },
                    ],
                }
            ],
            "total": {"pod_usage_memory_gigabytes": 9.309312, "pod_request_memory_gigabytes": 12.431585},
        }

    @patch("api.report.ocp.query_handler.OCPReportQueryHandler")
    def test_ocpcpuview_success(self, mock_handler):
        """Test OCP cpu view report."""
        mock_handler.return_value.execute_query.return_value = self.report_ocp_cpu
        params = {
            "group_by[node]": "*",
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        user = User.objects.get(username=self.user_data["username"])

        django_request = HttpRequest()
        if not django_request.META.get("HTTP_HOST"):
            django_request.META["HTTP_HOST"] = "testhost"

        qd = QueryDict(mutable=True)
        qd.update(params)
        django_request.GET = qd
        request = Request(django_request)
        request.user = user

        response = OCPCpuView().get(request)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("api.report.ocp.query_handler.OCPReportQueryHandler")
    def test_ocpmemview_success(self, mock_handler):
        """Test OCP memory view report."""
        mock_handler.return_value.execute_query.return_value = self.report_ocp_mem
        params = {
            "group_by[node]": "*",
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        user = User.objects.get(username=self.user_data["username"])

        django_request = HttpRequest()
        if not django_request.META.get("HTTP_HOST"):
            django_request.META["HTTP_HOST"] = "testhost"

        qd = QueryDict(mutable=True)
        qd.update(params)
        django_request.GET = qd
        request = Request(django_request)
        request.user = user

        response = OCPMemoryView().get(request)
        self.assertIsInstance(response, Response)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_cpu(self):
        """Test that OCP CPU endpoint works."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        response = client.get(url, **self.headers)

        expected_end_date = self.dh.today.date().strftime("%Y-%m-%d")
        expected_start_date = self.ten_days_ago.strftime("%Y-%m-%d")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_start_date)
        self.assertEqual(dates[-1], expected_end_date)

        for item in data.get("data"):
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("limit" in values)
                self.assertTrue("usage" in values)
                self.assertTrue("request" in values)

    def test_costs_api_has_units(self):
        """Test that the costs API returns units."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        response = client.get(url, **self.headers)
        response_json = response.json()

        total = response_json.get("meta", {}).get("total", {})
        data = response_json.get("data", {})
        self.assertTrue("cost" in total)
        self.assertEqual(total.get("cost", {}).get("total", {}).get("units"), "USD")

        for item in data:
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("cost" in values)
                self.assertEqual(values.get("cost", {}).get("total").get("units"), "USD")

    def test_cpu_api_has_units(self):
        """Test that the CPU API returns units."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        response = client.get(url, **self.headers)
        response_json = response.json()

        total = response_json.get("meta", {}).get("total", {})
        data = response_json.get("data", {})
        self.assertTrue("usage" in total)
        self.assertEqual(total.get("usage", {}).get("units"), "Core-Hours")

        for item in data:
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("usage" in values)
                self.assertEqual(values.get("usage", {}).get("units"), "Core-Hours")

    def test_memory_api_has_units(self):
        """Test that the memory API returns units."""
        url = reverse("reports-openshift-memory")
        client = APIClient()
        response = client.get(url, **self.headers)
        response_json = response.json()

        total = response_json.get("meta", {}).get("total", {})
        data = response_json.get("data", {})
        self.assertTrue("usage" in total)
        self.assertEqual(total.get("usage", {}).get("units"), "GB-Hours")

        for item in data:
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("usage" in values)
                self.assertEqual(values.get("usage", {}).get("units"), "GB-Hours")

    def test_execute_query_ocp_cpu_last_thirty_days(self):
        """Test that OCP CPU endpoint works."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"filter[time_scope_value]": "-30", "filter[time_scope_units]": "day", "filter[resolution]": "daily"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)

        expected_end_date = self.dh.today
        expected_start_date = self.dh.n_days_ago(expected_end_date, 29)
        expected_end_date = str(expected_end_date.date())
        expected_start_date = str(expected_start_date.date())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_start_date)
        self.assertEqual(dates[-1], expected_end_date)

        for item in data.get("data"):
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("limit" in values)
                self.assertTrue("usage" in values)
                self.assertTrue("request" in values)

    def test_execute_query_ocp_cpu_this_month(self):
        """Test that data is returned for the full month."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)

        expected_date = self.dh.today.strftime("%Y-%m")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_date)

        values = data.get("data")[0].get("values")[0]
        self.assertTrue("limit" in values)
        self.assertTrue("usage" in values)
        self.assertTrue("request" in values)

    def test_execute_query_ocp_cpu_this_month_daily(self):
        """Test that data is returned for the full month."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"filter[resolution]": "daily", "filter[time_scope_value]": "-1", "filter[time_scope_units]": "month"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)

        expected_start_date = self.dh.this_month_start.strftime("%Y-%m-%d")
        expected_end_date = self.dh.today.strftime("%Y-%m-%d")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_start_date)
        self.assertEqual(dates[-1], expected_end_date)

        for item in data.get("data"):
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("limit" in values)
                self.assertTrue("usage" in values)
                self.assertTrue("request" in values)

    def test_execute_query_ocp_cpu_last_month(self):
        """Test that data is returned for the last month."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-2",
            "filter[time_scope_units]": "month",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)

        expected_date = self.dh.last_month_start.strftime("%Y-%m")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_date)

        values = data.get("data")[0].get("values")[0]
        self.assertTrue("limit" in values)
        self.assertTrue("usage" in values)
        self.assertTrue("request" in values)

    def test_execute_query_ocp_cpu_last_month_daily(self):
        """Test that data is returned for the full month."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"filter[resolution]": "daily", "filter[time_scope_value]": "-2", "filter[time_scope_units]": "month"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)

        expected_start_date = self.dh.last_month_start.strftime("%Y-%m-%d")
        expected_end_date = self.dh.last_month_end.strftime("%Y-%m-%d")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        dates = sorted(item.get("date") for item in data.get("data"))
        self.assertEqual(dates[0], expected_start_date)
        self.assertEqual(dates[-1], expected_end_date)

        for item in data.get("data"):
            if item.get("values"):
                values = item.get("values")[0]
                self.assertTrue("limit" in values)
                self.assertTrue("usage" in values)
                self.assertTrue("request" in values)

    def test_execute_query_ocp_memory_group_by_limit(self):
        """Test that OCP Mem endpoint works with limits."""
        url = reverse("reports-openshift-memory")
        client = APIClient()
        params = {
            "group_by[node]": "*",
            "filter[limit]": "1",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "filter[resolution]": "daily",
        }
        url = f"{url}?{urlencode(params, quote_via=quote_plus)}"
        response = client.get(url, **self.headers)
        data = response.data

        with tenant_context(self.tenant):
            totals = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .values(*["usage_start"])
                .annotate(usage=Sum("pod_usage_memory_gigabyte_hours"))
            )
            num_nodes = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .aggregate(Count("node", distinct=True))
                .get("node__count")
            )

        totals = {total.get("usage_start").strftime("%Y-%m-%d"): total.get("usage") for total in totals}

        self.assertIn("nodes", data.get("data")[0])

        # assert the others count is correct
        meta = data.get("meta")
        if "'no-node'" in str(data):
            num_nodes += 1
        self.assertEqual(meta.get("others"), num_nodes - 1)

        # Check if limit returns the correct number of results, and
        # that the totals add up properly
        for item in data.get("data"):
            if item.get("nodes"):
                date = item.get("date")
                nodes = item.get("nodes")
                node_total_usage = 0
                for node in nodes:
                    if node.get("values")[0].get("usage", {}):
                        node_value = node.get("values")[0].get("usage", {}).get("value", 0)
                        node_total_usage += node_value
                self.assertEqual(node_total_usage, totals.get(date))

    def test_execute_query_ocp_memory_group_by_limit_large(self):
        """Test that OCP Mem endpoint works with limits."""
        url = reverse("reports-openshift-memory")
        client = APIClient()
        params = {
            "group_by[node]": "*",
            "filter[limit]": "1000",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "filter[resolution]": "daily",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        data = response.data

        # assert the others count is correct
        meta = data.get("meta")
        self.assertEqual(meta.get("others"), 0)

    def test_execute_query_ocp_costs_group_by_cluster(self):
        """Test that the costs endpoint is reachable."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {"group_by[cluster]": "*"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_costs_group_by_node(self):
        """Test that the costs endpoint is reachable."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {"group_by[node]": "*"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_costs_group_by_project(self):
        """Test that the costs endpoint is reachable."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {
            "group_by[project]": "*",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            "filter[resolution]": "monthly",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Using .data instead of .json() retains the Decimal types for
        # direct value and type comparisons
        data = response.data

        with tenant_context(self.tenant):
            cost = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.dh.this_month_start.date())
                .aggregate(
                    total=Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_project_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "supplementary_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "infrastructure_project_monthly_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_project_markup_cost"), Value(0, output_field=DecimalField()))
                    )
                )
                .get("total")
            )
            expected_total = cost if cost is not None else 0
        total = data.get("meta", {}).get("total", {}).get("cost", {}).get("total", {}).get("value", 0)
        self.assertNotEqual(total, Decimal(0))
        self.assertAlmostEqual(total, expected_total, 6)

    def test_execute_query_ocp_costs_with_delta(self):
        """Test that deltas work for costs."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {
            "delta": "cost",
            "filter[resolution]": "daily",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        this_month_start = self.dh.this_month_start
        last_month_start = self.dh.last_month_start

        date_delta = relativedelta.relativedelta(months=1)
        last_month_end = self.dh.this_month_end - date_delta

        def date_to_string(dt):
            return dt.strftime("%Y-%m-%d")

        def string_to_date(dt):
            return datetime.datetime.strptime(dt, "%Y-%m-%d").date()

        with tenant_context(self.tenant):
            current_total = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=this_month_start.date())
                .aggregate(
                    total=Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                    )
                )
                .get("total")
            )
            current_total = current_total if current_total is not None else 0

            current_totals = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=this_month_start.date())
                .annotate(**{"date": TruncDayString("usage_start")})
                .values(*["date"])
                .annotate(
                    total=Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                    )
                )
            )

            prev_totals = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=last_month_start.date())
                .filter(usage_start__lte=last_month_end.date())
                .annotate(**{"date": TruncDayString("usage_start")})
                .values(*["date"])
                .annotate(
                    total=Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "supplementary_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("pvc", "infrastructure_monthly_cost_json"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                    )
                )
            )

        current_totals = {total.get("date"): total.get("total") for total in current_totals}
        prev_totals = {
            date_to_string(string_to_date(total.get("date")) + date_delta): total.get("total")
            for total in prev_totals
            if date_to_string(string_to_date(total.get("date")) + date_delta) in current_totals
        }

        prev_total = sum(prev_totals.values())
        prev_total = prev_total if prev_total is not None else 0

        expected_delta = current_total - prev_total
        delta = data.get("meta", {}).get("delta", {}).get("value")
        self.assertNotEqual(delta, Decimal(0))
        self.assertAlmostEqual(delta, expected_delta, 6)
        for item in data.get("data"):
            date = item.get("date")
            expected_delta = current_totals.get(date, 0) - prev_totals.get(date, 0)
            values = item.get("values", [])
            delta_value = 0
            if values:
                delta_value = values[0].get("delta_value")
            self.assertAlmostEqual(delta_value, expected_delta, 1)

    def test_execute_query_ocp_costs_with_invalid_delta(self):
        """Test that bad deltas don't work for costs."""
        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {"delta": "usage"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        params = {"delta": "request"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_query_ocp_cpu_with_delta_cost(self):
        """Test that cost deltas work for CPU."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": "cost"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_cpu_with_delta_usage(self):
        """Test that usage deltas work for CPU."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": "usage"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_cpu_with_delta_request(self):
        """Test that request deltas work for CPU."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": "request"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_memory_with_delta(self):
        """Test that deltas work for CPU."""
        url = reverse("reports-openshift-memory")
        client = APIClient()
        params = {"delta": "request"}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_ocp_cpu_with_delta_usage__capacity(self):
        """Test that usage v capacity deltas work."""
        delta = "usage__capacity"
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": delta}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        delta_one, delta_two = delta.split("__")
        data = response.data
        data = [entry for entry in data.get("data", []) if entry.get("values")]
        self.assertNotEqual(len(data), 0)
        for entry in data:
            values = entry.get("values")[0]
            delta_percent = (
                (values.get(delta_one, {}).get("value") / values.get(delta_two, {}).get("value") * 100)  # noqa: W504
                if values.get(delta_two, {}).get("value")
                else 0
            )
            self.assertEqual(values.get("delta_percent"), delta_percent)

    def test_execute_query_ocp_cpu_with_delta_usage__request(self):
        """Test that usage v request deltas work."""
        delta = "usage__request"
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": delta}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        delta_one, delta_two = delta.split("__")
        data = response.data
        data = [entry for entry in data.get("data", []) if entry.get("values")]
        self.assertNotEqual(len(data), 0)
        for entry in data:
            values = entry.get("values")[0]
            delta_percent = (
                (values.get(delta_one, {}).get("value") / values.get(delta_two, {}).get("value") * 100)  # noqa: W504
                if values.get(delta_two, {}).get("value")
                else 0
            )
            self.assertEqual(values.get("delta_percent"), delta_percent)

    def test_execute_query_ocp_cpu_with_delta_request__capacity(self):
        """Test that request v capacity deltas work."""
        delta = "request__capacity"
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"delta": delta}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        delta_one, delta_two = delta.split("__")
        data = response.json()
        data = [entry for entry in data.get("data", []) if entry.get("values")]
        self.assertNotEqual(len(data), 0)
        for entry in data:
            values = entry.get("values")[0]
            delta_percent = (
                (values.get(delta_one, {}).get("value") / values.get(delta_two, {}).get("value") * 100)  # noqa: W504
                if values.get(delta_two)
                else 0
            )
            self.assertAlmostEqual(values.get("delta_percent"), delta_percent)

    def test_execute_query_group_by_project(self):
        """Test that grouping by project filters data."""
        with tenant_context(self.tenant):
            # Force Django to do GROUP BY to get nodes
            projects = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .values(*["namespace"])
                .annotate(project_count=Count("namespace"))
                .all()
            )
            project_of_interest = projects[0].get("namespace")

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[project]": project_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        for entry in data.get("data", []):
            for project in entry.get("projects", []):
                self.assertEqual(project.get("project"), project_of_interest)

    def test_execute_query_group_by_project_duplicate_projects(self):
        """Test that same-named projects across clusters are accounted for."""
        data_config = {"namespaces": ["project_one", "project_two"]}
        project_of_interest = data_config["namespaces"][0]

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[project]": project_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        for entry in data.get("data", []):
            for project in entry.get("projects", []):
                self.assertEqual(project.get("project"), project_of_interest)
                values = project.get("values", [])
                self.assertEqual(len(values), 1)

    def test_execute_query_filter_by_project_duplicate_projects(self):
        """Test that same-named projects across clusters are accounted for."""
        data_config = {"namespaces": ["project_one", "project_two"]}
        project_of_interest = data_config["namespaces"][0]

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"filter[project]": project_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertNotEqual(data.get("data", []), [])
        for entry in data.get("data", []):
            values = entry.get("values", [])
            if values:
                self.assertEqual(len(values), 1)

    def test_execute_query_group_by_cluster(self):
        """Test that grouping by cluster filters data."""
        with tenant_context(self.tenant):
            # Force Django to do GROUP BY to get nodes
            clusters = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .values(*["cluster_id"])
                .annotate(cluster_count=Count("cluster_id"))
                .all()
            )
            cluster_of_interest = clusters[0].get("cluster_id")

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[cluster]": cluster_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        for entry in data.get("data", []):
            for cluster in entry.get("clusters", []):
                self.assertEqual(cluster.get("cluster"), cluster_of_interest)

    def test_execute_query_group_by_pod_fails(self):
        """Test that grouping by pod filters data."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[pod]": "*"}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_execute_query_group_by_node(self):
        """Test that grouping by node filters data."""
        with tenant_context(self.tenant):
            # Force Django to do GROUP BY to get nodes
            nodes = (
                OCPUsageLineItemDailySummary.objects.values(*["node"])
                .filter(usage_start__gte=self.ten_days_ago.date())
                .values(*["node"])
                .annotate(node_count=Count("node"))
                .all()
            )
            node_of_interest = nodes[0].get("node")

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[node]": node_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        for entry in data.get("data", []):
            for node in entry.get("nodes", []):
                self.assertIn(node.get("node"), node_of_interest)

    def test_execute_query_group_by_node_duplicate_projects(self):
        """Test that same-named nodes across clusters are accounted for."""
        data_config = {"nodes": ["node_one", "node_two"]}
        node_of_interest = data_config["nodes"][0]

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[node]": node_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        for entry in data.get("data", []):
            for node in entry.get("nodes", []):
                self.assertEqual(node.get("node"), node_of_interest)
                values = node.get("values", [])
                self.assertEqual(len(values), 1)

    def test_execute_query_filter_by_node_duplicate_projects(self):
        """Test that same-named nodes across clusters are accounted for."""
        with tenant_context(self.tenant):
            nodes = OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date()).values_list(
                "node"
            )
            node_of_interest = nodes[0][0]

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"filter[node]": node_of_interest}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertNotEqual(data.get("data"), [])
        for entry in data.get("data", []):
            values = entry.get("values", [])
            if values:
                self.assertEqual(len(values), 1)

    def test_execute_query_with_tag_filter(self):
        """Test that data is filtered by tag key."""
        url = "?filter[type]=pod&filter[time_scope_value]=-10&filter[enabled]=true"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        tag_keys.sort(reverse=True)
        filter_key = tag_keys[0]

        with tenant_context(self.tenant):
            labels = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .filter(pod_labels__has_key=filter_key)
                .values(*["pod_labels"])
                .all()
            )
            label_of_interest = labels[0]
            filter_value = label_of_interest.get("pod_labels", {}).get(filter_key)

            totals = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .filter(**{f"pod_labels__{filter_key}": filter_value})
                .aggregate(
                    **{
                        "usage": Sum("pod_usage_cpu_core_hours"),
                        "request": Sum("pod_request_cpu_core_hours"),
                        "limit": Sum("pod_limit_cpu_core_hours"),
                        "cost": Sum(
                            Coalesce(
                                KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                                Value(0, output_field=DecimalField()),
                            )
                            + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                            + Coalesce(
                                KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                                Value(0, output_field=DecimalField()),
                            )
                            + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                        ),
                    }
                )
            )

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {f"filter[tag:{filter_key}]": filter_value, "filter[time_scope_value]": -10}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        data_totals = data.get("meta", {}).get("total", {})
        for key in totals:
            expected = totals[key]
            if key == "cost":
                result = data_totals.get(key, {}).get("total", {}).get("value")
            else:
                result = data_totals.get(key, {}).get("value")
            self.assertEqual(result, expected)

    def test_execute_costs_query_with_tag_filter(self):
        """Test that data is filtered by tag key."""
        url = "?filter[type]=pod&filter[time_scope_value]=-10&filter[enabled]=true"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        tag_keys.sort(reverse=True)
        filter_key = tag_keys[0]
        with tenant_context(self.tenant):
            labels = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .filter(pod_labels__has_key=filter_key)
                .values(*["pod_labels"])
                .all()
            )
            label_of_interest = labels[0]
            filter_value = label_of_interest.get("pod_labels", {}).get(filter_key)

            totals = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .filter(**{f"pod_labels__{filter_key}": filter_value})
                .aggregate(
                    cost=Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("memory", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(
                            KeyDecimalTransform("storage", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                    )
                )
            )

        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {f"filter[tag:{filter_key}]": filter_value, "filter[time_scope_value]": -10}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        data_totals = data.get("meta", {}).get("total", {})
        for key in totals:
            expected = totals[key]
            result = data_totals.get(key, {}).get("total", {}).get("value")
            self.assertNotEqual(result, Decimal(0))
            self.assertEqual(result, expected)

    @skip("https://issues.redhat.com/browse/COST-2470")
    def test_execute_query_with_wildcard_tag_filter(self):
        """Test that data is filtered to include entries with tag key."""
        url = "?filter[type]=pod&filter[enabled]=true"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        filter_key = tag_keys[0]

        with tenant_context(self.tenant):
            totals = OCPUsageLineItemDailySummary.objects.filter(
                usage_start__gte=self.ten_days_ago.date(), pod_labels__has_key=filter_key
            ).aggregate(
                **{
                    "usage": Sum("pod_usage_cpu_core_hours"),
                    "request": Sum("pod_request_cpu_core_hours"),
                    "limit": Sum("pod_limit_cpu_core_hours"),
                    "cost": Sum(
                        Coalesce(
                            KeyDecimalTransform("cpu", "supplementary_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_raw_cost"), Value(0, output_field=DecimalField()))
                        + Coalesce(
                            KeyDecimalTransform("cpu", "infrastructure_usage_cost"),
                            Value(0, output_field=DecimalField()),
                        )
                        + Coalesce(F("infrastructure_markup_cost"), Value(0, output_field=DecimalField()))
                    ),
                }
            )

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            f"filter[tag:{filter_key}]": "*",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "filter[resolution]": "daily",
        }

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.data
        data_totals = data.get("meta", {}).get("total", {})
        for data_key in totals:
            with self.subTest(data_key=data_key):
                expected = totals[data_key]
                if data_key == "cost":
                    result = data_totals.get(data_key, {}).get("total", {}).get("value")
                else:
                    result = data_totals.get(data_key, {}).get("value")
                self.assertEqual(result, expected)

    def test_execute_query_with_tag_group_by(self):
        """Test that data is grouped by tag key."""
        url = "?filter[type]=pod&filter[enabled]=false"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        group_by_key = tag_keys[0]

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {f"group_by[tag:{group_by_key}]": "*"}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        data = data.get("data", [])
        expected_keys = ["date", group_by_key + "s"]
        for entry in data:
            self.assertEqual(list(entry.keys()), expected_keys)

    def test_execute_costs_query_with_tag_group_by(self):
        """Test that data is grouped by tag key."""
        url = "?filter[type]=pod&filter[enabled]=false"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        group_by_key = tag_keys[0]

        url = reverse("reports-openshift-costs")
        client = APIClient()
        params = {f"group_by[tag:{group_by_key}]": "*"}

        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        data = data.get("data", [])
        expected_keys = ["date", group_by_key + "s"]
        for entry in data:
            self.assertEqual(list(entry.keys()), expected_keys)

    def test_execute_query_with_group_by_tag_and_limit(self):
        """Test that data is grouped by tag key and limited."""
        client = APIClient()
        tag_key = "storageclass"
        tag_key_plural = f"{tag_key}s"

        url = reverse("reports-openshift-cpu")
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-2",
            "filter[time_scope_units]": "month",
            f"group_by[tag:{tag_key}]": "*",
            "filter[limit]": 2,
        }
        url = f"{url}?{urlencode(params, quote_via=quote_plus)}"
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        data = data.get("data", [])
        previous_tag_usage = data[0].get(tag_key_plural, [])[0].get("values", [{}])[0].get("usage", {}).get("value", 0)
        for entry in data[0].get(tag_key_plural, []):
            current_tag_usage = entry.get("values", [{}])[0].get("usage", {}).get("value", 0)
            if "Other" not in entry.get(tag_key):
                self.assertLessEqual(current_tag_usage, previous_tag_usage)
                previous_tag_usage = current_tag_usage

    def test_execute_query_with_group_by_and_limit(self):
        """Test that data is grouped by and limited."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {"group_by[node]": "*", "filter[limit]": 1}
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        data = data.get("data", [])
        self.assertNotEqual(data, [])
        for entry in data:
            other = entry.get("nodes", [])[-1:]
            if other:
                self.assertIn("Other", other[0].get("node"))

    def test_execute_query_with_group_by_order_by_and_limit(self):
        """Test that data is grouped by and limited on order by."""
        order_by_options = ["cost", "infrastructure", "supplementary", "usage", "request", "limit"]
        order_mapping = ["cost", "infrastructure", "supplementary"]

        for option in order_by_options:
            with self.subTest(test=option):
                client = APIClient()
                order_by_dict_key = f"order_by[{option}]"
                params = {
                    "filter[resolution]": "monthly",
                    "filter[time_scope_value]": "-1",
                    "filter[time_scope_units]": "month",
                    "group_by[node]": "*",
                    order_by_dict_key: "desc",
                    "filter[limit]": 5,
                }

                url = f'{reverse("reports-openshift-cpu")}?' + urlencode(params, quote_via=quote_plus)
                response = client.get(url, **self.headers)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

                data = response.json()
                data = data.get("data", [])
                self.assertTrue(data)
                nodes = data[0].get("nodes", [])
                data_key = None
                if option in order_mapping:
                    data_key = option
                    for node in nodes:
                        if node.get("node") in ("Others", "no-node"):
                            continue
                        previous_value = node.get("values", [])[0].get(data_key, {}).get("total", {}).get("value")
                        break
                else:
                    for node in nodes:
                        if node.get("node") in ("Others", "no-node"):
                            continue
                        previous_value = node.get("values", [])[0].get(option, {}).get("value")
                        break
                for entry in nodes:
                    if entry.get("node", "") in ("Others", "no-node"):
                        continue
                    if data_key:
                        current_value = entry.get("values", [])[0].get(data_key, {}).get("total", {}).get("value")
                    else:
                        current_value = entry.get("values", [])[0].get(option, {}).get("value")
                    self.assertTrue(current_value <= previous_value)
                    previous_value = current_value

    def test_execute_query_with_order_by(self):
        """Test that the possible order by options work."""
        order_by_options = ["cost", "infrastructure", "supplementary", "usage", "request", "limit"]
        for option in order_by_options:
            url = reverse("reports-openshift-cpu")
            client = APIClient()
            order_by_dict_key = f"order_by[{option}]"
            params = {
                "filter[resolution]": "monthly",
                "filter[time_scope_value]": "-1",
                "filter[time_scope_units]": "month",
                order_by_dict_key: "desc",
            }

            url = url + "?" + urlencode(params, quote_via=quote_plus)
            response = client.get(url, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_with_order_by_delta(self):
        """Test that data is grouped and limited by order by delta."""
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            "group_by[cluster]": "*",
            "order_by[delta]": "desc",
            "delta": "usage__capacity",
        }
        url = reverse("reports-openshift-cpu") + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        cluster = data.get("data", [])[0].get("clusters", [])
        p_usage = cluster[0].get("values", [])[0].get("usage", {}).get("value")
        p_cap = cluster[0].get("values", [])[0].get("capacity", {}).get("value")
        previous_usage = p_usage / p_cap
        for entry in cluster:
            c_usage = entry.get("values", [])[0].get("usage", {}).get("value")
            c_cap = entry.get("values", [])[0].get("capacity", {}).get("value")
            current_usage = c_usage / c_cap
            self.assertTrue(current_usage <= previous_usage)
            previous_usage = current_usage

    def test_execute_query_volume(self):
        """Test that the volume endpoint functions."""
        url = reverse("reports-openshift-volume")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        values = data.get("data")[0].get("values")[0]
        self.assertTrue("usage" in values)
        self.assertTrue("request" in values)
        self.assertTrue("cost" in values)
        self.assertEqual(values.get("usage", {}).get("units"), "GB-Mo")

    def test_execute_query_default_pagination(self):
        """Test that the default pagination works."""
        url = reverse("reports-openshift-volume")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        meta = response_data.get("meta", {})
        count = meta.get("count", 0)

        self.assertIn("total", meta)
        self.assertIn("filter", meta)
        self.assertIn("count", meta)

        self.assertEqual(len(data), count)

    def test_execute_query_limit_pagination(self):
        """Test that the default pagination works with a limit."""
        limit = 2
        start_date = self.ten_days_ago.date().strftime("%Y-%m-%d")
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "daily",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "limit": limit,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        meta = response_data.get("meta", {})
        count = meta.get("count", 0)

        self.assertIn("total", meta)
        self.assertIn("count", meta)

        self.assertNotEqual(len(data), count)
        if limit > count:
            self.assertEqual(len(data), count)
        else:
            self.assertEqual(len(data), limit)
        self.assertEqual(data[0].get("date"), start_date)

    def test_execute_query_limit_offset_pagination(self):
        """Test that the default pagination works with an offset."""
        limit = 1
        offset = 1
        start_date = (self.ten_days_ago + datetime.timedelta(days=offset)).date().strftime("%Y-%m-%d")
        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "daily",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "limit": limit,
            "offset": offset,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        meta = response_data.get("meta", {})
        count = meta.get("count", 0)
        self.assertIn("total", meta)
        self.assertIn("count", meta)

        self.assertNotEqual(len(data), count)
        if limit + offset > count:
            self.assertEqual(len(data), max((count - offset), 0))
        else:
            self.assertEqual(len(data), limit)
        self.assertEqual(data[0].get("date"), start_date)

    def test_execute_query_filter_limit_offset_pagination(self):
        """Test that the ranked group pagination works."""
        limit = 1
        offset = 0

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            "group_by[project]": "*",
            "filter[limit]": limit,
            "filter[offset]": offset,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        meta = response_data.get("meta", {})
        count = meta.get("count", 0)

        self.assertIn("total", meta)
        self.assertIn("filter", meta)
        self.assertIn("count", meta)

        for entry in data:
            projects = entry.get("projects", [])
            if limit + offset > count:
                self.assertEqual(len(projects), max((count - offset), 0))
            else:
                self.assertEqual(len(projects), limit)

    def test_execute_query_filter_limit_high_offset_pagination(self):
        """Test that the default pagination works."""
        limit = 1
        offset = 10

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            "group_by[project]": "*",
            "filter[limit]": limit,
            "filter[offset]": offset,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        meta = response_data.get("meta", {})
        count = meta.get("count", 0)

        self.assertIn("total", meta)
        self.assertIn("filter", meta)
        self.assertIn("count", meta)

        for entry in data:
            projects = entry.get("projects", [])
            if limit + offset > count:
                self.assertEqual(len(projects), max((count - offset), 0))
            else:
                self.assertEqual(len(projects), limit)

    def test_execute_query_with_and_filter(self):
        """Test the filter[and:] param in the view."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()

        with tenant_context(self.tenant):
            projects = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .values("namespace")
                .distinct()
            )
            projects = [project.get("namespace") for project in projects]

        params = {
            "filter[resolution]": "daily",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "filter[and:project]": projects,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        for entry in data:
            self.assertEqual(entry.get("values"), [])

    def test_execute_query_with_and_group_by(self):
        """Test the group_by[and:] param in the view."""
        url = reverse("reports-openshift-cpu")
        client = APIClient()

        with tenant_context(self.tenant):
            clusters = (
                OCPUsageLineItemDailySummary.objects.filter(usage_start__gte=self.ten_days_ago.date())
                .values("cluster_id")
                .distinct()
            )
            clusters = [cluster.get("cluster_id") for cluster in clusters]
        params = {
            "filter[resolution]": "daily",
            "filter[time_scope_value]": "-10",
            "filter[time_scope_units]": "day",
            "group_by[and:cluster]": clusters,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        data = response_data.get("data", [])
        for entry in data:
            self.assertEqual(entry.get("clusters"), [])

    def test_execute_query_with_and_tag_filter(self):
        """Test the filter[and:tag:] param in the view."""
        url = "?filter[type]=pod&filter[time_scope_value]=-1&filter[enabled]=true"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        filter_key = tag_keys[0]

        with tenant_context(self.tenant):
            labels = (
                OCPUsageLineItemDailySummary.objects.filter(
                    report_period__report_period_start__gte=self.dh.this_month_start.date()
                )
                .filter(pod_labels__has_key=filter_key)
                .values(*["pod_labels"])
                .all()
            )
            label_of_interest = labels[0]
            filter_value = label_of_interest.get("pod_labels", {}).get(filter_key)

        url = reverse("reports-openshift-cpu")
        client = APIClient()

        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            f"filter[and:tag:{filter_key}]": filter_value,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_execute_query_with_and_tag_group_by(self):
        """Test the group_by[and:tag:] param in the view."""
        url = "?filter[type]=pod&filter[time_scope_value]=-1&filter[enabled]=true"
        query_params = self.mocked_query_params(url, OCPTagView)
        handler = OCPTagQueryHandler(query_params)
        tag_keys = handler.get_tag_keys()
        group_by_key = tag_keys[0]

        with tenant_context(self.tenant):
            labels = (
                OCPUsageLineItemDailySummary.objects.filter(
                    report_period__report_period_start__gte=self.dh.this_month_start.date()
                )
                .filter(pod_labels__has_key=group_by_key)
                .values(*["pod_labels"])
                .all()
            )
            label_of_interest = labels[0]
            group_by_value = label_of_interest.get("pod_labels", {}).get(group_by_key)

        url = reverse("reports-openshift-cpu")
        client = APIClient()
        params = {
            "filter[resolution]": "monthly",
            "filter[time_scope_value]": "-1",
            "filter[time_scope_units]": "month",
            f"group_by[and:tag:{group_by_key}]": group_by_value,
        }
        url = url + "?" + urlencode(params, quote_via=quote_plus)
        response = client.get(url, **self.headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_order_by_tag_wo_group(self):
        """Test that order by tags without a group-by fails."""
        baseurl = reverse("reports-openshift-cpu")
        client = APIClient()

        tag_url = reverse("openshift-tags")
        tag_url = tag_url + "?filter[time_scope_value]=-1&key_only=True"
        response = client.get(tag_url, **self.headers)
        tag_keys = response.data.get("data", [])

        for key in tag_keys:
            order_by_dict_key = f"order_by[tag:{key}]"
            params = {
                "filter[resolution]": "monthly",
                "filter[time_scope_value]": "-1",
                "filter[time_scope_units]": "month",
                order_by_dict_key: random.choice(["asc", "desc"]),
            }

            url = baseurl + "?" + urlencode(params, quote_via=quote_plus)
            response = client.get(url, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_by_tag_w_wrong_group(self):
        """Test that order by tags with a non-matching group-by fails."""
        baseurl = reverse("reports-openshift-cpu")
        client = APIClient()

        tag_url = reverse("openshift-tags")
        tag_url = tag_url + "?filter[time_scope_value]=-1&key_only=True"
        response = client.get(tag_url, **self.headers)
        tag_keys = response.data.get("data", [])

        for key in tag_keys:
            order_by_dict_key = f"order_by[tag:{key}]"
            params = {
                "filter[resolution]": "monthly",
                "filter[time_scope_value]": "-1",
                "filter[time_scope_units]": "month",
                order_by_dict_key: random.choice(["asc", "desc"]),
                "group_by[usage]": random.choice(["asc", "desc"]),
            }

            url = baseurl + "?" + urlencode(params, quote_via=quote_plus)
            response = client.get(url, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_by_tag_w_tag_group(self):
        """Test that order by tags with a matching group-by tag works."""
        baseurl = reverse("reports-openshift-cpu")
        client = APIClient()

        tag_url = reverse("openshift-tags")
        tag_url = tag_url + "?filter[time_scope_value]=-1&key_only=True"
        response = client.get(tag_url, **self.headers)
        tag_keys = response.data.get("data", [])

        for key in tag_keys:
            order_by_dict_key = f"order_by[tag:{key}]"
            group_by_dict_key = f"group_by[tag:{key}]"
            params = {
                "filter[resolution]": "monthly",
                "filter[time_scope_value]": "-1",
                "filter[time_scope_units]": "month",
                order_by_dict_key: random.choice(["asc", "desc"]),
                group_by_dict_key: "*",
            }

            url = baseurl + "?" + urlencode(params, quote_via=quote_plus)
            response = client.get(url, **self.headers)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
