from rest_framework import permissions

from .models import UserRole


class IsAdminUser(permissions.BasePermission):
    """Allow access only to users with is_staff=True or is_superuser=True.
    Used only for the Django admin panel itself."""

    message = "Admin or staff access required."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_staff or request.user.is_superuser
        ))


class IsGoogleAuthenticated(permissions.BasePermission):
    """Allow access to any user authenticated via Google OAuth.
    This is the permission class for all Workspace Operations endpoints —
    any user who has completed Google OAuth login can perform admin operations.
    No Django staff/superuser status is required.
    """

    message = "Google OAuth login required. Please sign in with your Google account."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsOperatorOrAdmin(permissions.BasePermission):
    """Allow operator/admin role users. Staff/superusers are always allowed."""

    message = "Operator or admin role required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return getattr(user, "role", UserRole.OPERATOR) in {UserRole.OPERATOR, UserRole.ADMIN}


class IsAdminOrStaff(permissions.BasePermission):
    """Allow only admin role users, staff, or superusers."""

    message = "Admin role required."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return getattr(user, "role", UserRole.OPERATOR) == UserRole.ADMIN
