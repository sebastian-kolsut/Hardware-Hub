from rest_framework import generics

from .models import Hardware
from .serializers import HardwareSerializer


class HardwareListView(generics.ListAPIView):
    """Public hardware listing.

    Deliberately scoped to Hardware.objects.clean() — records flagged by the
    import for anomalies (duplicate ids, bad dates, unknown statuses, ...)
    never leave the admin. Admin staff work through those in /admin/, which
    has its own login and shows every record, flagged or not.
    """

    serializer_class = HardwareSerializer
    queryset = Hardware.objects.clean().order_by('name')
