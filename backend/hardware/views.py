from rest_framework import generics, mixins
from rest_framework.permissions import IsAuthenticated

from config.permissions import IsAdminUser

from .models import Hardware
from .serializers import HardwareSerializer


class HardwareListView(generics.ListCreateAPIView):
    """GET: hardware listing for any authenticated user.

    Deliberately scoped to Hardware.objects.clean() — records flagged by the
    import for anomalies (duplicate ids, bad dates, unknown statuses, ...)
    never leave the admin. Admin staff work through those in /admin/, which
    has its own login and shows every record, flagged or not.

    POST: admin-only creation of a new hardware record.
    """

    serializer_class = HardwareSerializer
    queryset = Hardware.objects.clean().order_by('name')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdminUser()]
        return [IsAuthenticated()]


class HardwareDetailView(
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, generics.GenericAPIView
):
    """Admin-only management of a single hardware record (partial update + delete).

    Operates over every record, including ones flagged for review, since
    fixing/removing those is exactly what an admin needs this for.
    """

    permission_classes = [IsAdminUser]
    serializer_class = HardwareSerializer
    queryset = Hardware.objects.all()

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
