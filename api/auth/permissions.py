from rest_framework import permissions


class IsSelfOrAdmin(permissions.BasePermission):
    """Allows access only to the user the object represents, or to staff."""

    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user
