#
# Copyright 2021 Red Hat Inc.
# SPDX-License-Identifier: Apache-2.0
#
"""Organizations serializers."""
from rest_framework import serializers

from api.report.serializers import add_operator_specified_fields
from api.report.serializers import ExcludeSerializer
from api.report.serializers import FilterSerializer
from api.report.serializers import handle_invalid_fields
from api.report.serializers import ParamSerializer
from api.report.serializers import StringOrListField
from api.report.serializers import validate_field


AWS_FILTER_OP_FIELDS = ["org_unit_id"]


class AWSOrgFilterSerializer(FilterSerializer):
    """Serializer for handling org query parameter filter."""

    org_unit_id = StringOrListField(child=serializers.CharField(), required=False)

    def __init__(self, *args, **kwargs):
        """Initialize the AWSOrgFilterSerializer."""
        super().__init__(*args, **kwargs)
        add_operator_specified_fields(self.fields, AWS_FILTER_OP_FIELDS)


class AWSOrgExcludeSerializer(ExcludeSerializer):
    """Serializer for handling org query parameter filter."""

    org_unit_id = StringOrListField(child=serializers.CharField(), required=False)

    def __init__(self, *args, **kwargs):
        """Initialize the AWSOrgExcludeSerializer."""
        super().__init__(*args, **kwargs)
        add_operator_specified_fields(self.fields, AWS_FILTER_OP_FIELDS)


class OrgQueryParamSerializer(ParamSerializer):
    """Serializer for handling query parameters."""

    exclude = ExcludeSerializer(required=False)
    filter = FilterSerializer(required=False)
    key_only = serializers.BooleanField(default=False)
    limit = serializers.IntegerField(required=False, min_value=1)
    offset = serializers.IntegerField(required=False, min_value=0)

    # DateField defaults: format='iso-8601', input_formats=['iso-8601']
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, data):
        """Validate incoming data.

        Args:
            data    (Dict): data to be validated
        Returns:
            (Dict): Validated data
        Raises:
            (ValidationError): if field inputs are invalid

        """
        super().validate(data)
        handle_invalid_fields(self, data)

        return data


class AWSOrgQueryParamSerializer(OrgQueryParamSerializer):
    """Serializer for handling AWS org query parameters."""

    exclude = AWSOrgExcludeSerializer(required=False)
    filter = AWSOrgFilterSerializer(required=False)

    def validate_exclude(self, value):
        """Validate incoming exlude data.

        Args:
            data    (Dict): data to be validated
        Returns:
            (Dict): Validated data
        Raises:
            (ValidationError): if exclude field inputs are invalid

        """
        validate_field(self, "exclude", AWSOrgExcludeSerializer, value)
        return value

    def validate_filter(self, value):
        """Validate incoming filter data.

        Args:
            data    (Dict): data to be validated
        Returns:
            (Dict): Validated data
        Raises:
            (ValidationError): if filter field inputs are invalid

        """
        validate_field(self, "filter", AWSOrgFilterSerializer, value)
        return value
