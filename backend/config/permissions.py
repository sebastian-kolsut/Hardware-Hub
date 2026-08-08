from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    """Grants access only to staff users — our admin role for this MVP.

    Defined once here and reused by every admin-only view instead of each
    view checking `request.user.is_staff` itself.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)
