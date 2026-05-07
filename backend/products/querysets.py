from django.db.models import (
    Avg,
    BooleanField,
    Case,
    Count,
    FloatField,
    IntegerField,
    OuterRef,
    Subquery,
    TextField,
    Value,
    Sum,
    When,
)
from django.db.models.functions import Coalesce, Round

from .models import Review, SneakerImage, SneakerSize


def sneaker_summary_queryset(queryset):
    total_stock_subquery = (
        SneakerSize.objects.filter(sneaker=OuterRef('pk'))
        .order_by()
        .values('sneaker')
        .annotate(total=Coalesce(Sum('stock'), 0))
        .values('total')[:1]
    )
    average_rating_subquery = (
        Review.objects.filter(sneaker=OuterRef('pk'))
        .order_by()
        .values('sneaker')
        .annotate(avg=Round(Avg('rating'), 1))
        .values('avg')[:1]
    )
    rating_count_subquery = (
        Review.objects.filter(sneaker=OuterRef('pk'))
        .order_by()
        .values('sneaker')
        .annotate(total=Count('id'))
        .values('total')[:1]
    )
    primary_image_subquery = (
        SneakerImage.objects.filter(sneaker=OuterRef('pk'))
        .order_by('-is_primary', 'order', 'id')
        .values('image')[:1]
    )
    latest_approved_comment_subquery = (
        Review.objects.filter(sneaker=OuterRef('pk'), status='approved')
        .exclude(comment='')
        .order_by('-created_at')
        .values('comment')[:1]
    )

    return queryset.annotate(
        _total_stock=Coalesce(
            Subquery(total_stock_subquery),
            Value(0),
            output_field=IntegerField(),
        ),
        average_rating=Subquery(
            average_rating_subquery,
            output_field=FloatField(),
        ),
        rating_count=Coalesce(
            Subquery(rating_count_subquery),
            Value(0),
            output_field=IntegerField(),
        ),
        primary_image=Subquery(
            primary_image_subquery,
            output_field=TextField(),
        ),
        latest_approved_comment=Coalesce(
            Subquery(latest_approved_comment_subquery),
            Value(''),
            output_field=TextField(),
        ),
    ).annotate(
        _is_in_stock=Case(
            When(_total_stock__gt=0, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    )


def sneaker_detail_queryset(queryset):
    review_count_subquery = (
        Review.objects.filter(sneaker=OuterRef('pk'), status='approved')
        .exclude(comment='')
        .order_by()
        .values('sneaker')
        .annotate(total=Count('id'))
        .values('total')[:1]
    )

    return sneaker_summary_queryset(queryset).annotate(
        review_count=Coalesce(
            Subquery(review_count_subquery),
            Value(0),
            output_field=IntegerField(),
        )
    )
