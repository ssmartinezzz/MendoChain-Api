"""Input and output DTOs. Input serializers only validate; output serializers only render."""
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from api.traceability.domain.roles import Role
from api.traceability.models import Actor, Transaction, Wine

WINE_FIELDS = ('variety_name', 'content', 'alcohol', 'brand_name', 'lote', 'year')


class WineUpdateInputSerializer(serializers.ModelSerializer):
    """Description only: the lot size is fixed on chain."""

    class Meta:
        model = Wine
        fields = WINE_FIELDS


class WineCreateInputSerializer(WineUpdateInputSerializer):
    total_quantity = serializers.IntegerField(min_value=1)

    class Meta(WineUpdateInputSerializer.Meta):
        fields = (*WINE_FIELDS, 'total_quantity')


class WineOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wine
        fields = ('id', *WINE_FIELDS, 'visibility', 'total_quantity', 'producer')
        read_only_fields = fields


class MovementInputSerializer(serializers.Serializer):
    wine = serializers.PrimaryKeyRelatedField(queryset=Wine.objects.all())
    recipient = serializers.PrimaryKeyRelatedField(queryset=Actor.objects.filter(revoked_at__isnull=True))
    quantity = serializers.IntegerField(min_value=1)


class MovementOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'quantity', 'transaction_id', 'wine', 'visibility', 'sender', 'recipient')
        read_only_fields = fields


class ActorInputSerializer(serializers.Serializer):
    user = serializers.PrimaryKeyRelatedField(queryset=get_user_model().objects.all())
    role = serializers.ChoiceField(choices=[role.value for role in Role])


class ActorOutputSerializer(serializers.ModelSerializer):
    """Public view of an actor: never the email or the key."""

    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()

    class Meta:
        model = Actor
        fields = ('id', 'name', 'role', 'address')
        read_only_fields = fields

    def get_name(self, actor):
        return actor.user.get_full_name() or f'Actor {actor.pk}'

    def get_role(self, actor):
        return Role(actor.role).name.lower()


class MemberInputSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    role = serializers.ChoiceField(choices=[role.value for role in Role])

    def validate_password(self, value):
        validate_password(value)
        return value


class MemberOutputSerializer(serializers.ModelSerializer):
    """Admin view of a user and its supply-chain actor, if any. Never exposes keys."""

    email = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    actor = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = ('id', 'email', 'name', 'is_staff', 'actor')
        read_only_fields = fields

    def get_email(self, user):
        return user.email or user.username

    def get_name(self, user):
        return user.get_full_name()

    def get_actor(self, user):
        actor = getattr(user, 'actor', None)
        if actor is None:
            return None
        return {
            'id': actor.pk,
            'role': Role(actor.role).name.lower(),
            'address': actor.address,
            'revoked': actor.revoked_at is not None,
        }
