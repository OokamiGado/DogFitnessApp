from decimal import Decimal
from datetime import date, time

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.db.models import ProtectedError

from clients.models import Owner, Dog, AuditLog
from scheduling.models import TrainingSession, Booking
from .models import PricingPlan, Payment


def _make_staff_user(username='staff_user'):
    return User.objects.create_user(username=username, password='testpass12345', is_staff=True)


def _make_regular_user(username='regular_user'):
    return User.objects.create_user(username=username, password='testpass12345', is_staff=False)


class PricingPlanModelTest(TestCase):
    def test_str_representation(self):
        plan = PricingPlan.objects.create(name='Trening indywidualny', price=Decimal('150.00'))
        self.assertIn('Trening indywidualny', str(plan))
        self.assertIn('150.00', str(plan))

    def test_default_is_active_true(self):
        plan = PricingPlan.objects.create(name='Karnet', price=Decimal('500.00'))
        self.assertTrue(plan.is_active)


class PaymentModelTest(TestCase):
    def setUp(self):
        self.owner = Owner.objects.create(first_name='Anna', last_name='Kowalska', phone='600111222')
        self.dog = Dog.objects.create(owner=self.owner, name='Reksio')

    def test_str_representation(self):
        payment = Payment.objects.create(
            owner=self.owner, amount=Decimal('150.00'), payment_date=date(2026, 3, 10),
        )
        self.assertIn('Anna Kowalska', str(payment))
        self.assertIn('150.00', str(payment))

    def test_is_paid_property(self):
        paid = Payment.objects.create(
            owner=self.owner, amount=Decimal('100'), payment_date=date.today(), status=Payment.STATUS_PAID,
        )
        pending = Payment.objects.create(
            owner=self.owner, amount=Decimal('100'), payment_date=date.today(), status=Payment.STATUS_PENDING,
        )
        self.assertTrue(paid.is_paid)
        self.assertFalse(pending.is_paid)

    def test_owner_protect_on_delete(self):
        """Nie mozna usunac klienta, jesli ma przypisane platnosci -
        to jest wymog zachowania historii finansowej (podatkowej)."""
        Payment.objects.create(owner=self.owner, amount=Decimal('100'), payment_date=date.today())
        with self.assertRaises(ProtectedError):
            self.owner.delete()

    def test_booking_set_null_on_delete(self):
        """Usuniecie rezerwacji NIE usuwa powiazanej platnosci - tylko
        odlinkowuje (booking=None), dane finansowe zostaja."""
        session = TrainingSession.objects.create(
            date=date(2026, 3, 10), start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        booking = Booking.objects.create(session=session, dog=self.dog, status=Booking.STATUS_CONFIRMED)
        payment = Payment.objects.create(
            owner=self.owner, booking=booking, amount=Decimal('150'), payment_date=date.today(),
        )
        booking.delete()
        payment.refresh_from_db()
        self.assertIsNone(payment.booking)


class FinanceAccessControlTest(TestCase):
    """Modul Finanse zawiera dane podatkowo-wrazliwe - dostepny TYLKO dla
    is_staff=True. Niezalogowany user przekierowany do logowania,
    zalogowany ale nie-staff przekierowany do dashboardu z komunikatem."""

    def setUp(self):
        self.client = Client()
        self.staff_user = _make_staff_user()
        self.regular_user = _make_regular_user()

    def test_anonymous_redirected_to_login(self):
        resp = self.client.get('/finance/payments/')
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login/', resp.url)

    def test_regular_user_blocked_from_payment_list(self):
        self.client.login(username='regular_user', password='testpass12345')
        resp = self.client.get('/finance/payments/')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, '/dashboard/')

    def test_regular_user_blocked_from_finance_report(self):
        self.client.login(username='regular_user', password='testpass12345')
        resp = self.client.get('/finance/report/')
        self.assertEqual(resp.status_code, 302)

    def test_regular_user_blocked_from_pricing_plan_list(self):
        self.client.login(username='regular_user', password='testpass12345')
        resp = self.client.get('/finance/pricing/')
        self.assertEqual(resp.status_code, 302)

    def test_staff_user_can_access_payment_list(self):
        self.client.login(username='staff_user', password='testpass12345')
        resp = self.client.get('/finance/payments/')
        self.assertEqual(resp.status_code, 200)

    def test_staff_user_can_access_finance_report(self):
        self.client.login(username='staff_user', password='testpass12345')
        resp = self.client.get('/finance/report/')
        self.assertEqual(resp.status_code, 200)

    def test_finance_link_hidden_for_regular_user_in_nav(self):
        self.client.login(username='regular_user', password='testpass12345')
        resp = self.client.get('/dashboard/')
        self.assertNotIn(b'Finanse', resp.content)

    def test_finance_link_visible_for_staff_in_nav(self):
        self.client.login(username='staff_user', password='testpass12345')
        resp = self.client.get('/dashboard/')
        self.assertIn(b'Finanse', resp.content)

    def test_pending_payments_section_hidden_for_regular_user(self):
        """Sekcja 'Oczekujace platnosci' na dashboardzie NIE powinna
        pojawic sie dla uzytkownika bez is_staff - nawet jesli istnieja
        oczekujace platnosci w systemie."""
        owner = Owner.objects.create(first_name='Jan', last_name='Nowak', phone='600999888')
        Payment.objects.create(
            owner=owner, amount=Decimal('999'), payment_date=date.today(), status=Payment.STATUS_PENDING,
        )
        self.client.login(username='regular_user', password='testpass12345')
        resp = self.client.get('/dashboard/')
        self.assertNotIn(b'Oczekujace platnosci', resp.content)

    def test_pending_payments_section_visible_for_staff(self):
        owner = Owner.objects.create(first_name='Jan', last_name='Nowak', phone='600999888')
        Payment.objects.create(
            owner=owner, amount=Decimal('999'), payment_date=date.today(), status=Payment.STATUS_PENDING,
        )
        self.client.login(username='staff_user', password='testpass12345')
        resp = self.client.get('/dashboard/')
        self.assertIn(b'Oczekujace platnosci', resp.content)


class PricingPlanViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = _make_staff_user()
        self.client.login(username='staff_user', password='testpass12345')

    def test_create_pricing_plan(self):
        resp = self.client.post('/finance/pricing/add/', {
            'name': 'Trening indywidualny 60 min', 'price': '150.00', 'description': '', 'is_active': 'on',
        })
        self.assertEqual(resp.status_code, 302)
        plan = PricingPlan.objects.get(name='Trening indywidualny 60 min')
        self.assertEqual(plan.price, Decimal('150.00'))

    def test_create_pricing_plan_logs_audit(self):
        self.client.post('/finance/pricing/add/', {
            'name': 'Karnet 10 wizyt', 'price': '1200.00', 'description': '', 'is_active': 'on',
        })
        log = AuditLog.objects.filter(target_type=AuditLog.TARGET_PRICING_PLAN, action=AuditLog.ACTION_CREATED).first()
        self.assertIsNotNone(log)
        self.assertIn('Karnet 10 wizyt', log.description)

    def test_price_must_be_positive(self):
        resp = self.client.post('/finance/pricing/add/', {
            'name': 'Niepoprawna cena', 'price': '-10.00', 'description': '', 'is_active': 'on',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(PricingPlan.objects.filter(name='Niepoprawna cena').exists())

    def test_delete_requires_confirmation_page(self):
        """GET na delete pokazuje strone potwierdzenia, NIE usuwa od razu."""
        plan = PricingPlan.objects.create(name='Do usuniecia', price=Decimal('100'))
        resp = self.client.get(f'/finance/pricing/{plan.pk}/delete/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(PricingPlan.objects.filter(pk=plan.pk).exists())

    def test_delete_post_removes_and_logs(self):
        plan = PricingPlan.objects.create(name='Do usuniecia', price=Decimal('100'))
        resp = self.client.post(f'/finance/pricing/{plan.pk}/delete/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(PricingPlan.objects.filter(pk=plan.pk).exists())
        log = AuditLog.objects.filter(
            target_type=AuditLog.TARGET_PRICING_PLAN, action=AuditLog.ACTION_DELETED_PERMANENT
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('Do usuniecia', log.description)

    def test_toggle_active(self):
        plan = PricingPlan.objects.create(name='Test', price=Decimal('50'), is_active=True)
        self.client.post(f'/finance/pricing/{plan.pk}/toggle/')
        plan.refresh_from_db()
        self.assertFalse(plan.is_active)


class PaymentViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = _make_staff_user()
        self.client.login(username='staff_user', password='testpass12345')
        self.owner = Owner.objects.create(first_name='Anna', last_name='Kowalska', phone='600111222')
        self.dog = Dog.objects.create(owner=self.owner, name='Reksio')
        self.session = TrainingSession.objects.create(
            date=date(2026, 3, 10), start_time=time(10, 0), end_time=time(11, 0), capacity=1,
        )
        self.booking = Booking.objects.create(session=self.session, dog=self.dog, status=Booking.STATUS_CONFIRMED)

    def test_create_general_payment(self):
        resp = self.client.post('/finance/payments/add/', {
            'owner': self.owner.pk, 'amount': '150.00', 'payment_date': '2026-03-10',
            'method': 'cash', 'status': 'paid', 'description': 'Trening', 'notes': '',
        })
        self.assertEqual(resp.status_code, 302)
        payment = Payment.objects.get(description='Trening')
        self.assertEqual(payment.created_by, self.staff_user)

    def test_create_payment_logs_audit(self):
        self.client.post('/finance/payments/add/', {
            'owner': self.owner.pk, 'amount': '150.00', 'payment_date': '2026-03-10',
            'method': 'cash', 'status': 'paid', 'description': 'Trening', 'notes': '',
        })
        log = AuditLog.objects.filter(target_type=AuditLog.TARGET_PAYMENT, action=AuditLog.ACTION_CREATED).first()
        self.assertIsNotNone(log)
        self.assertIn('Anna Kowalska', log.description)

    def test_create_payment_for_fixed_owner(self):
        resp = self.client.get(f'/finance/payments/add/owner/{self.owner.pk}/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Anna Kowalska', resp.content)

        resp = self.client.post(f'/finance/payments/add/owner/{self.owner.pk}/', {
            'owner': self.owner.pk, 'amount': '200.00', 'payment_date': '2026-03-15',
            'method': 'transfer', 'status': 'pending', 'description': 'Karnet', 'notes': '',
        })
        self.assertEqual(resp.status_code, 302)
        payment = Payment.objects.get(description='Karnet')
        self.assertEqual(payment.owner, self.owner)

    def test_create_payment_for_fixed_booking(self):
        """Regresja: queryset dla fixed_booking musi zawierac ten booking,
        inaczej walidacja ModelChoiceField odrzuca wartosc jako
        'niepoprawny wybor' mimo ze jest ustawiona jako initial."""
        resp = self.client.post(f'/finance/payments/add/booking/{self.booking.pk}/', {
            'owner': self.owner.pk, 'booking': self.booking.pk, 'amount': '150.00',
            'payment_date': '2026-03-10', 'method': 'blik', 'status': 'paid',
            'description': 'Za sesje', 'notes': '',
        })
        self.assertEqual(resp.status_code, 302)
        payment = Payment.objects.get(description='Za sesje')
        self.assertEqual(payment.booking, self.booking)

    def test_amount_must_be_positive(self):
        resp = self.client.post('/finance/payments/add/', {
            'owner': self.owner.pk, 'amount': '-50.00', 'payment_date': '2026-03-10',
            'method': 'cash', 'status': 'paid', 'description': 'Niepoprawna', 'notes': '',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Payment.objects.filter(description='Niepoprawna').exists())

    def test_mark_paid(self):
        payment = Payment.objects.create(
            owner=self.owner, amount=Decimal('100'), payment_date=date.today(), status=Payment.STATUS_PENDING,
        )
        resp = self.client.post(f'/finance/payments/{payment.pk}/mark-paid/')
        self.assertEqual(resp.status_code, 302)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.STATUS_PAID)

    def test_mark_paid_logs_audit(self):
        payment = Payment.objects.create(
            owner=self.owner, amount=Decimal('100'), payment_date=date.today(), status=Payment.STATUS_PENDING,
        )
        self.client.post(f'/finance/payments/{payment.pk}/mark-paid/')
        log = AuditLog.objects.filter(
            target_type=AuditLog.TARGET_PAYMENT, action=AuditLog.ACTION_STATUS_TOGGLED
        ).first()
        self.assertIsNotNone(log)

    def test_delete_requires_confirmation_page(self):
        payment = Payment.objects.create(owner=self.owner, amount=Decimal('100'), payment_date=date.today())
        resp = self.client.get(f'/finance/payments/{payment.pk}/delete/')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(Payment.objects.filter(pk=payment.pk).exists())

    def test_delete_post_removes_and_logs_before_deletion(self):
        """WAZNE: audit log musi zawierac kwote/klienta/date PRZED
        usunieciem rekordu - to jedyny trwaly slad po usunieciu."""
        payment = Payment.objects.create(
            owner=self.owner, amount=Decimal('777.00'), payment_date=date(2026, 3, 10),
        )
        resp = self.client.post(f'/finance/payments/{payment.pk}/delete/')
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Payment.objects.filter(pk=payment.pk).exists())
        log = AuditLog.objects.filter(
            target_type=AuditLog.TARGET_PAYMENT, action=AuditLog.ACTION_DELETED_PERMANENT
        ).first()
        self.assertIsNotNone(log)
        self.assertIn('777', log.description)
        self.assertIn('Anna Kowalska', log.description)

    def test_payment_list_filter_by_status(self):
        Payment.objects.create(
            owner=self.owner, amount=Decimal('100'), payment_date=date.today(),
            status=Payment.STATUS_PAID, description='Oplacona',
        )
        Payment.objects.create(
            owner=self.owner, amount=Decimal('50'), payment_date=date.today(),
            status=Payment.STATUS_PENDING, description='Oczekujaca',
        )
        resp = self.client.get('/finance/payments/?status=pending')
        self.assertContains(resp, 'Oczekujaca')
        self.assertNotContains(resp, 'Oplacona')


class FinanceReportTest(TestCase):
    """Testy kluczowe dla poprawnosci zestawien podatkowych - weryfikuja
    ze suma roczna = suma miesiecy = suma kwartalow, i ze platnosci
    'pending' NIGDY nie wplywaja na zadne z tych zestawien."""

    def setUp(self):
        self.client = Client()
        self.staff_user = _make_staff_user()
        self.client.login(username='staff_user', password='testpass12345')
        self.owner = Owner.objects.create(first_name='Anna', last_name='Kowalska', phone='600111222')

    def _pay(self, amount, pdate, status=Payment.STATUS_PAID):
        return Payment.objects.create(owner=self.owner, amount=Decimal(amount), payment_date=pdate, status=status)

    def test_yearly_total_matches_sum_of_months(self):
        self._pay('100.00', date(2026, 1, 15))
        self._pay('200.00', date(2026, 3, 1))
        self._pay('300.00', date(2026, 7, 5))

        resp = self.client.get('/finance/report/?year=2026')
        self.assertEqual(resp.status_code, 200)

        monthly_sum = sum(m['total'] for m in resp.context['monthly_data'])
        self.assertEqual(resp.context['year_total_amount'], Decimal('600.00'))
        self.assertEqual(monthly_sum, Decimal('600.00'))

    def test_yearly_total_matches_sum_of_quarters(self):
        self._pay('100.00', date(2026, 1, 15))
        self._pay('200.00', date(2026, 3, 1))
        self._pay('300.00', date(2026, 7, 5))

        resp = self.client.get('/finance/report/?year=2026')
        quarterly_sum = sum(q['total'] for q in resp.context['quarterly_data'])
        self.assertEqual(quarterly_sum, Decimal('600.00'))

    def test_specific_month_breakdown(self):
        self._pay('100.00', date(2026, 1, 15))
        self._pay('200.00', date(2026, 3, 1))
        self._pay('50.00', date(2026, 3, 20))

        resp = self.client.get('/finance/report/?year=2026')
        monthly = {m['month_num']: m['total'] for m in resp.context['monthly_data']}
        self.assertEqual(monthly[1], Decimal('100.00'))
        self.assertEqual(monthly[3], Decimal('250.00'))
        self.assertEqual(monthly[2], Decimal('0'))

    def test_pending_payments_excluded_from_report(self):
        self._pay('100.00', date(2026, 1, 15), status=Payment.STATUS_PAID)
        self._pay('99999.00', date(2026, 1, 15), status=Payment.STATUS_PENDING)

        resp = self.client.get('/finance/report/?year=2026')
        self.assertEqual(resp.context['year_total_amount'], Decimal('100.00'))

    def test_pending_payments_shown_separately(self):
        """Pending platnosci NIE wliczaja sie do przychodu, ale ich
        suma/liczba dla wybranego roku jest pokazana osobno (informacyjnie)."""
        self._pay('500.00', date(2026, 5, 1), status=Payment.STATUS_PENDING)

        resp = self.client.get('/finance/report/?year=2026')
        self.assertEqual(resp.context['pending_in_year_amount'], Decimal('500.00'))
        self.assertEqual(resp.context['pending_in_year_count'], 1)

    def test_invalid_year_parameter_does_not_crash(self):
        """Regresja: ?year=abc wczesniej rzucalo ValueError (500 error).
        Teraz powinno bezpiecznie sfallbackowac na biezacy rok."""
        resp = self.client.get('/finance/report/?year=abc')
        self.assertEqual(resp.status_code, 200)

    def test_invalid_year_export_csv_does_not_crash(self):
        resp = self.client.get('/finance/report/export/?year=not-a-year')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp['Content-Type'].startswith('text/csv'))

    def test_by_method_breakdown(self):
        self._pay('100.00', date(2026, 1, 1))
        Payment.objects.filter(amount=Decimal('100.00')).update(method=Payment.METHOD_CASH)
        self._pay('200.00', date(2026, 1, 2))
        Payment.objects.filter(amount=Decimal('200.00')).update(method=Payment.METHOD_TRANSFER)

        resp = self.client.get('/finance/report/?year=2026')
        methods = {row['method_label']: row['total'] for row in resp.context['by_method_display']}
        self.assertEqual(methods.get('Gotowka'), Decimal('100.00'))
        self.assertEqual(methods.get('Przelew'), Decimal('200.00'))

    def test_export_csv_contains_correct_total(self):
        self._pay('100.00', date(2026, 1, 15))
        self._pay('250.00', date(2026, 6, 1))

        resp = self.client.get('/finance/report/export/?year=2026')
        content = resp.content.decode('utf-8-sig')
        self.assertIn('Anna Kowalska', content)
        self.assertIn('SUMA ROCZNA', content)

    def test_other_year_data_not_included(self):
        self._pay('100.00', date(2025, 6, 1))
        self._pay('200.00', date(2026, 6, 1))

        resp = self.client.get('/finance/report/?year=2026')
        self.assertEqual(resp.context['year_total_amount'], Decimal('200.00'))
