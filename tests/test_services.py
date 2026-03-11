"""
Service layer tests — verify shared mutation behavior for UI and chat paths.

Validates that services produce correct side effects: DB writes, cascades,
and validation. Socket.IO emits are tested via mock.
Run: python -m pytest tests/test_services.py -v
"""
import pytest
from unittest.mock import patch
from datetime import datetime

from app import create_app
from models import (db, Activity, Day, AccommodationOption, AccommodationLocation,
                    ChecklistItem, ChecklistOption)


@pytest.fixture(scope='module')
def svc_app():
    """Create app for service mutation tests.

    Uses the standard create_app() which reads from data/japan_trip.db.
    Service tests may mutate this DB, but smoke tests also use it with
    module scope. pytest runs modules in file-name order, so test_services
    runs first. We accept that mutations persist — tests are written to
    be order-independent and only verify behavior, not final state.
    """
    app = create_app(run_data_migrations=False)
    app.config['TESTING'] = True
    with app.app_context():
        yield app


@pytest.fixture(autouse=True)
def ctx(svc_app):
    """Provide app context for each test."""
    with svc_app.app_context():
        yield svc_app


# ---- Activity Services ----

class TestActivityToggle:
    def test_toggle_sets_completed_and_timestamp(self, ctx):
        from services.activities import toggle
        act = Activity.query.filter_by(is_completed=False).first()
        assert act is not None
        aid = act.id
        with patch('services.activities.socketio'):
            result = toggle(aid)
        assert result.is_completed is True
        assert result.completed_at is not None
        # Toggle back
        with patch('services.activities.socketio'):
            result = toggle(aid)
        assert result.is_completed is False
        assert result.completed_at is None

    def test_toggle_emits_socketio(self, ctx):
        from services.activities import toggle
        act = Activity.query.filter_by(is_completed=False).first()
        with patch('services.activities.socketio') as mock_sio:
            toggle(act.id)
            mock_sio.emit.assert_called_once()
            args = mock_sio.emit.call_args
            assert args[0][0] == 'activity_toggled'
            assert args[0][1]['id'] == act.id


class TestActivityAdd:
    def test_add_validates_time_slot(self, ctx):
        from services.activities import add
        day = Day.query.first()
        with pytest.raises(ValueError, match='time_slot'):
            with patch('services.activities.socketio'):
                add(day.id, {'title': 'Test', 'time_slot': 'invalid_slot'})

    def test_add_validates_negative_cost(self, ctx):
        from services.activities import add
        day = Day.query.first()
        with pytest.raises(ValueError):
            with patch('services.activities.socketio'):
                add(day.id, {'title': 'Test', 'cost_per_person': -5})

    def test_add_creates_activity(self, ctx):
        from services.activities import add
        day = Day.query.first()
        with patch('services.activities.socketio'):
            result = add(day.id, {
                'title': '__test_svc_activity__',
                'time_slot': 'morning',
            })
        assert result.id is not None
        assert result.title == '__test_svc_activity__'
        # Clean up
        db.session.delete(result)
        db.session.commit()


class TestActivityEliminate:
    def test_eliminate_toggles(self, ctx):
        from services.activities import eliminate
        act = Activity.query.filter_by(is_eliminated=False).first()
        result = eliminate(act.id)
        assert result.is_eliminated is True
        result = eliminate(act.id)
        assert result.is_eliminated is False


# ---- Accommodation Services ----

class TestAccommodationSelect:
    def test_select_deselects_siblings(self, ctx):
        from services.accommodations import select
        # Find a location with multiple options
        loc = AccommodationLocation.query.first()
        options = AccommodationOption.query.filter_by(location_id=loc.id).all()
        if len(options) < 2:
            pytest.skip('Need 2+ options to test select')
        # Remember original selection to restore after
        original = next((o for o in options if o.is_selected), None)
        with patch('services.accommodations.socketio'):
            select(options[1].id)
        refreshed = AccommodationOption.query.filter_by(
            location_id=loc.id, is_selected=True).all()
        assert len(refreshed) == 1
        assert refreshed[0].id == options[1].id
        # Restore original selection
        if original:
            with patch('services.accommodations.socketio'):
                select(original.id)


