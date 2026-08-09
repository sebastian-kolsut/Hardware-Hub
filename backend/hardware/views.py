from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, mixins, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.permissions import IsAdminUser

from .models import Hardware
from .serializers import HardwareSerializer

NOT_AVAILABLE_REASONS = {
    Hardware.Status.IN_USE: 'This item is already rented.',
    Hardware.Status.REPAIR: 'This item is in repair and not available for rent.',
}


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


class HardwareRentView(APIView):
    """Rents a hardware item to the calling user, if it's actually eligible.

    Looks the item up out of Hardware.objects.all() (not .clean()) and
    re-checks needs_review here regardless of what queryset any other view
    used to find this id — a flagged item must never become rentable just
    because someone hits this endpoint directly with its id.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        hw = get_object_or_404(Hardware, pk=pk)

        if hw.needs_review:
            return Response(
                {'detail': 'This item is flagged for review and is not eligible for rental.'},
                status=status.HTTP_409_CONFLICT,
            )

        if hw.status != Hardware.Status.AVAILABLE:
            detail = NOT_AVAILABLE_REASONS.get(hw.status, 'This item is not available for rent.')
            return Response({'detail': detail}, status=status.HTTP_409_CONFLICT)

        hw.status = Hardware.Status.IN_USE
        hw.rented_by = request.user
        hw.rented_at = timezone.now()
        hw.save(update_fields=['status', 'rented_by', 'rented_at', 'updated_at'])

        return Response(HardwareSerializer(hw, context={'request': request}).data)


class HardwareReturnView(APIView):
    """Returns a hardware item — only the current renter or an admin may do this."""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        hw = get_object_or_404(Hardware, pk=pk)

        if hw.rented_by_id is None:
            return Response(
                {'detail': 'This item is not currently rented.'},
                status=status.HTTP_409_CONFLICT,
            )

        if hw.rented_by_id != request.user.id and not request.user.is_staff:
            return Response(
                {'detail': 'You do not have permission to return this item.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        hw.status = Hardware.Status.AVAILABLE
        hw.rented_by = None
        hw.rented_at = None
        hw.save(update_fields=['status', 'rented_by', 'rented_at', 'updated_at'])

        return Response(HardwareSerializer(hw, context={'request': request}).data)
