from flask import Blueprint, render_template
from models import ReferenceContent

reference_bp = Blueprint('reference', __name__)


@reference_bp.route('/reference')
def reference_view():
    sections = {}
    items = ReferenceContent.query.order_by(ReferenceContent.sort_order).all()
    for item in items:
        sections.setdefault(item.section, []).append(item)
    return render_template('reference.html', sections=sections)
