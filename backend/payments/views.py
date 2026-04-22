import uuid
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request):
    card_number = str(request.data.get('card_number', '')).replace(' ', '')
    expiry_month = str(request.data.get('expiry_month', '')).strip()
    expiry_year = str(request.data.get('expiry_year', '')).strip()
    cvv = str(request.data.get('cvv', '')).strip()

    if len(card_number) < 13:
        return Response({'approved': False, 'reason': 'Invalid card number.'}, status=400)
    if not expiry_month or not expiry_year:
        return Response({'approved': False, 'reason': 'Invalid expiry date.'}, status=400)
    if len(cvv) < 3:
        return Response({'approved': False, 'reason': 'Invalid CVV.'}, status=400)

    return Response({
        'approved': True,
        'transaction_id': f'TXN-{uuid.uuid4().hex[:12].upper()}',
        'last4': card_number[-4:],
    })
