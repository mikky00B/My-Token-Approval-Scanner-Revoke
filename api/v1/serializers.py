"""
API serializers for wallet scanning.
"""

from rest_framework import serializers
from apps.wallets.services.validator import WalletValidator, ValidationError


class ScanRequestSerializer(serializers.Serializer):
    """
    Validates incoming scan requests.
    """

    wallet_address = serializers.CharField(
        max_length=42, required=True, help_text="Ethereum wallet address (0x...)"
    )
    chain_id = serializers.IntegerField(
        default=1, help_text="Blockchain network ID (1 for Ethereum)"
    )

    def validate_wallet_address(self, value):
        """Validate wallet address format."""
        try:
            return WalletValidator.validate_address(value)
        except ValidationError as e:
            raise serializers.ValidationError(str(e))

    def validate_chain_id(self, value):
        """Validate chain is supported."""
        try:
            WalletValidator.validate_chain(value)
            return value
        except ValidationError as e:
            raise serializers.ValidationError(str(e))


class ApprovalSerializer(serializers.Serializer):
    """
    Serializes approval data for API responses.
    """

    token_address = serializers.CharField()
    token_type = serializers.CharField()
    spender_address = serializers.CharField()
    approved_amount = serializers.CharField(allow_null=True)
    is_unlimited = serializers.BooleanField()
    is_operator = serializers.BooleanField()
    risk_points = serializers.IntegerField()
    risk_level = serializers.CharField()
    risk_reasons = serializers.ListField(child=serializers.CharField())


class ScanResultSerializer(serializers.Serializer):
    """
    Serializes complete scan results.
    """

    scan_id = serializers.IntegerField()
    wallet_address = serializers.CharField()
    chain_id = serializers.IntegerField()
    status = serializers.CharField()
    total_approvals = serializers.IntegerField()
    total_risk_score = serializers.IntegerField()
    risk_level = serializers.CharField()
    high_risk_count = serializers.IntegerField()
    critical_risk_count = serializers.IntegerField()
    approvals = ApprovalSerializer(many=True)
    scanned_at = serializers.DateTimeField(source="started_at")