class TestAccommodationUpdateStatus:
    def test_rejects_invalid_status(self, ctx):
        from services.accommodations import update_status
        opt = AccommodationOption.query.filter_by(is_selected=True).first()
        with pytest.raises(ValueError):
            with patch('services.accommodations.socketio'):
                update_status(opt.id, {'booking_status': 'nonexistent_status'})

    def test_confirmed_requires_document(self, ctx):
        from services.accommodations import update_status
        # Find an option without a document
        opt = AccommodationOption.query.filter(
            AccommodationOption.document_id.is_(None)
        ).first()
        if not opt:
            pytest.skip('All options have documents')
        with pytest.raises(ValueError, match='document'):
            with patch('services.accommodations.socketio'):
                update_status(opt.id, {'booking_status': 'confirmed'})

    def test_update_cascades_to_checklist(self, ctx):
        from services.accommodations import update_status
        # Find an option whose location has a linked checklist item
        cl = ChecklistItem.query.filter(
            ChecklistItem.accommodation_location_id.isnot(None)
        ).first()
        if not cl:
            pytest.skip('No linked checklist items')
        opt = AccommodationOption.query.filter_by(
            location_id=cl.accommodation_location_id, is_selected=True
        ).first()
        if not opt:
            pytest.skip('No selected option for linked checklist')
        orig_status = opt.booking_status
        orig_cl_status = cl.status
        with patch('services.accommodations.socketio'):
            update_status(opt.id, {'booking_status': 'booked'})
        db.session.refresh(cl)
        assert cl.status == 'booked'
        # Restore
        opt.booking_status = orig_status
        cl.status = orig_cl_status
        db.session.commit()

    def test_validates_negative_price(self, ctx):
        from services.accommodations import update_status
        opt = AccommodationOption.query.first()
        with pytest.raises(ValueError):
            with patch('services.accommodations.socketio'):
                update_status(opt.id, {'price_low': -100})


class TestAccommodationEliminate:
    def test_cannot_eliminate_booked(self, ctx):
        from services.accommodations import eliminate
        opt = AccommodationOption.query.filter_by(booking_status='booked').first()
        if not opt:
            pytest.skip('No booked options')
        with pytest.raises(ValueError, match='Cannot eliminate'):
            with patch('services.accommodations.socketio'):
                eliminate(opt.id, eliminate=True)


# ---- Checklist Services ----

class TestChecklistToggle:
    def test_toggle_syncs_status_field(self, ctx):
        from services.checklists import toggle
        item = ChecklistItem.query.filter_by(is_completed=False).first()
        with patch('services.checklists.socketio'):
            result = toggle(item.id)
        assert result.is_completed is True
        assert result.status == 'completed'
        with patch('services.checklists.socketio'):
            result = toggle(item.id)
        assert result.is_completed is False
        assert result.status == 'pending'


class TestChecklistUpdateStatus:
    def test_rejects_invalid_status(self, ctx):
        from services.checklists import update_status
        item = ChecklistItem.query.first()
        with pytest.raises(ValueError, match='Invalid status'):
            with patch('services.checklists.socketio'):
                update_status(item.id, 'bogus')

    def test_cascades_to_accommodation(self, ctx):
        from services.checklists import update_status
        cl = ChecklistItem.query.filter(
            ChecklistItem.accommodation_location_id.isnot(None)
        ).first()
        if not cl:
            pytest.skip('No linked checklist items')
        opt = AccommodationOption.query.filter_by(
            location_id=cl.accommodation_location_id, is_selected=True
        ).first()
        if not opt:
            pytest.skip('No selected option')
        orig_opt_status = opt.booking_status
        orig_cl_status = cl.status
        with patch('services.checklists.socketio'):
            update_status(cl.id, 'booked')
        db.session.refresh(opt)
        assert opt.booking_status in ('booked', 'confirmed')
        # Restore
        opt.booking_status = orig_opt_status
        cl.status = orig_cl_status
        db.session.commit()


class TestChecklistCreate:
    def test_rejects_invalid_category(self, ctx):
        from services.checklists import create
        with pytest.raises(ValueError, match='Cannot add'):
            with patch('services.checklists.socketio'):
                create({'title': 'Test', 'category': 'accommodation'})

    def test_creates_item(self, ctx):
        from services.checklists import create
        with patch('services.checklists.socketio'):
            item = create({'title': '__test_svc_checklist__', 'category': 'packing_essential'})
        assert item.id is not None
        assert item.status == 'pending'
        # Clean up
        db.session.delete(item)
        db.session.commit()


class TestChecklistDelete:
    def test_enforces_category_restriction(self, ctx):
        from services.checklists import delete
        # Find an accommodation checklist item (not deletable)
        item = ChecklistItem.query.filter_by(category='accommodation').first()
        if not item:
            pytest.skip('No accommodation checklist items')
        with pytest.raises(ValueError, match='Cannot delete'):
            with patch('services.checklists.socketio'):
                delete(item.id, enforce_category=True)

    def test_bypass_category_for_chat(self, ctx):
        """Chat tools pass enforce_category=False to delete any item."""
        from services.checklists import create, delete
        with patch('services.checklists.socketio'):
            item = create({'title': '__test_del__', 'category': 'packing_essential'})
            delete(item.id, enforce_category=False)
        assert ChecklistItem.query.get(item.id) is None
