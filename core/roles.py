"""CRM role helpers — used by permissions, middleware, and JWT."""

from django.contrib.auth import get_user_model

User = get_user_model()

ROLE_SUPER_ADMIN = 'super_admin'
ROLE_ADMIN = 'admin'
ROLE_STAFF = 'staff'
ROLE_TECHNICIAN = 'technician'
ROLE_BLOG_USER = 'blog_user'

CRM_OPERATIONAL_ROLES = frozenset({
    ROLE_SUPER_ADMIN,
    ROLE_ADMIN,
    ROLE_STAFF,
    ROLE_TECHNICIAN,
})
BLOG_CMS_ROLES = frozenset({ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_STAFF, ROLE_BLOG_USER})

ROLE_DISPLAY = {
    ROLE_SUPER_ADMIN: 'Super Admin',
    ROLE_ADMIN: 'Admin',
    ROLE_STAFF: 'Staff',
    ROLE_TECHNICIAN: 'Technician',
    ROLE_BLOG_USER: 'Blog User',
}

DISPLAY_TO_ROLE = {v: k for k, v in ROLE_DISPLAY.items()}
DISPLAY_TO_ROLE['Blog User'] = ROLE_BLOG_USER


def get_user_profile(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    return getattr(user, 'crm_profile', None)


def get_user_role(user) -> str | None:
    """Resolve CRM role for a user."""
    if not user or not getattr(user, 'is_authenticated', False):
        return None

    profile = get_user_profile(user)
    if profile is not None:
        return profile.role

    # Legacy users without profile
    if user.is_superuser:
        return ROLE_SUPER_ADMIN
    if user.is_staff:
        return ROLE_STAFF
    return None


def is_blog_user(user) -> bool:
    return get_user_role(user) == ROLE_BLOG_USER


def is_crm_operational_user(user) -> bool:
    return get_user_role(user) in CRM_OPERATIONAL_ROLES


def can_access_blog_cms(user) -> bool:
    return get_user_role(user) in BLOG_CMS_ROLES


def role_display(user) -> str:
    role = get_user_role(user)
    if role:
        return ROLE_DISPLAY.get(role, role)
    return 'Unknown'


def ensure_user_profile(user, role: str | None = None):
    """Create or update UserProfile for a user."""
    from .models import UserProfile, CRMRole

    profile, created = UserProfile.objects.get_or_create(user=user)
    if role is not None:
        profile.role = role
        profile.save(update_fields=['role', 'updated_at'])
    elif created:
        if user.is_superuser:
            profile.role = CRMRole.SUPER_ADMIN
        elif user.is_staff:
            profile.role = CRMRole.STAFF
        profile.save(update_fields=['role', 'updated_at'])
    return profile
