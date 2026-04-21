"""Betting guides routes."""
from flask import Blueprint
from ..extensions import cache
from ..models.guide import Guide
from ..utils.helpers import json_error, json_success

guides_bp = Blueprint('guides', __name__)


@guides_bp.route('/', methods=['GET'])
@cache.cached(timeout=3600)
def get_guides():
    """Get list of published guides."""
    guides = Guide.query.filter_by(published=True).order_by(Guide.created_at.desc()).all()

    return json_success(data={
        'guides': [guide.to_dict(include_body=False) for guide in guides]
    })


@guides_bp.route('/<slug>', methods=['GET'])
@cache.cached(timeout=3600)
def get_guide(slug):
    """Get single guide by slug."""
    guide = Guide.query.filter_by(slug=slug, published=True).first()

    if not guide:
        return json_error('Guide not found', 404)

    return json_success(data=guide.to_dict())


@guides_bp.route('/sport/<sport_name>', methods=['GET'])
@cache.cached(timeout=3600)
def get_guides_by_sport(sport_name):
    """Get guides for a specific sport."""
    from ..models.sport import Sport

    sport = Sport.query.filter_by(name=sport_name.lower()).first()

    if not sport:
        return json_error('Sport not found', 404)

    guides = Guide.query.filter_by(
        sport_id=sport.id,
        published=True
    ).order_by(Guide.created_at.desc()).all()

    return json_success(data={
        'sport': sport.to_dict(),
        'guides': [guide.to_dict(include_body=False) for guide in guides]
    })
